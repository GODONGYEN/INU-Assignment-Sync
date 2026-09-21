import calendar
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, parse_qsl, urlencode, urljoin, urlparse, urlunparse
from zoneinfo import ZoneInfo

try:
    from playwright.sync_api import Locator, Page, sync_playwright
except ModuleNotFoundError:
    Locator = object  # type: ignore[assignment]
    Page = object  # type: ignore[assignment]
    sync_playwright = None

from src.config import (
    ASSIGNMENTS_URL,
    ASSIGNMENT_COURSE_SELECTOR,
    ASSIGNMENT_DUE_DATE_SELECTOR,
    ASSIGNMENT_DUE_TEXT_SELECTOR,
    ASSIGNMENT_DUE_TIME_SELECTOR,
    ASSIGNMENT_TITLE_SELECTOR,
    BASE_URL,
    CALENDAR_MONTHS_BACK,
    CALENDAR_MONTHS_FORWARD,
    CALENDAR_DAY_CELL_SELECTOR,
    CALENDAR_DAY_NUMBER_SELECTOR,
    CALENDAR_EVENT_LINK_SELECTOR,
    CALENDAR_EVENT_SELECTOR,
    CALENDAR_TABLE_SELECTOR,
    CURRENT_MONTH_SELECTOR,
    HEADLESS,
    INCLUDE_KEYWORDS,
    E_LEARNING_ID,
    E_LEARNING_PASSWORD,
    GUI_MODE,
    LOGIN_ID_SELECTOR,
    LOGIN_PASSWORD_SELECTOR,
    LOGIN_SUBMIT_SELECTOR,
    LOGIN_SUCCESS_WAIT_SELECTOR,
    LOGIN_WAIT_TIMEOUT_MS,
    LOGIN_URL,
    LOGS_DIR,
    PAGE_TIMEOUT_MS,
    SAVE_DEBUG_SNAPSHOT,
    SLOW_MO_MS,
    TIMEZONE,
    USE_MANUAL_LOGIN,
)
from src.models import RawAssignment
from src.normalizer import clean_text


CALENDAR_ROOT_FALLBACK_SELECTORS = [
    "table.calendarmonth.calendartable",
    ".maincalendar",
    ".calendarwrapper",
    "[data-region='calendar']",
    "[data-region='month-view']",
    ".calendar-event-panel",
    ".calendar-controls",
]

CURRENT_MONTH_FALLBACK_SELECTORS = [
    "h2.current",
    ".current",
    ".calendar-controls .current",
    "[data-region='view-title']",
    ".page-header-headings h1",
    "#page-header h1",
    "h1",
]

CALENDAR_EVENT_FALLBACK_SELECTORS = [
    "ul.events-new li.calendar_event_course",
    "li.calendar_event_course",
    ".calendar_event_course",
    ".calendar_event_group",
    ".calendar_event_user",
    ".calendar_event_global",
    "[data-region='event-item']",
    "[data-event-id]",
    ".eventlist .event",
    ".event",
    "a[href*='calendar/view.php?view=event']",
    "a[href*='/mod/assign/']",
    "a[href*='mod/assign/view.php']",
]

CALENDAR_EVENT_LINK_FALLBACK_SELECTORS = [
    "a",
    ".eventname a",
    "[data-action='view-event']",
    "a[href*='calendar/view.php']",
    "a[href*='/mod/assign/']",
    "a[href*='mod/assign/view.php']",
]

CALENDAR_DAY_NUMBER_FALLBACK_SELECTORS = [
    "div.day",
    ".day",
    ".day-number",
    ".calendar-day-number",
    "[data-region='day-content']",
    "a[data-action='view-day-link']",
]


def selector_candidates(primary: str, fallbacks: list[str]) -> list[str]:
    """환경변수 selector를 먼저 쓰고, 이어서 코드에 내장된 후보를 중복 없이 반환합니다."""
    candidates = []
    for selector in [primary, *fallbacks]:
        cleaned = clean_text(selector)
        if cleaned and cleaned not in candidates:
            candidates.append(cleaned)
    return candidates


def safe_text(parent, selector: str) -> str:
    """selector가 없거나 요소가 없어도 프로그램이 죽지 않도록 문자열을 안전하게 읽습니다."""
    if not selector:
        return ""

    try:
        locator = parent.locator(selector).first
        if locator.count() == 0:
            return ""
        return clean_text(locator.text_content() or "")
    except Exception:
        return ""


