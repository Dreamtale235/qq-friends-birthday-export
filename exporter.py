"""CSV 与 iCalendar 导出器。"""
import csv
import hashlib
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from config import DATA_DIR

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExportResult:
    """一次完整导出的两个文件。"""

    csv_path: Path
    ics_path: Path


def export_csv(friends: list[dict], output_path: Path | None = None) -> Path:
    """将好友生日列表导出为 CSV（UTF-8 with BOM）。"""
    if output_path is None:
        today = date.today().strftime("%Y-%m-%d")
        output_path = _next_available_path(
            DATA_DIR / f"qq_friends_birthdays_{today}.csv"
        )

    friends_sorted = sorted(
        friends,
        key=lambda friend: friend.get("birthday", "99-99"),
    )
    fieldnames = [
        "name", "birthday", "birth_year", "zodiac",
        "days_until_birthday", "remark",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(friends_sorted)

    logger.info("已导出 %s 位好友生日 → %s", len(friends_sorted), output_path)
    return output_path


def export_ics(friends: list[dict], output_path: Path | None = None) -> Path:
    """导出可导入主流日历应用的年度生日事件。"""
    if output_path is None:
        today = date.today().strftime("%Y-%m-%d")
        output_path = _next_available_path(
            DATA_DIR / f"qq_friends_birthdays_{today}.ics"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    exported_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    today = date.today()
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Dreamtale235//QQ Friends Birthday Exporter 0.4.0//ZH-CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:QQ好友生日",
        "X-WR-CALDESC:从 QQ 邮箱好友生日日历导出的年度提醒",
    ]

    for friend in sorted(friends, key=lambda item: item.get("birthday", "99-99")):
        lines.extend(_build_ics_event(friend, today, exported_at))

    lines.append("END:VCALENDAR")
    content = "\r\n".join(_fold_ics_line(line) for line in lines) + "\r\n"
    with open(output_path, "w", encoding="utf-8", newline="") as file:
        file.write(content)

    logger.info("已导出 %s 位好友生日 → %s", len(friends), output_path)
    return output_path


def export_all(friends: list[dict], output_dir: Path | None = None) -> ExportResult:
    """使用统一文件名同时导出 CSV 和 ICS。"""
    output_dir = output_dir or DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"qq_friends_birthdays_{date.today():%Y-%m-%d}"
    csv_path, ics_path = _next_available_bundle(output_dir, stem)
    try:
        export_csv(friends, csv_path)
        export_ics(friends, ics_path)
    except Exception:
        csv_path.unlink(missing_ok=True)
        ics_path.unlink(missing_ok=True)
        raise
    return ExportResult(csv_path=csv_path, ics_path=ics_path)


def _build_ics_event(friend: dict, today: date, exported_at: str) -> list[str]:
    name = str(friend.get("name", "")).strip()
    birthday = str(friend.get("birthday", "")).strip()
    if not name:
        raise ValueError("ICS 导出遇到空好友名称")

    try:
        month_text, day_text = birthday.split("-", maxsplit=1)
        month, day = int(month_text), int(day_text)
        date(2000, month, day)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"无效生日日期：{birthday!r}") from exc

    original_birthday = birthday
    if (month, day) == (2, 29):
        day = 28

    start = date(today.year, month, day)
    if start < today:
        start = date(today.year + 1, month, day)
    end = start + timedelta(days=1)

    digest = hashlib.sha256(
        f"{name}\0{original_birthday}".encode("utf-8")
    ).hexdigest()[:32]
    summary = _escape_ics_text(f"{name}生日")
    description = _escape_ics_text(
        f"来源：QQ 邮箱好友生日日历；原始日期：{original_birthday}"
    )
    alarm_description = _escape_ics_text(f"{name}生日提醒")

    return [
        "BEGIN:VEVENT",
        f"UID:{digest}@qq-friends-birthday-export",
        f"DTSTAMP:{exported_at}",
        f"DTSTART;VALUE=DATE:{start:%Y%m%d}",
        f"DTEND;VALUE=DATE:{end:%Y%m%d}",
        "RRULE:FREQ=YEARLY",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "TRIGGER:-P7D",
        f"DESCRIPTION:{alarm_description}",
        "END:VALARM",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "TRIGGER:-P1D",
        f"DESCRIPTION:{alarm_description}",
        "END:VALARM",
        "END:VEVENT",
    ]


def _escape_ics_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def _fold_ics_line(line: str) -> str:
    """按 RFC 5545 将内容行折叠到最多 75 个 UTF-8 字节。"""
    chunks: list[str] = []
    current = ""
    for char in line:
        if len((current + char).encode("utf-8")) > 75:
            chunks.append(current)
            current = " " + char
        else:
            current += char
    chunks.append(current)
    return "\r\n".join(chunks)


def _next_available_bundle(output_dir: Path, stem: str) -> tuple[Path, Path]:
    index = 1
    while True:
        suffix = "" if index == 1 else f"_{index}"
        csv_path = output_dir / f"{stem}{suffix}.csv"
        ics_path = output_dir / f"{stem}{suffix}.ics"
        if not csv_path.exists() and not ics_path.exists():
            return csv_path, ics_path
        index += 1


def _next_available_path(path: Path) -> Path:
    """避免覆盖已有的单个导出文件。"""
    if not path.exists():
        return path

    index = 2
    while True:
        candidate = path.parent / f"{path.stem}_{index}{path.suffix}"
        if not candidate.exists():
            return candidate
        index += 1
