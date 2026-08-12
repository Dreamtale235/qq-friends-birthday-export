import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from exporter import _build_ics_event, export_all, export_csv, export_ics


FRIENDS = [
    {
        "name": "张三,测试;好友",
        "birthday": "05-24",
        "birth_year": "",
        "zodiac": "双子座",
        "days_until_birthday": 10,
        "remark": "",
    },
    {
        "name": "李四",
        "birthday": "01-02",
        "birth_year": "",
        "zodiac": "摩羯座",
        "days_until_birthday": 200,
        "remark": "",
    },
]


class ExporterTestCase(unittest.TestCase):
    def test_csv_is_sorted_and_utf8_bom(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "birthdays.csv"
            export_csv(FRIENDS, path)

            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
            with open(path, encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual([row["name"] for row in rows], ["李四", "张三,测试;好友"])

    def test_ics_contains_yearly_events_and_two_alarms(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "birthdays.ics"
            export_ics(FRIENDS, path)
            content = path.read_text(encoding="utf-8")

            self.assertEqual(content.count("BEGIN:VEVENT"), 2)
            self.assertEqual(content.count("RRULE:FREQ=YEARLY"), 2)
            self.assertEqual(content.count("TRIGGER:-P7D"), 2)
            self.assertEqual(content.count("TRIGGER:-P1D"), 2)
            self.assertIn(r"SUMMARY:张三\,测试\;好友生日", content)

    def test_ics_uses_crlf_and_folds_utf8_lines(self):
        friend = dict(FRIENDS[0], name="很长的中文好友名字" * 12)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "birthdays.ics"
            export_ics([friend], path)
            raw = path.read_bytes()

            self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
            for line in raw.split(b"\r\n"):
                self.assertLessEqual(len(line), 75)

    def test_uid_is_stable_and_feb_29_maps_to_feb_28(self):
        friend = dict(FRIENDS[0], birthday="02-29")
        first = _build_ics_event(friend, date(2026, 1, 1), "20260101T000000Z")
        second = _build_ics_event(friend, date(2026, 1, 1), "20260101T000000Z")

        first_uid = next(line for line in first if line.startswith("UID:"))
        second_uid = next(line for line in second if line.startswith("UID:"))
        self.assertEqual(first_uid, second_uid)
        self.assertIn("DTSTART;VALUE=DATE:20260228", first)
        self.assertIn("DESCRIPTION:来源：QQ 邮箱好友生日日历；原始日期：02-29", first)

    def test_bundle_uses_matching_non_overwriting_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            first = export_all(FRIENDS, output_dir)
            second = export_all(FRIENDS, output_dir)

            self.assertEqual(first.csv_path.stem, first.ics_path.stem)
            self.assertEqual(second.csv_path.stem, second.ics_path.stem)
            self.assertNotEqual(first.csv_path.stem, second.csv_path.stem)
            self.assertTrue(second.csv_path.stem.endswith("_2"))

    def test_invalid_birthday_fails_instead_of_silently_skipping(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "birthdays.ics"
            with self.assertRaisesRegex(ValueError, "无效生日日期"):
                export_ics([dict(FRIENDS[0], birthday="02-31")], path)

    def test_bundle_removes_csv_when_ics_export_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            with self.assertRaisesRegex(ValueError, "无效生日日期"):
                export_all([dict(FRIENDS[0], birthday="02-31")], output_dir)
            self.assertEqual(list(output_dir.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