def safe_attribute(parent, selector: str, attribute_name: str) -> str:
    """링크 주소 같은 속성값을 안전하게 읽습니다."""
    if not selector:
        return ""

    try:
        locator = parent.locator(selector).first
        if locator.count() == 0:
            return ""
        return clean_text(locator.get_attribute(attribute_name) or "")
    except Exception:
        return ""


def safe_locator_count(parent, selector: str) -> int:
    """selector 문법이 바뀌었거나 요소가 없어도 안전하게 count를 가져옵니다."""
    try:
        return parent.locator(selector).count()
    except Exception:
        return 0


def get_text_if_exists(locator: Locator) -> str:
    """Locator가 실제 요소를 가리킬 때만 텍스트를 꺼냅니다."""
    try:
        if locator.count() == 0:
            return ""
        return clean_text(locator.text_content() or "")
    except Exception:
        return ""


def get_attribute_if_exists(locator: Locator, attribute_name: str) -> str:
    """Locator가 있을 때만 속성값을 읽습니다."""
    try:
        if locator.count() == 0:
            return ""
        return clean_text(locator.get_attribute(attribute_name) or "")
    except Exception:
        return ""


def first_non_empty_text(page: Page, selectors: list[str]) -> str:
    """여러 selector 후보 중 먼저 텍스트를 찾은 값을 반환합니다."""
    for selector in selectors:
        if not selector:
            continue
        text = safe_text(page, selector)
        if text:
            return text
    return ""


def first_visible_selector(page: Page, selectors: list[str]) -> str:
    """여러 selector 중 페이지에 실제로 존재하는 첫 selector를 찾습니다."""
    for selector in selectors:
        if safe_locator_count(page, selector) > 0:
            return selector
    return ""


def wait_for_any_selector(page: Page, selectors: list[str], timeout: int) -> str:
    """여러 selector 후보 중 하나가 나타날 때까지 짧게 나눠 기다립니다."""
    deadline = datetime.now().timestamp() + (timeout / 1000)

    while datetime.now().timestamp() < deadline:
        selector = first_visible_selector(page, selectors)
        if selector:
            return selector
        page.wait_for_timeout(500)

    return ""


def first_non_empty_attribute(page: Page, selectors: list[str], attribute_name: str) -> str:
    """여러 selector 후보 중 먼저 속성값을 찾은 값을 반환합니다."""
    for selector in selectors:
        if not selector:
            continue
        value = safe_attribute(page, selector, attribute_name)
        if value:
            return value
    return ""


def build_day_cell_xpath_condition() -> str:
    """CALENDAR_DAY_CELL_SELECTOR 값을 XPath class 조건으로 바꿉니다."""
    class_tokens = []
    day_cell_selector_candidates = [
        CALENDAR_DAY_CELL_SELECTOR,
        "td.day",
        "td.duration_course",
        ".day",
        ".calendar-day",
    ]

    for token in ",".join(day_cell_selector_candidates).split(","):
        cleaned = token.strip()
        if "." in cleaned:
            class_tokens.append(cleaned.split(".")[-1])

    if not class_tokens:
        class_tokens = ["day"]

    return " or ".join([f'contains(@class, "{class_name}")' for class_name in class_tokens])


def find_parent_day_cell(event_item: Locator) -> Locator:
    """이벤트가 들어 있는 상위 날짜 셀을 찾습니다."""
    condition = build_day_cell_xpath_condition()
    xpath = (
        "xpath=ancestor::*[self::td or self::div]"
        f"[({condition}) or @data-day or @data-date or contains(@class, 'calendar-day')][1]"
    )
    return event_item.locator(xpath).first


def save_debug_snapshot(page: Page, label: str, reason: str) -> None:
    """selector 실패를 분석할 수 있도록 선택적으로 HTML과 스크린샷을 저장합니다."""
    if not SAVE_DEBUG_SNAPSHOT:
        print(
            "[INFO] 디버그 스냅샷 저장이 꺼져 있습니다. "
            "필요하면 .env에서 SAVE_DEBUG_SNAPSHOT=true로 설정하세요."
        )
        return

    safe_label = re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", label).strip("_") or "snapshot"
    timestamp = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y%m%d_%H%M%S")
    debug_dir = Path(LOGS_DIR) / "lms_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    html_path = debug_dir / f"{timestamp}_{safe_label}.html"
    png_path = debug_dir / f"{timestamp}_{safe_label}.png"

    html_path.write_text(page.content(), encoding="utf-8")
    try:
        page.screenshot(path=str(png_path), full_page=True)
    except Exception as error:
        print(f"[WARN] 디버그 스크린샷 저장 실패: {error}")

    print(f"[INFO] LMS 디버그 HTML 저장: {html_path}")
    print(f"[INFO] LMS 디버그 스크린샷 저장: {png_path}")
    print(f"[INFO] 저장 사유: {reason}")


