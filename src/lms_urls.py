"""Move the retired INU defaults to the new LMS without changing custom hosts."""
from urllib.parse import urlparse

LMS_HOME = "https://lms.inu.ac.kr/"


def migrate_lms_url(value: str) -> str:
    if urlparse(value).hostname == "cyber.inu.ac.kr":
        return LMS_HOME
    return value
