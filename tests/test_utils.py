import unittest
from datetime import date

from utils import _next_birthday, calc_zodiac, parse_birthday_date


class UtilsTestCase(unittest.TestCase):
    def test_calc_zodiac_boundaries(self):
        self.assertEqual(calc_zodiac(1, 19), "摩羯座")
        self.assertEqual(calc_zodiac(1, 20), "水瓶座")
        self.assertEqual(calc_zodiac(12, 21), "射手座")
        self.assertEqual(calc_zodiac(12, 22), "摩羯座")

    def test_next_birthday_keeps_future_date_in_current_year(self):
        self.assertEqual(_next_birthday(date(2026, 5, 24), 6, 1), date(2026, 6, 1))

    def test_next_birthday_moves_past_date_to_next_year(self):
        self.assertEqual(_next_birthday(date(2026, 5, 24), 5, 1), date(2027, 5, 1))

    def test_next_birthday_handles_feb_29_in_common_year(self):
        self.assertEqual(_next_birthday(date(2026, 1, 1), 2, 29), date(2026, 2, 28))

    def test_parse_birthday_date(self):
        cases = [
            ("05-24", (5, 24)),
            ("5/24", (5, 24)),
            ("5 月 24 日", (5, 24)),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(parse_birthday_date(raw), expected)


if __name__ == "__main__":
    unittest.main()