def title_matches_keywords(title: str) -> bool:
    """이벤트 제목이 과제 후보로 보이는지 키워드 기준으로 확인합니다."""
    normalized_title = clean_text(title).lower()
    return any(keyword.lower() in normalized_title for keyword in INCLUDE_KEYWORDS)


def extract_event_id_from_url(url: str) -> str:
    """캘린더 href의 #event_123 형태에서 event id를 찾습니다."""
    match = re.search(r"#event_(\d+)", url or "")
    if match:
        return match.group(1)

    match = re.search(r"[?&]eventid=(\d+)", url or "", flags=re.IGNORECASE)
    if match:
        return match.group(1)

    match = re.search(r"[?&]id=(\d+)", url or "", flags=re.IGNORECASE)
    return match.group(1) if match else ""


def extract_event_id_from_item(event_item: Locator, event_url: str) -> str:
    """URL과 data 속성에서 이벤트 ID를 최대한 찾습니다."""
    event_id = extract_event_id_from_url(event_url)
    if event_id:
        return event_id

    for attribute_name in ["data-event-id", "data-eventid", "data-id", "id"]:
        value = get_attribute_if_exists(event_item, attribute_name)
        if not value:
            continue
        match = re.search(r"\d+", value)
        if match:
            return match.group()

    return ""


def parse_date_from_text(value: str, year: int) -> Optional[datetime]:
    """텍스트 속 날짜 표현에서 날짜만 추출합니다."""
    text = clean_text(value)
    if not text:
        return None

    patterns = [
        r"(\d{4})[-./년\s]+(\d{1,2})[-./월\s]+(\d{1,2})",
        r"(\d{1,2})[-./월\s]+(\d{1,2})[-./일\s]*",
    ]

    match = re.search(patterns[0], text)
    if match:
        parsed_year = int(match.group(1))
        parsed_month = int(match.group(2))
        parsed_day = int(match.group(3))
        try:
            return datetime(parsed_year, parsed_month, parsed_day, 23, 59, tzinfo=ZoneInfo(TIMEZONE))
        except ValueError:
            return None

    match = re.search(patterns[1], text)
    if match:
        parsed_month = int(match.group(1))
        parsed_day = int(match.group(2))
        try:
            return datetime(year, parsed_month, parsed_day, 23, 59, tzinfo=ZoneInfo(TIMEZONE))
        except ValueError:
            return None

    return None


def is_manual_login_completed(page: Page) -> bool:
    """현재 페이지 상태가 로그인 완료로 볼 수 있는지 확인합니다."""
    try:
        current_url = page.url or ""
    except Exception:
        current_url = ""

    parsed = urlparse(current_url)
    if parsed.hostname != urlparse(BASE_URL).hostname or "login" in parsed.path.lower():
        return False
    if safe_locator_count(page, 'input[type="password"]'):
        return False
    # A redirect to the SSO provider or a public home page is not a login.
    return any(safe_locator_count(page, selector) > 0 for selector in [
        "a[href*='/course/view.php?id=']",
        "a[href*='/login/logout.php']",
        "a[href*='logout']",
        CALENDAR_TABLE_SELECTOR,
    ])


def wait_for_manual_login_completion(page: Page) -> None:
    """수동 로그인 완료를 자동 감지할 때까지 기다립니다."""
    print("[INFO] GUI 모드: 로그인 완료를 자동 감지합니다.")
    deadline = datetime.now().timestamp() + (LOGIN_WAIT_TIMEOUT_MS / 1000)

    while datetime.now().timestamp() < deadline:
        if is_manual_login_completed(page):
            print("[INFO] 로그인 완료를 자동 감지했습니다.")
            return
        page.wait_for_timeout(1000)

    raise RuntimeError(
        "[ERROR] 로그인 완료를 감지하지 못했습니다. 브라우저에서 로그인을 완료했는지 확인하세요."
    )


