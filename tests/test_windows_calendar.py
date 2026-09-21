import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from src.models import RawAssignment
from src.normalizer import normalize_assignment
from src.ics_export import export_calendar
from src.outlook_sync import OutlookCalendar, GraphError


def assignment():
    return normalize_assignment(RawAssignment('한글 과목', '보고서, 제출; 확인\n다음 줄', '', '', '',
        'https://lms.inu.ac.kr/mod/assign/view.php?id=123',
        due_at=datetime(2026, 10, 2, 18, 30, tzinfo=ZoneInfo('Asia/Seoul'))))


class WindowsCalendarTests(unittest.TestCase):
    def test_ics_unicode_folding_utc_and_stable_uid(self):
        item = assignment()
        item.event_title = '한글' * 100 + ',;\nnext'
        with tempfile.TemporaryDirectory() as folder:
            path = export_calendar([item], Path(folder)/'일정.ics', 'INU 과제', 30, [180])
            content = path.read_bytes()
            lines = content.split(b'\r\n')
            self.assertTrue(all(len(line) <= 75 for line in lines))
            self.assertIn(b'DTSTART:20261002T093000Z', content)
            unfolded = content.replace(b'\r\n ', b'').decode()
            self.assertIn('\\,\\;\\nnext', unfolded)
            uid = [x for x in lines if x.startswith(b'UID:')][0]
            self.assertIn(uid, export_calendar([item], path, 'INU 과제', 30, []).read_bytes())

    def test_outlook_utc_payload_and_single_reminder(self):
        client = OutlookCalendar('')
        with patch('src.outlook_sync.REMINDER_MINUTES', [1440, 180]):
            data = client.payload(assignment())
        self.assertEqual(data['start'], {'dateTime': '2026-10-02T09:30:00', 'timeZone': 'UTC'})
        self.assertEqual(data['reminderMinutesBeforeStart'], 180)
        self.assertNotIn('attendees', data)

    def test_remote_identity_search_not_limited_to_due_date(self):
        client = OutlookCalendar('')
        client.calendar_id = 'a/b'
        client.request = Mock(return_value={'value': [{'id': 'stable-id'}]})
        self.assertEqual(client.find_existing_calendar_event(assignment()), 'stable-id')
        path = client.request.call_args.args[1]
        self.assertIn('a%2Fb/events', path)
        self.assertIn('singleValueExtendedProperties', path)
        self.assertNotIn('start', path)

    def test_pagination(self):
        client = OutlookCalendar('')
        client.request = Mock(side_effect=[{'value':[{'id':'1'}], '@odata.nextLink':'https://graph.microsoft.com/v1.0/next'}, {'value':[{'id':'2'}]}])
        self.assertEqual(len(list(client.items('/me/calendars'))), 2)

    def test_update_only_not_found_allows_recreate(self):
        client = OutlookCalendar('')
        client.calendar_id = 'calendar'
        client.request = Mock(side_effect=GraphError(404))
        self.assertIsNone(client.update_calendar_event('id', assignment()))
        client.request = Mock(side_effect=GraphError(403))
        with self.assertRaises(GraphError):
            client.update_calendar_event('id', assignment())

    def test_separate_account_calendar_histories(self):
        def client(account, calendar):
            c = OutlookCalendar('')
            c.login = lambda: setattr(c, 'scope_id', account)
            c.items = lambda _: iter([{'id': calendar, 'name': 'INU 과제'}])
            c.ensure_calendar_exists('INU 과제')
            return c.scope_id
        self.assertNotEqual(client('a','x'), client('b','x'))
        self.assertNotEqual(client('a','x'), client('a','y'))
        self.assertEqual(client('a','x'), client('a','x'))

    def test_missing_client_id_and_untrusted_next_link(self):
        with self.assertRaisesRegex(RuntimeError, '앱 등록 ID'):
            OutlookCalendar('').login()
        with self.assertRaisesRegex(RuntimeError, '잘못된'):
            OutlookCalendar('').request('GET', 'https://example.com/steal')

    def test_duplicate_named_calendars_not_silently_chosen(self):
        client = OutlookCalendar('')
        client.login = Mock()
        client.items = Mock(return_value=iter([{'id':'1','name':'INU'}, {'id':'2','name':'INU'}]))
        with self.assertRaisesRegex(RuntimeError, '여러 개'):
            client.ensure_calendar_exists('INU')
