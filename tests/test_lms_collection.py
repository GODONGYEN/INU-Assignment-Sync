"""Offline browser fixtures based on the labels/links observed in Chrome.
These verify the collector, not the production DOM or authentication session.
"""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright
from src.new_lms import collect_new_lms_assignments


class CollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def collect(self, broken=False):
        context = self.browser.new_context()
        def serve(route):
            url = route.request.url
            if '/local/ubion/' in url:
                html = '''<title>테스트 강좌 | 인천대학교 LMS</title>
                  <h2>학습활동 모아보기</h2><table><tr><td>
                  <a href="/mod/assign/view.php?id=100">키워드 없는 보고서</a>
                  <a href="/mod/assign/view.php?id=100#main">중복</a>
                  <a href="/mod/assign/view.php?id=200">기한 없는 과제</a>
                  <a href="/mod/assign/view.php?id=300">범위 밖 과제</a>
                  <a href="/mod/vod/view.php?id=400">동영상</a>
                  </td></tr></table>'''
            elif '/mod/assign/' in url:
                deadline = ('2026-02-30 18:30:00' if broken else '2026-10-02 18:30:00')
                if 'id=200' in url:
                    deadline = '-'
                if 'id=300' in url:
                    deadline = '2027-10-02 18:30:00'
                html = '<h5>과제 정보</h5><li>종료 일시 ' + deadline + '</li>'
            else:
                html = '''<button>수강 강좌</button><a href="/course/view.php?id=42">테스트 강좌</a>
                <a href="/course/view.php?id=42&mode=sections">같은 강좌</a>'''
            route.fulfill(status=200, content_type='text/html; charset=utf-8', body=html)
        context.route('**/*', serve)
        try:
            return collect_new_lms_assignments(context.new_page(),
                datetime(2026, 9, 1, tzinfo=ZoneInfo('Asia/Seoul')),
                datetime(2026, 11, 1, tzinfo=ZoneInfo('Asia/Seoul')))
        finally:
            context.close()

    def test_courses_details_deduplication_and_window(self):
        assignments = self.collect()
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].course_name, '테스트 강좌')
        self.assertEqual(assignments[0].title, '키워드 없는 보고서')
        self.assertEqual(assignments[0].due_at.hour, 18)

    def test_invalid_date_stops_partial_sync(self):
        with self.assertRaisesRegex(RuntimeError, '동기화를 중단'):
            self.collect(broken=True)
