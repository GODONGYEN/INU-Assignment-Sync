import subprocess
from datetime import datetime, timedelta
from typing import Optional

from src.config import CALENDAR_NAME, EVENT_DURATION_MINUTES, REMINDER_MINUTES
from src.models import NormalizedAssignment


MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


def escape_applescript_string(value: str) -> str:
    """AppleScript 문자열 안에서 큰따옴표와 역슬래시를 안전하게 이스케이프합니다."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def to_applescript_string_expression(value: str) -> str:
    """
    여러 줄 문자열을 AppleScript에서 안전하게 만들기 위한 표현식으로 바꿉니다.

    예:
    "첫 줄" & return & "둘째 줄"
    """
    lines = value.splitlines() or [""]
    return " & return & ".join(f'"{escape_applescript_string(line)}"' for line in lines)


def build_applescript_date(variable_name: str, value: datetime) -> str:
    """파이썬 datetime 값을 AppleScript date 생성 코드로 바꿉니다."""
    month_name = MONTH_NAMES[value.month]
    return f"""
set {variable_name} to current date
set year of {variable_name} to {value.year}
set month of {variable_name} to {month_name}
set day of {variable_name} to {value.day}
set hours of {variable_name} to {value.hour}
set minutes of {variable_name} to {value.minute}
set seconds of {variable_name} to {value.second}
""".strip()


def build_alarm_script(reminder_minutes: list[int]) -> str:
    """분 단위 알림 설정값을 AppleScript display alarm 생성 코드로 바꿉니다."""
    lines = []
    for minutes in reminder_minutes:
        trigger_seconds = int(minutes) * 60
        lines.append(
            f"make new display alarm at end of display alarms with properties {{trigger interval:-{trigger_seconds}}}"
        )
    return "\n".join(lines)


def run_osascript(script: str) -> str:
    """AppleScript를 osascript로 실행하고 stdout/stderr를 로그로 남깁니다."""
    result = subprocess.run(
        ["osascript"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if stdout:
        print(f"[AppleScript stdout] {stdout}")
    if stderr:
        print(f"[AppleScript stderr] {stderr}")

    if result.returncode != 0:
        raise RuntimeError(stderr or "osascript 실행 중 알 수 없는 오류가 발생했습니다.")

    return stdout


def ensure_calendar_exists(calendar_name: str = CALENDAR_NAME) -> None:
    """지정한 이름의 캘린더가 없으면 새로 만듭니다."""
    script = f"""
set calendarName to "{escape_applescript_string(calendar_name)}"

tell application "Calendar"
    if not (exists calendar calendarName) then
        make new calendar with properties {{name:calendarName}}
    end if
    reload calendars
end tell
"""
    run_osascript(script)


def find_existing_calendar_event(
    assignment: NormalizedAssignment,
    calendar_name: str = CALENDAR_NAME,
) -> Optional[str]:
    """
    Calendar 내부에서 이미 존재하는 과제 이벤트를 찾습니다.

    기준:
    - 같은 캘린더
    - 마감일 기준 ±1일 범위
    - notes 메타데이터의 event_id / source_url 일치 우선
    - 없으면 제목 동일/유사 비교
    """
    search_start = assignment.due_at - timedelta(days=1)
    search_end = assignment.due_at + timedelta(days=1)

    search_start_script = build_applescript_date("searchStartDate", search_start)
    search_end_script = build_applescript_date("searchEndDate", search_end)

    script = f"""
set calendarName to "{escape_applescript_string(calendar_name)}"
set eventTitle to "{escape_applescript_string(assignment.event_title)}"
set eventMetaEventId to "{escape_applescript_string(assignment.event_id)}"
set eventSourceUrl to "{escape_applescript_string(assignment.source_url)}"
{search_start_script}
{search_end_script}

