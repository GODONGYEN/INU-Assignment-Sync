import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.lms_urls import migrate_lms_url
from src.new_lms import canonical_activity_url, parse_assignment_deadline
from src.normalizer import normalize_link_for_identity
from src.scraper import is_manual_login_completed


class NewLmsTests(unittest.TestCase):
    def test_end_time_precedes_opening_time(self):
        text = '제출 기간\n2026-09-15 00:00:00 ~ 2026-10-02 18:30:00\n종료 일시 2026-10-02 18:30:00'
        self.assertEqual(parse_assignment_deadline(text), datetime(2026, 10, 2, 18, 30, tzinfo=ZoneInfo('Asia/Seoul')))

    def test_period_fallback(self):
        self.assertEqual(parse_assignment_deadline('제출 기간\n2026-09-15 00:00 ~ 2026-10-02 23:59').day, 2)

    def test_missing_or_invalid_deadline(self):
        for text in ['종료 일시 -', '남은 기한 종료 일시까지 11 일 남음', '종료 일시 2026-02-30 23:59:00']:
            self.assertIsNone(parse_assignment_deadline(text))

    def test_url_migration(self):
        self.assertEqual(migrate_lms_url('https://cyber.inu.ac.kr/login.php'), 'https://lms.inu.ac.kr/')
        self.assertEqual(migrate_lms_url('https://example.org/login.php'), 'https://example.org/login.php')

    def test_stable_identity_separates_lms_databases(self):
        old = normalize_link_for_identity('https://cyber.inu.ac.kr/mod/assign/view.php?id=123')
        new = normalize_link_for_identity('https://lms.inu.ac.kr/mod/assign/view.php?id=123')
        self.assertNotEqual(old, new)
        self.assertEqual(new, normalize_link_for_identity('https://lms.inu.ac.kr/mod/assign/view.php?id=123&x=1#main'))

    def test_link_dedupe_and_external_rejection(self):
        self.assertEqual(canonical_activity_url('/course/view.php?id=42&mode=sections#section-3', '/course/view.php'), 'https://lms.inu.ac.kr/course/view.php?id=42')
        self.assertEqual(canonical_activity_url('https://example.org/course/view.php?id=42', '/course/view.php'), '')

    def test_sso_and_public_home_are_not_logged_in(self):
        class Page:
            url = 'https://sso.inu.ac.kr/'
        with patch('src.scraper.safe_locator_count', return_value=0):
            self.assertFalse(is_manual_login_completed(Page()))
            Page.url = 'https://lms.inu.ac.kr/'
            self.assertFalse(is_manual_login_completed(Page()))
        with patch('src.scraper.safe_locator_count', side_effect=lambda p, s: int('/course/view.php' in s)):
            self.assertTrue(is_manual_login_completed(Page()))


if __name__ == '__main__':
    unittest.main()
