"""命令行模式（python main.py --cli 或直接运行此文件）"""
import logging
import sys

from logger import setup
from pipeline import run_pipeline


def run_cli():
    setup()
    logger = logging.getLogger(__name__)

    # 强制 UTF-8 避免特殊字符导致 GBK 编码错误
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 50)
    print("  QQ 好友生日导出工具 v0.2 (CLI)")
    print("=" * 50)
    print()

    _cancelled = False

    def on_status(msg: str):
        print(f"  [{msg}]")

    def on_progress(cur: int, tot: int):
        print(f"  进度：{cur}/{tot} 月")

    def on_log(msg: str):
        logger.info(f"  → {msg}")

    def on_done(path, count, friends):
        nonlocal _cancelled
        _cancelled = True
        print()
        print(f"  Done! 文件：{path}")
        print(f"  Done! 共 {count} 位好友生日")
        print()

        # 预览最近生日
        preview = sorted(friends, key=lambda f: f.get("days_until_birthday", 999))[:10]
        print("  ── 最近生日预览（前 10 位）──")
        for f_row in preview:
            name = f_row['name'][:12]
            print(f"  {f_row['birthday']}  {name:12s}  {f_row.get('zodiac', ''):4s}  {f_row.get('days_until_birthday', '?')} 天后")
        print()

    def on_error(msg: str):
        logger.error(msg)

    def is_cancelled() -> bool:
        return _cancelled

    run_pipeline(on_status, on_progress, on_log, on_done, on_error, is_cancelled)


if __name__ == "__main__":
    run_cli()