tell application "Calendar"
    if not (exists calendar calendarName) then
        return ""
    end if

    tell calendar calendarName
        set candidateEvents to (every event whose start date >= searchStartDate and start date <= searchEndDate)
        repeat with candidateEvent in candidateEvents
            set eventSummary to ""
            set eventDescription to ""

            try
                set eventSummary to summary of candidateEvent
            end try

            try
                set eventDescription to description of candidateEvent
            end try

            set titleMatch to false
            if eventSummary is not "" then
                if eventSummary is eventTitle then
                    set titleMatch to true
                else if eventSummary contains eventTitle then
                    set titleMatch to true
                else if eventTitle contains eventSummary then
                    set titleMatch to true
                end if
            end if

            set eventIdMatch to false
            if eventMetaEventId is not "" and eventDescription contains ("INU_LMS_EVENT_ID=" & eventMetaEventId) then
                set eventIdMatch to true
            end if

            set sourceUrlMatch to false
            if eventSourceUrl is not "" and eventDescription contains ("INU_LMS_SOURCE_URL=" & eventSourceUrl) then
                set sourceUrlMatch to true
            end if

            if eventIdMatch or sourceUrlMatch or titleMatch then
                return uid of candidateEvent
            end if
        end repeat
    end tell
end tell

return ""
"""
    result = run_osascript(script)
    return result or None


def create_calendar_event(
    assignment: NormalizedAssignment,
    calendar_name: str = CALENDAR_NAME,
    duration_minutes: int = EVENT_DURATION_MINUTES,
    reminder_minutes: Optional[list[int]] = None,
) -> str:
    """새 과제를 Calendar 이벤트로 등록하고 event uid를 반환합니다."""
    reminder_minutes = reminder_minutes or REMINDER_MINUTES
    event_start_script = build_applescript_date("eventStartDate", assignment.due_at)
    description_expression = to_applescript_string_expression(assignment.notes)
    alarm_script = build_alarm_script(reminder_minutes)

    script = f"""
set calendarName to "{escape_applescript_string(calendar_name)}"
set eventTitle to "{escape_applescript_string(assignment.event_title)}"
set eventDescription to {description_expression}
set eventUrl to "{escape_applescript_string(assignment.link)}"
{event_start_script}
set eventEndDate to eventStartDate + ({duration_minutes} * minutes)

tell application "Calendar"
    if not (exists calendar calendarName) then
        make new calendar with properties {{name:calendarName}}
    end if

    tell calendar calendarName
        set newEvent to make new event with properties {{summary:eventTitle, start date:eventStartDate, end date:eventEndDate}}
        set description of newEvent to eventDescription

        try
            set url of newEvent to eventUrl
        end try

        tell newEvent
            {alarm_script}
        end tell

        set createdUid to uid of newEvent
    end tell

    reload calendars
end tell

return createdUid
"""
    return run_osascript(script)


def update_calendar_event(
    event_uid: str,
    assignment: NormalizedAssignment,
    calendar_name: str = CALENDAR_NAME,
    duration_minutes: int = EVENT_DURATION_MINUTES,
    reminder_minutes: Optional[list[int]] = None,
) -> Optional[str]:
    """
    기존 Calendar 이벤트를 수정합니다.

    저장된 uid에 해당하는 일정이 없으면 None을 반환해서
    호출한 쪽에서 다시 판단할 수 있게 합니다.
    """
    reminder_minutes = reminder_minutes or REMINDER_MINUTES
    event_start_script = build_applescript_date("eventStartDate", assignment.due_at)
    description_expression = to_applescript_string_expression(assignment.notes)
    alarm_script = build_alarm_script(reminder_minutes)

    script = f"""
set calendarName to "{escape_applescript_string(calendar_name)}"
set targetUid to "{escape_applescript_string(event_uid)}"
set eventTitle to "{escape_applescript_string(assignment.event_title)}"
set eventDescription to {description_expression}
set eventUrl to "{escape_applescript_string(assignment.link)}"
{event_start_script}
set eventEndDate to eventStartDate + ({duration_minutes} * minutes)

tell application "Calendar"
    if not (exists calendar calendarName) then
        return "__NOT_FOUND__"
    end if

    tell calendar calendarName
        set matchedEvents to (every event whose uid = targetUid)
        if (count of matchedEvents) is 0 then
            return "__NOT_FOUND__"
        end if

        set targetEvent to item 1 of matchedEvents
        set summary of targetEvent to eventTitle
        set start date of targetEvent to eventStartDate
        set end date of targetEvent to eventEndDate
        set description of targetEvent to eventDescription

        try
            set url of targetEvent to eventUrl
        end try

        tell targetEvent
            delete every display alarm
            {alarm_script}
        end tell

        set updatedUid to uid of targetEvent
    end tell

    reload calendars
end tell

return updatedUid
"""
    result = run_osascript(script)
    if result == "__NOT_FOUND__":
        return None
    return result