def shift_month(year: int, month: int, offset: int) -> tuple[int, int]:
    """연/월에서 offset개월 이동한 결과를 돌려줍니다."""
    month_index = (year * 12 + (month - 1)) + offset
    shifted_year = month_index // 12
    shifted_month = (month_index % 12) + 1
    return shifted_year, shifted_month


def build_collection_months() -> list[tuple[int, int]]:
    """현재 시각 기준으로 수집할 월 목록을 만듭니다."""
    now = datetime.now(ZoneInfo(TIMEZONE))
    months = []
    for offset in range(-CALENDAR_MONTHS_BACK, CALENDAR_MONTHS_FORWARD + 1):
        months.append(shift_month(now.year, now.month, offset))
    return months


def build_collection_window(months: list[tuple[int, int]]) -> tuple[datetime, datetime]:
    """수집 범위의 시작 시각과 끝 시각(다음 달 시작 직전이 아닌 시작점)을 계산합니다."""
    first_year, first_month = months[0]
    last_year, last_month = months[-1]
    start = datetime(first_year, first_month, 1, 0, 0, tzinfo=ZoneInfo(TIMEZONE))
    next_year, next_month = shift_month(last_year, last_month, 1)
    end = datetime(next_year, next_month, 1, 0, 0, tzinfo=ZoneInfo(TIMEZONE))
    return start, end


def build_month_page_url(base_url: str, year: int, month: int) -> str:
    """
    Moodle 월간 캘린더 URL을 만듭니다.

    `time`은 Asia/Seoul 기준 해당 월 1일 12:00의 Unix timestamp를 사용합니다.
    """
    month_anchor = datetime(year, month, 1, 12, 0, tzinfo=ZoneInfo(TIMEZONE))
    parsed = urlparse(base_url)
    query_items = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query_items["view"] = "month"
    query_items["time"] = str(int(month_anchor.timestamp()))
    return urlunparse(parsed._replace(query=urlencode(query_items)))


def resolve_calendar_year_month(page: Page) -> tuple[int, int]:
    """
    현재 보고 있는 월간 캘린더의 연도/월을 구합니다.

    우선순위:
    1. `h2.current` 텍스트
    2. URL 쿼리의 year/month
    3. URL 쿼리의 time timestamp
    4. 페이지 제목이나 본문에서 '2026년 4월' 같은 문자열 찾기
    5. 마지막 fallback으로 현재 로컬 시간
    """
    current_month_text = first_non_empty_text(
        page,
        selector_candidates(CURRENT_MONTH_SELECTOR, CURRENT_MONTH_FALLBACK_SELECTORS),
    )
    match = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월", current_month_text or "")
    if match:
        return int(match.group(1)), int(match.group(2))

    match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})",
        current_month_text or "",
        flags=re.IGNORECASE,
    )
    if match:
        month_name = match.group(1).lower()
        month_index = [
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ].index(month_name) + 1
        return int(match.group(2)), month_index

    parsed = urlparse(page.url)
    query = parse_qs(parsed.query)

    year = query.get("year", [""])[0]
    month = query.get("month", [""])[0]
    if year.isdigit() and month.isdigit():
        return int(year), int(month)

    time_value = query.get("time", [""])[0]
    if time_value.isdigit():
        dt = datetime.fromtimestamp(int(time_value), tz=ZoneInfo(TIMEZONE))
        return dt.year, dt.month

    candidate_texts = [page.title(), safe_text(page, "body")]
    for text in candidate_texts:
        match = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월", text or "")
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})",
            text or "",
            flags=re.IGNORECASE,
        )
        if match:
            month_name = match.group(1).lower()
            month_index = [
                "january",
                "february",
                "march",
                "april",
                "may",
                "june",
                "july",
                "august",
                "september",
                "october",
                "november",
                "december",
            ].index(month_name) + 1
            return int(match.group(2)), month_index

    now = datetime.now(ZoneInfo(TIMEZONE))
    return now.year, now.month


def build_due_at_from_day_number(year: int, month: int, day_number_text: str) -> Optional[datetime]:
    """캘린더 셀의 날짜 숫자와 현재 월/연도로 마감일 23:59를 만듭니다."""
    match = re.search(r"\d+", day_number_text or "")
    if not match:
        return None

    day = int(match.group())
    _, last_day = calendar.monthrange(year, month)
    if day < 1 or day > last_day:
        return None
    return datetime(year, month, day, 23, 59, tzinfo=ZoneInfo(TIMEZONE))


