import unittest
from unittest.mock import Mock, patch

from crawler import QQMailCrawler


class CrawlerTestCase(unittest.TestCase):
    def test_calendar_ready_requires_visible_grid(self):
        page = Mock()
        crawler = QQMailCrawler(page)

        self.assertTrue(crawler._wait_for_calendar_ready())
        page.wait_for_selector.assert_called_once_with(
            ".grid-cell",
            state="visible",
            timeout=10000,
        )

    def test_month_navigation_failures_are_recorded(self):
        page = Mock()
        page.is_closed.return_value = False
        crawler = QQMailCrawler(page)

        with (
            patch.object(crawler, "_navigate_to_month", return_value=False),
            patch.object(crawler, "_random_delay"),
        ):
            with self.assertLogs("crawler", level="WARNING"):
                friends = crawler.crawl_all_months()

        self.assertEqual(friends, [])
        self.assertEqual(crawler.failed_months, list(range(1, 13)))


if __name__ == "__main__":
    unittest.main()
