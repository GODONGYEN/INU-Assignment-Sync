import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import main
from src.models import RawAssignment


class SyncModeTests(unittest.TestCase):
    def run_main(self, folder, mode, dry, outlook=None):
        raw = RawAssignment('과목', '과제', '', '', '', 'https://lms.inu.ac.kr/mod/assign/view.php?id=42',
            due_at=datetime(2099, 1, 1, 12, tzinfo=ZoneInfo('Asia/Seoul')))
        with ExitStack() as stack:
            for name, value in {
                'CALENDAR_BACKEND': mode, 'DRY_RUN': dry,
                'ENV_PATH': Path(folder), 'DATABASE_PATH': Path(folder)/'state.sqlite3',
                'ICS_PATH': Path(folder)/'output.ics',
            }.items():
                stack.enter_context(patch.object(main, name, value))
            stack.enter_context(patch.object(main, 'setup_file_logging', return_value=Mock()))
            stack.enter_context(patch.object(main, 'attach_stdout_stderr_to_logger'))
            stack.enter_context(patch.object(main, 'login_and_collect_assignments', return_value=[raw]))
            apple = stack.enter_context(patch.object(main.apple_calendar, 'ensure_calendar_exists'))
            if outlook is not None:
                stack.enter_context(patch('src.outlook_sync.OutlookCalendar', return_value=outlook))
            main.main()
            apple.assert_not_called()

    def test_ics_preview_writes_no_file_or_sync_history(self):
        with tempfile.TemporaryDirectory() as folder:
            self.run_main(folder, 'ics', True)
            self.assertEqual(list(Path(folder).iterdir()), [])
            self.run_main(folder, 'ics', False)
            self.assertTrue((Path(folder)/'output.ics').exists())
            self.assertFalse((Path(folder)/'state.sqlite3').exists())

    def test_outlook_dry_run_never_logs_in_or_mutates_remote(self):
        client = Mock(scope_id=None)
        with tempfile.TemporaryDirectory() as folder:
            self.run_main(folder, 'outlook', True, client)
        client.ensure_calendar_exists.assert_not_called()
        client.create_calendar_event.assert_not_called()
        client.update_calendar_event.assert_not_called()
        client.find_existing_calendar_event.assert_not_called()

    def test_outlook_rerun_skips_and_deleted_event_is_recreated(self):
        client = Mock(scope_id='account-calendar', create_calendar_event=Mock(return_value='event-id'))
        client.find_existing_calendar_event.side_effect = [None, 'event-id', None]
        with tempfile.TemporaryDirectory() as folder:
            self.run_main(folder, 'outlook', False, client)
            self.run_main(folder, 'outlook', False, client)
            self.assertEqual(client.create_calendar_event.call_count, 1)
            self.run_main(folder, 'outlook', False, client)
            self.assertEqual(client.create_calendar_event.call_count, 2)