def build_due_at_from_event_item(event_item: Locator, year: int, month: int) -> Optional[datetime]:
    """이벤트가 속한 날짜 셀/속성/텍스트에서 due_at을 최대한 복원합니다."""
    day_cell = find_parent_day_cell(event_item)

    for attribute_name in ["data-date", "data-day", "aria-label", "title"]:
        value = get_attribute_if_exists(day_cell, attribute_name)
        due_at = parse_date_from_text(value, year)
        if due_at:
            return due_at

    day_number_selectors = selector_candidates(
        CALENDAR_DAY_NUMBER_SELECTOR,
        CALENDAR_DAY_NUMBER_FALLBACK_SELECTORS,
    )
    for selector in day_number_selectors:
        day_number_text = safe_text(day_cell, selector)
        due_at = build_due_at_from_day_number(year, month, day_number_text)
        if due_at:
            return due_at

    for attribute_name in ["data-date", "data-day", "aria-label", "title"]:
        value = get_attribute_if_exists(event_item, attribute_name)
        due_at = parse_date_from_text(value, year)
        if due_at:
            return due_at

    # 마지막으로 주변 텍스트에서 날짜를 찾아봅니다. 너무 넓게 잡으면 오탐이 생겨 fallback으로만 둡니다.
    return parse_date_from_text(get_text_if_exists(day_cell), year)


def build_calendar_event_dedupe_key(event: dict) -> str:
    """캘린더 이벤트 단계에서 사용할 중복 제거 키를 만듭니다."""
    if event["event_id"]:
        return f"event:{event['event_id']}"
    return f"url:{event['event_url']}||title:{event['title']}||due:{event['due_at'].isoformat()}"


def is_due_at_within_collection_window(
    due_at: datetime,
    window_start: datetime,
    window_end: datetime,
) -> bool:
    """마감 시각이 현재 수집 범위 안에 들어오는지 확인합니다."""
    return window_start <= due_at < window_end


def get_event_link_info(event_item: Locator) -> tuple[str, str]:
    """이벤트 요소에서 제목과 링크를 찾습니다."""
    link_selectors = selector_candidates(
        CALENDAR_EVENT_LINK_SELECTOR,
        CALENDAR_EVENT_LINK_FALLBACK_SELECTORS,
    )

    for selector in link_selectors:
        link_locator = event_item.locator(selector).first
        if link_locator.count() == 0:
            continue

        href = get_attribute_if_exists(link_locator, "href")
        title = (
            get_text_if_exists(link_locator)
            or get_attribute_if_exists(link_locator, "title")
            or get_attribute_if_exists(link_locator, "aria-label")
        )

        if href or title:
            return title, href

    href = get_attribute_if_exists(event_item, "href")
    title = (
        get_text_if_exists(event_item)
        or get_attribute_if_exists(event_item, "title")
        or get_attribute_if_exists(event_item, "aria-label")
    )
    return title, href


