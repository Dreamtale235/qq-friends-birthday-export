"""QQ 好友生日导出工具入口。"""
import argparse
import os
import sys
from pathlib import Path

from auth import clear_saved_session
from logger import setup


def _check_chromium() -> bool:
    """在 Playwright 的常见缓存位置查找 Chromium。"""
    home = Path.home()
    search_dirs = []
    if configured := os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        search_dirs.append(Path(configured).expanduser())
    if local_app_data := os.environ.get("LOCALAPPDATA"):
        search_dirs.append(Path(local_app_data) / "ms-playwright")
    search_dirs.extend([
        home / ".cache" / "ms-playwright",
        home / "Library" / "Caches" / "ms-playwright",
        Path(sys.executable).resolve().parent / "browsers",
        Path.cwd() / "browsers",
    ])

    for directory in dict.fromkeys(search_dirs):
        if not directory.is_dir():
            continue
        if any(
            child.name.startswith("chromium-")
            for child in directory.iterdir()
        ):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(directory)
            return True
    return False


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QQ 好友生日导出工具 v0.4.0")
    parser.add_argument("--cli", action="store_true", help="使用命令行模式")
    parser.add_argument(
        "--remember-session",
        action="store_true",
        help="明确允许将 QQ 登录状态保存到本机",
    )
    parser.add_argument(
        "--clear-session",
        action="store_true",
        help="删除本工具保存的 QQ 登录状态并退出",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.clear_session:
        removed = clear_saved_session()
        print("已清除保存的登录状态。" if removed else "没有找到已保存的登录状态。")
        return

    if args.remember_session and not args.cli:
        parser.error("--remember-session 仅用于 CLI；GUI 请勾选“记住登录状态”")

    setup()

    if not _check_chromium():
        print("=" * 55)
        print("  未找到 Chromium 浏览器内核，请先运行：")
        print("    playwright install chromium")
        print("  下载约 150MB，只需运行一次。")
        print("=" * 55)
        raise SystemExit(1)

    if args.cli:
        from run_cli import run_cli

        run_cli(remember_session=args.remember_session)
        return

    from gui import main as gui_main

    gui_main()


if __name__ == "__main__":
    main()
