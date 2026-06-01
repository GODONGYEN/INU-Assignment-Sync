import os
from pathlib import Path

from dotenv import load_dotenv


# 개발 환경에서는 프로젝트 루트를, 패키징 앱에서는 Electron이 넘겨준 앱 데이터 경로를 사용합니다.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"
README_PATH = PROJECT_ROOT / "README.md"
APP_DATA_DIR = Path(os.getenv("INU_SYNC_APP_DATA_DIR", str(PROJECT_ROOT))).expanduser()
ENV_PATH = Path(os.getenv("INU_SYNC_ENV_PATH", str(APP_DATA_DIR / ".env"))).expanduser()
LOGS_DIR = Path(os.getenv("INU_SYNC_LOGS_DIR", str(APP_DATA_DIR / "logs"))).expanduser()
LOG_FILE_PATH = LOGS_DIR / "app.log"
DATA_DIR = Path(os.getenv("INU_SYNC_DATA_DIR", str(APP_DATA_DIR / "data"))).expanduser()

load_dotenv(ENV_PATH)


def get_bool(env_name: str, default: bool) -> bool:
    """문자열 환경변수를 True/False로 바꿔 줍니다."""
    value = os.getenv(env_name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_int(env_name: str, default: int) -> int:
    """정수 환경변수가 비어 있으면 기본값을 사용합니다."""
    value = os.getenv(env_name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def get_list(env_name: str, default: list[str]) -> list[str]:
    """쉼표로 구분된 환경변수를 문자열 목록으로 바꿉니다."""
    value = os.getenv(env_name)
    if value is None or value.strip() == "":
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


def get_int_list(env_name: str, default: list[int]) -> list[int]:
    """쉼표로 구분된 환경변수를 정수 목록으로 바꿉니다."""
    values = get_list(env_name, [str(item) for item in default])
    return [int(value) for value in values]


# --------------------------------------------
# 사이트 정보
# --------------------------------------------
LOGIN_URL = os.getenv("LOGIN_URL", "https://cyber.inu.ac.kr/login.php")
ASSIGNMENTS_URL = os.getenv("ASSIGNMENTS_URL", "https://cyber.inu.ac.kr/calendar/view.php?view=month")
BASE_URL = os.getenv("BASE_URL", "https://cyber.inu.ac.kr")


# --------------------------------------------
# 로그인 정보
# --------------------------------------------
USE_MANUAL_LOGIN = get_bool("USE_MANUAL_LOGIN", True)
GUI_MODE = get_bool("GUI_MODE", False)
E_LEARNING_ID = os.getenv("E_LEARNING_ID", "")
E_LEARNING_PASSWORD = os.getenv("E_LEARNING_PASSWORD", "")


# --------------------------------------------
# 브라우저 실행 옵션
# --------------------------------------------
HEADLESS = get_bool("HEADLESS", False)
SLOW_MO_MS = get_int("SLOW_MO_MS", 0)
PAGE_TIMEOUT_MS = get_int("PAGE_TIMEOUT_MS", 15000)
LOGIN_WAIT_TIMEOUT_MS = get_int("LOGIN_WAIT_TIMEOUT_MS", 180000)


# --------------------------------------------
# 캘린더 / DB 설정
# --------------------------------------------
CALENDAR_NAME = os.getenv("CALENDAR_NAME", "INU 과제")
EVENT_DURATION_MINUTES = get_int("EVENT_DURATION_MINUTES", 30)
TIMEZONE = os.getenv("TIMEZONE", "Asia/Seoul")
database_path_value = os.getenv("DATABASE_PATH", "data/sync_state.sqlite3")
DATABASE_PATH = Path(database_path_value).expanduser()
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = APP_DATA_DIR / database_path_value
CALENDAR_MONTHS_BACK = get_int("CALENDAR_MONTHS_BACK", 2)
CALENDAR_MONTHS_FORWARD = get_int("CALENDAR_MONTHS_FORWARD", 6)
INCLUDE_PAST_ASSIGNMENTS = get_bool("INCLUDE_PAST_ASSIGNMENTS", False)
DRY_RUN = get_bool("DRY_RUN", True)
REMINDER_MINUTES = get_int_list("REMINDER_MINUTES", [1440, 180])


# --------------------------------------------
# 로그인 selector 예시
# 실제 사이트 구조에 맞게 자유롭게 바꾸면 됩니다.
# --------------------------------------------
LOGIN_ID_SELECTOR = os.getenv("LOGIN_ID_SELECTOR", "input[name='username']")
LOGIN_PASSWORD_SELECTOR = os.getenv("LOGIN_PASSWORD_SELECTOR", "input[name='password']")
LOGIN_SUBMIT_SELECTOR = os.getenv("LOGIN_SUBMIT_SELECTOR", "input[name='loginbutton']")
LOGIN_SUCCESS_WAIT_SELECTOR = os.getenv("LOGIN_SUCCESS_WAIT_SELECTOR", "body:not(#page-login-index)")


# --------------------------------------------
# 캘린더 / 과제 selector 예시
# 실제 사이트 구조에 맞게 자유롭게 바꾸면 됩니다.
# --------------------------------------------
CALENDAR_TABLE_SELECTOR = os.getenv("CALENDAR_TABLE_SELECTOR", "table.calendarmonth.calendartable")
CURRENT_MONTH_SELECTOR = os.getenv("CURRENT_MONTH_SELECTOR", "h2.current")
CALENDAR_EVENT_SELECTOR = os.getenv("CALENDAR_EVENT_SELECTOR", "ul.events-new li.calendar_event_course")
CALENDAR_EVENT_LINK_SELECTOR = os.getenv("CALENDAR_EVENT_LINK_SELECTOR", "a")
CALENDAR_DAY_CELL_SELECTOR = os.getenv("CALENDAR_DAY_CELL_SELECTOR", "td.day, td.duration_course")
CALENDAR_DAY_NUMBER_SELECTOR = os.getenv("CALENDAR_DAY_NUMBER_SELECTOR", "div.day")

ASSIGNMENT_ROW_SELECTOR = os.getenv("ASSIGNMENT_ROW_SELECTOR", ".assignment-row")
ASSIGNMENT_COURSE_SELECTOR = os.getenv("ASSIGNMENT_COURSE_SELECTOR", ".course-name")
ASSIGNMENT_TITLE_SELECTOR = os.getenv("ASSIGNMENT_TITLE_SELECTOR", ".assignment-title")
ASSIGNMENT_DUE_DATE_SELECTOR = os.getenv("ASSIGNMENT_DUE_DATE_SELECTOR", ".due-date")
ASSIGNMENT_DUE_TIME_SELECTOR = os.getenv("ASSIGNMENT_DUE_TIME_SELECTOR", ".due-time")
ASSIGNMENT_DUE_TEXT_SELECTOR = os.getenv("ASSIGNMENT_DUE_TEXT_SELECTOR", ".due-datetime")
ASSIGNMENT_LINK_SELECTOR = os.getenv("ASSIGNMENT_LINK_SELECTOR", "a.assignment-link")


# --------------------------------------------
# 캘린더 이벤트 제목 필터
# --------------------------------------------
INCLUDE_KEYWORDS = get_list(
    "INCLUDE_KEYWORDS",
    ["과제", "assignment", "Assign", "Submission", "제출", "연습문제", "lab", "quiz"],
)
