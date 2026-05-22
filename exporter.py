"""CSV 导出器"""
import csv
import logging
from pathlib import Path

from config import DATA_DIR

logger = logging.getLogger(__name__)


def export_csv(friends: list[dict], output_path: Path | None = None) -> Path:
    """将好友生日列表导出为 CSV（UTF-8 with BOM）

    Args:
        friends: [{"name": ..., "birthday": "MM-DD", ...}, ...]
        output_path: 输出路径，默认自动生成带日期的文件名

    Returns:
        实际写入的文件路径
    """
    from datetime import date

    if output_path is None:
        today = date.today().strftime("%Y-%m-%d")
        output_path = DATA_DIR / f"qq_friends_birthdays_{today}.csv"

    # 按生日日期排序（MM-DD）
    friends_sorted = sorted(
        friends,
        key=lambda f: f.get("birthday", "99-99"),
    )

    fieldnames = [
        "name", "birthday", "birth_year", "zodiac",
        "days_until_birthday", "remark",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(friends_sorted)

    logger.info(f"已导出 {len(friends_sorted)} 位好友生日 → {output_path}")
    return output_path