def collect_calendar_events_for_month(page: Page, target_year: int, target_month: int) -> list[dict]:
    """특정 월의 월간 캘린더 페이지에서 이벤트 목록을 수집합니다."""
    target_label = f"{target_year:04d}-{target_month:02d}"
    print(f"[INFO] 캘린더 월 수집 시작: {target_label}")

    month_url = build_month_page_url(ASSIGNMENTS_URL, target_year, target_month)
    page.goto(month_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
    root_selectors = selector_candidates(CALENDAR_TABLE_SELECTOR, CALENDAR_ROOT_FALLBACK_SELECTORS)
    matched_root_selector = wait_for_any_selector(page, root_selectors, PAGE_TIMEOUT_MS)
    if not matched_root_selector:
        save_debug_snapshot(page, f"calendar_root_missing_{target_label}", "캘린더 루트 selector 탐색 실패")
        raise RuntimeError(
            "캘린더 테이블 selector를 찾지 못했습니다. "
            f"시도한 selector={root_selectors!r}"
        )

    print(f"[INFO] 캘린더 루트 selector 사용: {matched_root_selector}")

    events = []
    event_selectors = selector_candidates(CALENDAR_EVENT_SELECTOR, CALENDAR_EVENT_FALLBACK_SELECTORS)
    matched_event_selector = first_visible_selector(page, event_selectors)
    if not matched_event_selector:
        save_debug_snapshot(page, f"calendar_events_missing_{target_label}", "캘린더 이벤트 selector 탐색 실패")
        print(f"[WARN] 캘린더 이벤트 selector를 찾지 못했습니다. 시도한 selector={event_selectors!r}")
        return []

    print(f"[INFO] 캘린더 이벤트 selector 사용: {matched_event_selector}")

    event_items = page.locator(matched_event_selector)
    event_count = event_items.count()
    current_year, current_month = resolve_calendar_year_month(page)
    print(f"[INFO] 현재 캘린더 기준 연월: {current_year:04d}-{current_month:02d}")

    print(f"[INFO] 발견한 이벤트 수: {event_count}개")

    for index in range(event_count):
        event_item = event_items.nth(index)
        title, href = get_event_link_info(event_item)
        absolute_url = urljoin(BASE_URL, href) if href else ""
        due_at = build_due_at_from_event_item(event_item, current_year, current_month)
        event_id = extract_event_id_from_item(event_item, absolute_url)
        if due_at is None:
            _, last_day = calendar.monthrange(current_year, current_month)
            print(
                "[건너뜀] 유효하지 않은 캘린더 날짜입니다: "
                f"year={current_year}, month={current_month}, title={title!r}, "
                f"허용범위=1~{last_day}"
            )
            continue

        calendar_date = due_at.strftime("%Y-%m-%d")
        print(f"[INFO] 캘린더 날짜 기반 마감일 생성: {due_at.strftime('%Y-%m-%d %H:%M')}")

        events.append(
            {
                "title": title,
                "event_url": absolute_url,
                "event_id": event_id,
                "calendar_date": calendar_date,
                "due_at": due_at,
                "priority_by_keyword": title_matches_keywords(title),
            }
        )

    keyword_candidates = sum(1 for event in events if event["priority_by_keyword"])
    print(f"[INFO] 과제 후보 수: {keyword_candidates}개")
    return events


def collect_calendar_events(page: Page) -> tuple[list[dict], dict, datetime, datetime]:
    """여러 달의 월간 캘린더 페이지를 순회하며 이벤트를 모읍니다."""
    months = build_collection_months()
    window_start, window_end = build_collection_window(months)

    all_events: list[dict] = []
    total_keyword_candidates = 0

    for year, month in months:
        month_events = collect_calendar_events_for_month(page, year, month)
        all_events.extend(month_events)
        total_keyword_candidates += sum(1 for event in month_events if event["priority_by_keyword"])

    summary = {
        "months_count": len(months),
        "total_events": len(all_events),
        "total_candidates": total_keyword_candidates,
    }

    print(f"[INFO] 전체 수집 월 수: {summary['months_count']}개월")
    print(f"[INFO] 전체 캘린더 이벤트 수: {summary['total_events']}개")
    print(f"[INFO] 전체 과제 후보 수: {summary['total_candidates']}개")

    return all_events, summary, window_start, window_end


def resolve_assignment_detail_url(detail_page: Page, fallback_title: str) -> str:
    """이벤트 페이지 안에서 실제 mod_assign 상세 링크가 보이면 그 링크를 반환합니다."""
    if "/mod/assign/" in urlparse(detail_page.url).path:
        return detail_page.url

    candidate_selectors = [
        "a[href*='/mod/assign/']",
        "a[href*='mod/assign/view.php']",
    ]

    for selector in candidate_selectors:
        links = detail_page.locator(selector)
        count = min(links.count(), 20)
        for index in range(count):
            link = links.nth(index)
            href = clean_text(link.get_attribute("href") or "")
            text = get_text_if_exists(link)
            if not href:
                continue
            absolute_url = urljoin(BASE_URL, href)
            if fallback_title and fallback_title in text:
                return absolute_url
            if "/mod/assign/" in urlparse(absolute_url).path:
                return absolute_url

    return detail_page.url


def find_due_text_in_block(text: str) -> str:
    """큰 텍스트 블록 안에서 마감일/제출기한으로 보이는 줄을 찾습니다."""
    patterns = [
        r"(?:제출\s*기한|제출\s*마감|마감(?:일|시간|일시)?|마감일자)\s*:?\s*([^\n\r]+)",
        r"(?:Due date|Cut-off date|Due)\s*:?\s*([^\n\r]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return clean_text(match.group(1))

    return ""


def extract_due_text_from_detail(page: Page) -> str:
    """상세 페이지에서 마감일/시간 문자열을 최대한 찾아냅니다."""
    direct_due_text = first_non_empty_text(
        page,
        [
            ASSIGNMENT_DUE_TEXT_SELECTOR,
            ASSIGNMENT_DUE_DATE_SELECTOR,
            ASSIGNMENT_DUE_TIME_SELECTOR,
        ],
    )
    if direct_due_text:
        return direct_due_text

    text_blocks = [
        first_non_empty_text(page, [".submissionstatustable"]),
        first_non_empty_text(page, [".generaltable"]),
        first_non_empty_text(page, ["#region-main"]),
        first_non_empty_text(page, ["body"]),
    ]

    for text_block in text_blocks:
        if not text_block:
            continue
        due_text = find_due_text_in_block(text_block)
        if due_text:
            return due_text

    return ""


def extract_course_name_from_detail(page: Page, assignment_title: str) -> str:
    """상세 페이지에서 과목명을 찾되, 못 찾으면 기본 문구를 반환합니다."""
    selector_candidates = [
        ASSIGNMENT_COURSE_SELECTOR,
        "nav.breadcrumb li:nth-last-child(2)",
        "nav[aria-label*='breadcrumb'] li:nth-last-child(2)",
        ".breadcrumb .breadcrumb-item:nth-last-child(2)",
        ".page-context-header .page-header-headings h1",
    ]

    for selector in selector_candidates:
        course_name = safe_text(page, selector)
        if not course_name:
            continue
        if clean_text(course_name) == clean_text(assignment_title):
            continue
        return course_name

    return "과목명 미확인"


def extract_title_from_detail(page: Page, fallback_title: str) -> str:
    """상세 페이지에서 과제 제목을 찾고, 없으면 캘린더 제목을 그대로 사용합니다."""
    title = first_non_empty_text(
        page,
        [
            ASSIGNMENT_TITLE_SELECTOR,
            "#page-header h1",
            ".page-header-headings h1",
            "#region-main h1",
            "h1",
        ],
    )
    return title or fallback_title


def build_raw_assignment_from_event(detail_page: Page, event: dict) -> Optional[RawAssignment]:
    """캘린더 이벤트 하나를 과제 데이터로 변환합니다."""
    if not event["event_url"]:
        return None

    detail_page.goto(event["event_url"], wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
    detail_page.wait_for_load_state("domcontentloaded", timeout=PAGE_TIMEOUT_MS)

    resolved_url = resolve_assignment_detail_url(detail_page, event["title"])
    if resolved_url != detail_page.url:
        detail_page.goto(resolved_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        detail_page.wait_for_load_state("domcontentloaded", timeout=PAGE_TIMEOUT_MS)

    final_url = detail_page.url
    is_mod_assign = "/mod/assign/" in urlparse(final_url).path
    is_keyword_match = event["priority_by_keyword"]

    assignment_title = extract_title_from_detail(detail_page, event["title"])
    course_name = extract_course_name_from_detail(detail_page, assignment_title)
    # 제목 키워드도 없고 mod_assign도 아니면 과제가 아닐 가능성이 높습니다.
    if not is_mod_assign and not is_keyword_match:
        return None

    return RawAssignment(
        course_name=course_name or "과목명 미확인",
        title=assignment_title or event["title"],
        due_date_text=event["calendar_date"],
        due_time_text="23:59" if event["calendar_date"] else "",
        due_text="",
        link=final_url or event["event_url"],
        event_id=event["event_id"],
        source_link=event["event_url"],
        due_at=event["due_at"],
    )


def perform_login(page: Page) -> None:
    """환경설정에 따라 수동 로그인 또는 자동 로그인을 수행합니다."""
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)

    if USE_MANUAL_LOGIN:
        print("\n브라우저가 열렸습니다.")
        if GUI_MODE:
            print("이러닝 사이트에 직접 로그인해 주세요. GUI 모드에서는 Enter 입력 없이 자동으로 로그인 완료를 감지합니다.")
            wait_for_manual_login_completion(page)
        else:
            print("이러닝 사이트에 직접 로그인한 뒤, LMS 수강 강좌를 확인할 수 있는 상태에서 Enter를 눌러 주세요.")
            try:
                input("로그인 완료 후 Enter: ")
            except EOFError as error:
                raise RuntimeError(
                    "표준 입력을 읽을 수 없습니다. GUI 실행이라면 GUI_MODE=true로 실행해 주세요."
                ) from error

            if not is_manual_login_completed(page):
                raise RuntimeError("로그인이 완료되지 않았습니다. 로그인 후 다시 시도해 주세요.")
        return

    if not E_LEARNING_ID or not E_LEARNING_PASSWORD:
        raise ValueError(
            "USE_MANUAL_LOGIN=false 인데 E_LEARNING_ID 또는 E_LEARNING_PASSWORD가 비어 있습니다."
        )

    # 자동 로그인은 선택 기능으로만 남겨 두고, 기본값은 USE_MANUAL_LOGIN=true 입니다.
    page.fill(LOGIN_ID_SELECTOR, E_LEARNING_ID)
    page.fill(LOGIN_PASSWORD_SELECTOR, E_LEARNING_PASSWORD)
    page.click(LOGIN_SUBMIT_SELECTOR)
    try:
        page.wait_for_selector(LOGIN_SUCCESS_WAIT_SELECTOR, timeout=PAGE_TIMEOUT_MS)
    except Exception as error:
        raise RuntimeError(
            "로그인 성공 확인 selector를 찾지 못했습니다. "
            f"LOGIN_SUCCESS_WAIT_SELECTOR={LOGIN_SUCCESS_WAIT_SELECTOR!r} / {error}"
        ) from error


def extract_assignments_from_page(page: Page) -> list[RawAssignment]:
    """월간 캘린더에서 이벤트를 수집하고, 각 상세 페이지를 따라가 과제 정보로 정리합니다."""
    if urlparse(BASE_URL).hostname == "lms.inu.ac.kr":
        from src.new_lms import collect_new_lms_assignments
        window_start, window_end = build_collection_window(build_collection_months())
        return collect_new_lms_assignments(page, window_start, window_end)

    calendar_events, _summary, window_start, window_end = collect_calendar_events(page)
    raw_assignments: list[RawAssignment] = []
    seen_calendar_keys = set()
    seen_assignment_keys = set()

    detail_page = page.context.new_page()
    try:
        for event in calendar_events:
            calendar_key = build_calendar_event_dedupe_key(event)
            if calendar_key in seen_calendar_keys:
                continue
            seen_calendar_keys.add(calendar_key)

            try:
                raw_assignment = build_raw_assignment_from_event(detail_page, event)
            except Exception as error:
                print(f"[건너뜀] 이벤트 상세 수집 실패: {event['title']} / {error}")
                continue

            if raw_assignment is None:
                continue

            if raw_assignment.due_at is None:
                print(f"[건너뜀] 마감일 정보가 비어 있습니다: {raw_assignment.title}")
                continue

            if not is_due_at_within_collection_window(raw_assignment.due_at, window_start, window_end):
                print(
                    "[건너뜀] 수집 대상 월 범위를 벗어난 일정입니다: "
                    f"{raw_assignment.title} / {raw_assignment.due_at.strftime('%Y-%m-%d %H:%M')}"
                )
                continue

            dedupe_key = raw_assignment.event_id
            if not dedupe_key:
                dedupe_key = (
                    f"{raw_assignment.link}||{raw_assignment.title}||{raw_assignment.due_at.isoformat()}"
                )

            if dedupe_key in seen_assignment_keys:
                continue

            seen_assignment_keys.add(dedupe_key)
            raw_assignments.append(raw_assignment)
    finally:
        detail_page.close()

    print(f"[INFO] 최종 과제 수: {len(raw_assignments)}개")
    print(f"[과제] 최종 과제로 처리한 이벤트 수: {len(raw_assignments)}개")
    return raw_assignments


def login_and_collect_assignments() -> list[RawAssignment]:
    """브라우저를 열고 로그인한 뒤 과제 목록을 수집합니다."""
    if sync_playwright is None:
        raise RuntimeError(
            "Playwright가 설치되지 않았습니다. "
            "`pip install -r requirements.txt` 후 `playwright install chromium`을 실행해 주세요."
        )

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(headless=HEADLESS, slow_mo=SLOW_MO_MS)
        except Exception as error:
            raise RuntimeError(
                "Playwright Chromium 실행에 실패했습니다. "
                "`playwright install chromium`이 완료되었는지 확인해 주세요."
            ) from error
        context = browser.new_context()
        page = context.new_page()

        try:
            perform_login(page)
            assignments = extract_assignments_from_page(page)
            return assignments
        finally:
            browser.close()
