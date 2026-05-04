from datetime import datetime
from zoneinfo import ZoneInfo

from src.calendar_sync import (
    create_calendar_event,
    ensure_calendar_exists,
    find_existing_calendar_event,
    update_calendar_event,
)
from src.config import CALENDAR_NAME, DRY_RUN, ENV_EXAMPLE_PATH, ENV_PATH, LOG_FILE_PATH, INCLUDE_PAST_ASSIGNMENTS, TIMEZONE
from src.logging_utils import attach_stdout_stderr_to_logger, setup_file_logging
from src.normalizer import normalize_assignment
from src.scraper import login_and_collect_assignments
from src.storage import SQLiteSyncStore


def assignment_changed(saved_row: dict, normalized_assignment) -> bool:
    """저장된 이력과 현재 과제 정보가 다른지 확인합니다."""
    return any(
        [
            saved_row["due_at_iso"] != normalized_assignment.due_at.isoformat(),
            saved_row["course_name"] != normalized_assignment.course_name,
            saved_row["title"] != normalized_assignment.title,
            (saved_row["link"] or "") != normalized_assignment.link,
            (saved_row["event_id"] or "") != normalized_assignment.event_id,
            (saved_row["source_url"] or "") != normalized_assignment.source_url,
            saved_row["event_title"] != normalized_assignment.event_title,
        ]
    )


def main() -> None:
    """프로그램 전체 흐름을 순서대로 실행합니다."""
    logger = setup_file_logging(LOG_FILE_PATH)
    attach_stdout_stderr_to_logger(logger)

    if not ENV_PATH.exists():
        if ENV_EXAMPLE_PATH.exists():
            print("[ERROR] .env 파일이 없습니다. 먼저 .env.example을 복사해 설정을 확인해 주세요.")
        else:
            print("[ERROR] .env 파일과 .env.example 파일이 모두 없습니다.")
        return

    print("1) 이러닝 사이트에서 과제 목록을 가져오는 중입니다...")
    try:
        raw_assignments = login_and_collect_assignments()
    except Exception as error:
        print(f"[ERROR] LMS 수집 시작 실패: {error}")
        return

    print("2) 과제 데이터를 표준 형식으로 정리하는 중입니다...")
    normalized_assignments = []
    seen_ids = set()

    for raw_assignment in raw_assignments:
        try:
            normalized = normalize_assignment(raw_assignment)
        except Exception as error:
            print(f"[ERROR] 과제 데이터 해석 실패: {error}")
            continue

        if normalized.external_id in seen_ids:
            print(f"[SKIP] 같은 실행 안에서 중복 과제 발견: {normalized.event_title}")
            continue

        seen_ids.add(normalized.external_id)
        normalized_assignments.append(normalized)

    print(f"[INFO] 수집된 과제 수: {len(normalized_assignments)}")
    if not normalized_assignments:
        print("[ERROR] 과제가 0개 수집되었습니다. 로그인 상태, 캘린더 범위, selector 설정을 확인해 주세요.")
        return

    try:
        store = SQLiteSyncStore()
    except Exception as error:
        print(f"[ERROR] SQLite DB 오류: {error}")
        return

    if not DRY_RUN:
        try:
            ensure_calendar_exists(CALENDAR_NAME)
        except Exception as error:
            print(f"[ERROR] macOS Calendar 권한 또는 AppleScript 오류: {error}")
            return

    now = datetime.now(ZoneInfo(TIMEZONE))

    new_target_count = 0
    update_target_count = 0
    skip_count = 0
    error_count = 0

    print("3) 캘린더 동기화를 시작합니다...")
    for assignment in normalized_assignments:
        try:
            saved_row = store.get_assignment(assignment.external_id)
            saved_event_uid = saved_row["event_uid"] if saved_row is not None else None
            calendar_event_uid = saved_event_uid
            if not DRY_RUN:
                calendar_event_uid = saved_event_uid or find_existing_calendar_event(assignment)
            is_past_assignment = assignment.due_at < now

            # 이미 Calendar에 있으면 새로 만들지 않고 연결만 저장합니다.
            if saved_row is None and calendar_event_uid is not None:
                if not DRY_RUN:
                    store.upsert_assignment(assignment, calendar_event_uid)
                skip_count += 1
                print(f"[SKIP] Calendar에 이미 존재: {assignment.event_title}")
                continue

            if saved_row is None and calendar_event_uid is None and is_past_assignment and not INCLUDE_PAST_ASSIGNMENTS:
                skip_count += 1
                print(f"[SKIP] 지난 과제 제외됨: {assignment.event_title}")
                continue

            if saved_row is not None and calendar_event_uid is not None and assignment_changed(saved_row, assignment):
                update_target_count += 1
                print(f"[UPDATE] 마감 변경 감지 → 이벤트 수정: {assignment.event_title}")

                if DRY_RUN:
                    print(f"[DRY-RUN] 수정 예정: {assignment.event_title}")
                    continue

                updated_event_uid = update_calendar_event(calendar_event_uid, assignment)
                if updated_event_uid is None:
                    duplicate_uid = find_existing_calendar_event(assignment)
                    if duplicate_uid is not None:
                        updated_event_uid = update_calendar_event(duplicate_uid, assignment)
                    else:
                        updated_event_uid = create_calendar_event(assignment)

                store.upsert_assignment(assignment, updated_event_uid)
                print(f"[UPDATE] 수정 완료: {assignment.event_title}")
                continue

            if saved_row is not None and calendar_event_uid is not None:
                skip_count += 1
                print(f"[SKIP] 변경 없음: {assignment.event_title}")
                continue

            new_target_count += 1
            if DRY_RUN:
                print(f"[DRY-RUN] 신규 등록 예정: {assignment.event_title}")
                continue

            created_event_uid = create_calendar_event(assignment)
            store.upsert_assignment(assignment, created_event_uid)
            print(f"[OK] 등록 완료: {assignment.event_title}")
        except Exception as error:
            error_count += 1
            print(f"[ERROR] 동기화 실패: {assignment.event_title} / {error}")
            continue

    print("\n동기화가 끝났습니다.")
    print(f"[INFO] 신규 등록 대상: {new_target_count}")
    print(f"[INFO] 업데이트 대상: {update_target_count}")
    print(f"[INFO] 스킵: {skip_count}")
    if error_count:
        print(f"[ERROR] 실패: {error_count}")


if __name__ == "__main__":
    main()
