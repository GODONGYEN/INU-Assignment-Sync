"""Collector for the INU Ubion LMS, inspected in Chrome on 2026-09-21."""
import re
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from src.config import ASSIGNMENTS_URL, BASE_URL, PAGE_TIMEOUT_MS
from src.models import RawAssignment
from src.normalizer import clean_text, parse_due_datetime

COURSE_PATH = "/course/view.php"
ASSIGN_PATH = "/mod/assign/view.php"
DATE_TIME = r"\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?"


def parse_assignment_deadline(text):
    """Use the explicit end time, never the opening time or 'remaining days'."""
    match = re.search(r"종료\s*일시\s*:?\s*(" + DATE_TIME + r")", text)
    if not match:
        match = re.search(
            r"제출\s*기간\s*:?\s*" + DATE_TIME + r"\s*[~～–]\s*(" + DATE_TIME + r")",
            text,
        )
    if not match:
        match = re.search(
            r"(?:제출\s*기한|마감\s*일시|Due date)\s*:?\s*(" + DATE_TIME + r")",
            text, re.IGNORECASE,
        )
    return parse_due_datetime("", "", match.group(1)) if match else None


def canonical_activity_url(href, path):
    parsed = urlparse(urljoin(BASE_URL + "/", href))
    item_id = parse_qs(parsed.query).get("id", [""])[0]
    if (parsed.hostname != urlparse(BASE_URL).hostname or parsed.path != path
            or not item_id.isdigit()):
        return ""
    return f"{BASE_URL}{path}?{urlencode({'id': item_id})}"


def collect_links(page, path):
    result = {}
    links = page.locator(f'a[href*="{path}"]')
    for index in range(links.count()):
        link = links.nth(index)
        url = canonical_activity_url(link.get_attribute("href") or "", path)
        if url and url not in result:
            result[url] = clean_text(link.get_attribute("title") or link.text_content() or "")
    return result


def ensure_lms_page(page):
    if urlparse(page.url).hostname != urlparse(BASE_URL).hostname:
        raise RuntimeError("LMS 밖으로 이동했습니다. 로그인 상태를 확인한 뒤 다시 실행하세요.")
    if page.locator('input[type="password"]').count() or "/login" in urlparse(page.url).path:
        raise RuntimeError("LMS 로그인 세션이 만료되었습니다. 다시 로그인해 주세요.")


def collect_new_lms_assignments(page, window_start, window_end):
    page.goto(ASSIGNMENTS_URL, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
    ensure_lms_page(page)
    # The enrolled-courses menu contains every course; the home carousel only
    # shows three at a time, and this week's todo list omits older assignments.
    menu = page.get_by_text("수강 강좌", exact=True)
    if menu.count() and menu.first.is_visible():
        menu.first.click()
    try:
        page.locator(f'a[href*="{COURSE_PATH}"]').first.wait_for(
            state="attached", timeout=PAGE_TIMEOUT_MS)
    except Exception as error:
        raise RuntimeError("수강 강좌 목록을 찾지 못했습니다. 로그인 또는 LMS 화면을 확인하세요.") from error
    courses = collect_links(page, COURSE_PATH)
    if not courses:
        raise RuntimeError("수강 강좌 목록을 읽지 못했습니다.")
    print(f"[INFO] 수강 강좌 수: {len(courses)}개")
    assignments = []
    seen = set()
    failures = []
    detail = page.context.new_page()
    try:
        for course_url in courses:
            course_id = parse_qs(urlparse(course_url).query)["id"][0]
            activities_url = f"{BASE_URL}/local/ubion/course/activities.php?id={course_id}"
            try:
                page.goto(activities_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
                ensure_lms_page(page)
                page.get_by_role("heading", name="학습활동 모아보기", exact=True).wait_for(
                    timeout=PAGE_TIMEOUT_MS)
                page.get_by_role("table").first.wait_for(state="attached", timeout=PAGE_TIMEOUT_MS)
                course_name = clean_text(page.title().split("|")[0])
                links = collect_links(page, ASSIGN_PATH)
                print(f"[INFO] 강좌 과제 수: {course_name} / {len(links)}개")
                for assignment_url, title in links.items():
                    if assignment_url in seen:
                        continue
                    seen.add(assignment_url)
                    detail.goto(assignment_url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
                    ensure_lms_page(detail)
                    detail.get_by_role("heading", name="과제 정보", exact=True).wait_for(
                        timeout=PAGE_TIMEOUT_MS)
                    text = detail.locator("body").inner_text()
                    due_at = parse_assignment_deadline(text)
                    if due_at is None:
                        # A changed date format must not silently become today's deadline.
                        if re.search(r"종료\s*일시\s*:?\s*\d", text):
                            raise RuntimeError(f"과제 마감일 형식을 읽을 수 없습니다: {title}")
                        print(f"[건너뜀] 마감일이 없는 과제: {title}")
                        continue
                    if not window_start <= due_at < window_end:
                        continue
                    if not title:
                        raise RuntimeError("과제 제목을 읽지 못했습니다.")
                    assignments.append(RawAssignment(
                        course_name=course_name, title=title,
                        due_date_text=due_at.strftime("%Y-%m-%d"),
                        due_time_text=due_at.strftime("%H:%M:%S"), due_text="",
                        link=assignment_url, source_link=assignment_url, due_at=due_at,
                    ))
            except Exception as error:
                failures.append(f"강좌 {course_id}: {error}")
    finally:
        detail.close()
    if failures:
        raise RuntimeError("일부 강좌 수집에 실패해 동기화를 중단합니다. " + " / ".join(failures))
    print(f"[INFO] 최종 과제 수: {len(assignments)}개")
    return assignments
