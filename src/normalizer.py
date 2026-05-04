import hashlib
import re
from datetime import datetime
from typing import Optional
from urllib.parse import parse_qs, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from src.config import TIMEZONE
from src.models import NormalizedAssignment, RawAssignment


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


def clean_text(value: str) -> str:
    """줄바꿈이나 연속 공백을 정리해서 읽기 쉬운 문자열로 만듭니다."""
    return re.sub(r"\s+", " ", (value or "")).strip()


def extract_event_id_from_text(value: str) -> str:
    """링크 문자열에서 #event_123 형태의 event id를 추출합니다."""
    match = re.search(r"#event_(\d+)", value or "")
    return match.group(1) if match else ""


def normalize_link_for_identity(link: str) -> str:
    """중복 판단에 쓸 링크를 정규화합니다."""
    if not link:
        return ""

    parsed = urlsplit(link)
    query = parse_qs(parsed.query)

    # Moodle mod_assign 링크라면 id 파라미터가 사실상 고유값 역할을 합니다.
    if "/mod/assign/" in parsed.path and query.get("id"):
        return f"mod_assign:{query['id'][0]}"

    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))


def build_assignment_id(raw_assignment: RawAssignment) -> str:
    """
    과제를 식별할 고유 ID를 만듭니다.

    우선순위:
    1. 캘린더 href의 #event_숫자
    2. 상세 페이지 URL
    3. 마지막 fallback으로 제목/과목명 조합 해시
    """
    if clean_text(raw_assignment.event_id):
        return f"event:{clean_text(raw_assignment.event_id)}"

    link_candidate = clean_text(raw_assignment.link) or clean_text(raw_assignment.source_link)
    normalized_link = normalize_link_for_identity(link_candidate)
    if normalized_link:
        return f"url:{normalized_link}"

    raw_key = f"{raw_assignment.course_name}||{raw_assignment.title}".strip()
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def preprocess_datetime_text(value: str) -> str:
    """한국어 날짜 문자열도 여러 포맷으로 파싱하기 쉽게 정리합니다."""
    text = clean_text(value)

    # 요일 표기를 지워서 파싱 패턴 수를 줄입니다.
    text = re.sub(r"\([^)]*\)", "", text)

    # 한글 날짜 표기를 일반적인 구분자로 바꿉니다.
    text = text.replace("년", "-")
    text = text.replace("월", "-")
    text = text.replace("일", "")
    text = text.replace(".", "-")
    text = text.replace("/", "-")
    text = text.replace(",", " ")

    # 자주 붙는 안내 문구를 제거합니다.
    text = text.replace("까지", "")
    text = text.replace("마감", "")
    text = text.replace("제출", "")
    text = text.replace("Due date", "")
    text = text.replace("Cut-off date", "")
    text = text.replace("Due", "")

    # 영어 요일 표기도 제거합니다.
    text = re.sub(
        r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # 오전/오후를 파이썬이 이해할 수 있는 형태로 바꿉니다.
    text = text.replace("오전", "AM")
    text = text.replace("오후", "PM")

    return clean_text(text)


def parse_due_datetime(due_date_text: str, due_time_text: str, due_text: str) -> Optional[datetime]:
    """
    여러 형태의 마감일 문자열을 파이썬 datetime으로 바꿉니다.

    사이트마다 표기가 달라질 수 있으므로, 자주 쓰는 패턴을 여러 개 시도합니다.
    """
    candidates = []

    if clean_text(due_date_text) and clean_text(due_time_text):
        candidates.append(f"{due_date_text} {due_time_text}")

    if clean_text(due_text):
        candidates.append(due_text)

    if clean_text(due_date_text) and not clean_text(due_time_text):
        # 시간이 따로 없으면 보통 하루 끝으로 간주합니다.
        candidates.append(f"{due_date_text} 23:59")

    patterns = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %p %I:%M",
        "%Y-%m-%d %I:%M %p",
        "%d %B %Y %H:%M",
        "%d %B %Y %I:%M %p",
        "%B %d %Y %H:%M",
        "%B %d %Y %I:%M %p",
        "%d %b %Y %H:%M",
        "%d %b %Y %I:%M %p",
        "%b %d %Y %H:%M",
        "%b %d %Y %I:%M %p",
        "%Y-%m-%d",
        "%d %B %Y",
        "%B %d %Y",
        "%d %b %Y",
        "%b %d %Y",
    ]

    for candidate in candidates:
        normalized_text = preprocess_datetime_text(candidate)
        for pattern in patterns:
            try:
                parsed = datetime.strptime(normalized_text, pattern)
                if pattern == "%Y-%m-%d":
                    parsed = parsed.replace(hour=23, minute=59)
                return parsed.replace(tzinfo=ZoneInfo(TIMEZONE))
            except ValueError:
                continue

    return None


