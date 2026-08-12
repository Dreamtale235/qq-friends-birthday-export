import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from exporter import ExportResult
from pipeline import run_pipeline


class PipelineTestCase(unittest.TestCase):
    def setUp(self):
        self.statuses = []
        self.logs = []
        self.done = []
        self.errors = []
        self.manager = Mock()
        self.manager.check_session_valid.return_value = False
        self.manager.start_browser.return_value = Mock()
        self.manager.login.return_value = True
        self.crawler = Mock()
        self.crawler.navigate_to_calendar.return_value = True
        self.crawler.failed_months = []
        self.crawler.crawl_all_months.return_value = [
            {"name": "测试好友", "birthday": "05-24"}
        ]

    def _run(self, *, cancelled=False, persist_session=False):
        result = ExportResult(Path("birthdays.csv"), Path("birthdays.ics"))
        with (
            patch("pipeline.AuthManager", return_value=self.manager) as manager_class,
            patch("pipeline.QQMailCrawler", return_value=self.crawler),
            patch("pipeline.export_all", return_value=result) as export_all,
        ):
            run_pipeline(
                self.statuses.append,
                lambda current, total: None,
                self.logs.append,
                lambda exported, count, friends: self.done.append(
                    (exported, count, friends)
                ),
                self.errors.append,
                lambda: cancelled,
                persist_session=persist_session,
            )
        return manager_class, export_all

    def test_success_exports_bundle_and_closes_browser(self):
        manager_class, export_all = self._run(persist_session=True)

        manager_class.assert_called_once_with(headless=False, persist_session=True)
        export_all.assert_called_once()
        self.assertEqual(self.done[0][0].ics_path, Path("birthdays.ics"))
        self.manager.close.assert_called_once()
        self.assertFalse(self.errors)

    def test_login_failure_stops_before_crawling(self):
        self.manager.login.return_value = False
        _, export_all = self._run()

        self.crawler.crawl_all_months.assert_not_called()
        export_all.assert_not_called()
        self.assertIn("登录超时或失败", self.errors)
        self.manager.close.assert_called_once()

    def test_calendar_navigation_failure_stops_export(self):
        self.crawler.navigate_to_calendar.return_value = False
        _, export_all = self._run()

        self.crawler.crawl_all_months.assert_not_called()
        export_all.assert_not_called()
        self.assertRegex(self.errors[0], "日历页面")
        self.manager.close.assert_called_once()

    def test_failed_months_do_not_write_partial_backup(self):
        self.crawler.failed_months = [3, 7]
        _, export_all = self._run()

        export_all.assert_not_called()
        self.assertIn("月份处理失败：3、7", self.errors)
        self.assertTrue(any("不完整备份" in log for log in self.logs))

    def test_zero_birthdays_does_not_export(self):
        self.crawler.crawl_all_months.return_value = []
        _, export_all = self._run()

        export_all.assert_not_called()
        self.assertIn("未获取到数据，请查看日志", self.errors)


if __name__ == "__main__":
    unittest.main()
