import sqlite3
from datetime import datetime
from pathlib import Path

from src.config import CALENDAR_NAME, DATABASE_PATH
from src.models import NormalizedAssignment


class SQLiteSyncStore:
    """과제와 캘린더 일정의 연결 정보를 SQLite에 저장합니다."""

    def __init__(self, database_path: Path = DATABASE_PATH) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self) -> None:
        """처음 실행할 때 필요한 테이블을 만들어 둡니다."""
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS assignment_sync (
                    external_id TEXT PRIMARY KEY,
                    course_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    link TEXT,
                    event_id TEXT,
                    source_url TEXT,
                    due_at_iso TEXT NOT NULL,
                    calendar_name TEXT NOT NULL,
                    event_uid TEXT NOT NULL,
                    event_title TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._ensure_column(connection, "assignment_sync", "event_id", "TEXT")
            self._ensure_column(connection, "assignment_sync", "source_url", "TEXT")
            connection.commit()

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_definition: str,
    ) -> None:
        """기존 DB를 깨지 않도록 누락된 컬럼만 추가합니다."""
        columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        existing_column_names = {column["name"] for column in columns}
        if column_name in existing_column_names:
            return
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")

    def get_assignment(self, external_id: str):
        """과제 고유 ID로 기존 동기화 이력을 조회합니다."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    external_id,
                    course_name,
                    title,
                    link,
                    event_id,
                    source_url,
                    due_at_iso,
                    calendar_name,
                    event_uid,
                    event_title,
                    updated_at
                FROM assignment_sync
                WHERE external_id = ?
                """,
                (external_id,),
            ).fetchone()
            return row

    def upsert_assignment(self, assignment: NormalizedAssignment, event_uid: str) -> None:
        """신규 저장과 기존 갱신을 한 번에 처리합니다."""
        now_iso = datetime.now().isoformat(timespec="seconds")

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO assignment_sync (
                    external_id,
                    course_name,
                    title,
                    link,
                    event_id,
                    source_url,
                    due_at_iso,
                    calendar_name,
                    event_uid,
                    event_title,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(external_id) DO UPDATE SET
                    course_name = excluded.course_name,
                    title = excluded.title,
                    link = excluded.link,
                    event_id = excluded.event_id,
                    source_url = excluded.source_url,
                    due_at_iso = excluded.due_at_iso,
                    calendar_name = excluded.calendar_name,
                    event_uid = excluded.event_uid,
                    event_title = excluded.event_title,
                    updated_at = excluded.updated_at
                """,
                (
                    assignment.external_id,
                    assignment.course_name,
                    assignment.title,
                    assignment.link,
                    assignment.event_id,
                    assignment.source_url,
                    assignment.due_at.isoformat(),
                    CALENDAR_NAME,
                    event_uid,
                    assignment.event_title,
                    now_iso,
                ),
            )
            connection.commit()