def build_fallback_due_at() -> datetime:
    """
    마감일을 어디에서도 얻지 못했을 때 사용할 최후 기본값입니다.

    이번 프로젝트에서는 원칙적으로 scraper가 캘린더 날짜를 기준으로
    due_at을 채워 주도록 했기 때문에, 이 값은 예외 상황용 안전장치입니다.
    """
    now = datetime.now(ZoneInfo(TIMEZONE))
    return now.replace(hour=23, minute=59, second=0, microsecond=0)


def build_notes(
    course_name: str,
    title: str,
    due_at: datetime,
    link: str,
    event_id: str,
    source_url: str,
) -> str:
    """Calendar 메모에 들어갈 내용을 보기 좋게 만듭니다."""
    due_text = due_at.strftime("%Y-%m-%d %H:%M")
    due_at_iso = due_at.isoformat()
    return "\n".join(
        [
            f"과목: {course_name}",
            f"과제: {title}",
            f"마감: {due_text}",
            "",
            f"INU_LMS_EVENT_ID={event_id}",
            f"INU_LMS_SOURCE_URL={source_url}",
            f"INU_LMS_DUE_AT={due_at_iso}",
        ]
    )


def build_event_title(course_name: str, title: str) -> str:
    """
    캘린더 일정 제목을 만듭니다.

    과목명을 아직 찾지 못한 경우에는 `[과목명 미확인]` 접두사를 붙이지 않고
    과제 제목만 보여 주는 편이 더 자연스럽습니다.
    """
    if course_name == "과목명 미확인":
        return title
    return f"[{course_name}] {title}"


def normalize_assignment(raw_assignment: RawAssignment) -> NormalizedAssignment:
    """원본 과제 데이터를 표준 구조로 바꿉니다."""
    course_name = clean_text(raw_assignment.course_name)
    title = clean_text(raw_assignment.title)
    link = clean_text(raw_assignment.link)

    if not course_name:
        raise ValueError("과목명이 비어 있습니다.")

    if not title:
        raise ValueError("과제 제목이 비어 있습니다.")

    due_at = raw_assignment.due_at
    if due_at is None:
        due_at = parse_due_datetime(
            due_date_text=raw_assignment.due_date_text,
            due_time_text=raw_assignment.due_time_text,
            due_text=raw_assignment.due_text,
        )

    # 마감일 파싱 실패로 과제를 버리지 않고, 가능한 기본값으로 계속 진행합니다.
    if due_at is None:
        due_at = build_fallback_due_at()

    external_id = build_assignment_id(raw_assignment)
    event_title = build_event_title(course_name=course_name, title=title)
    event_id = clean_text(raw_assignment.event_id)
    source_url = clean_text(raw_assignment.source_link) or link
    notes = build_notes(
        course_name=course_name,
        title=title,
        due_at=due_at,
        link=link,
        event_id=event_id,
        source_url=source_url,
    )

    return NormalizedAssignment(
        external_id=external_id,
        course_name=course_name,
        title=title,
        due_at=due_at,
        link=link,
        event_id=event_id,
        source_url=source_url,
        event_title=event_title,
        notes=notes,
    )
