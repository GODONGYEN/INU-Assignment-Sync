from datetime import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class RawAssignment:
    """브라우저에서 바로 추출한 원본 과제 데이터입니다."""

    course_name: str
    title: str
    due_date_text: str
    due_time_text: str
    due_text: str
    link: str
    event_id: str = ""
    source_link: str = ""
    due_at: Optional[datetime] = None


@dataclass
class NormalizedAssignment:
    """캘린더 등록에 바로 사용할 수 있는 정리된 과제 데이터입니다."""

    external_id: str
    course_name: str
    title: str
    due_at: datetime
    link: str
    event_id: str
    source_url: str
    event_title: str
    notes: str
