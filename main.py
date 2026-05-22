"""QQ 好友生日导出工具 — 入口"""
import os
import sys

from logger import setup


def _check_chromium():
    """检查 Chromium 是否已安装（在多个可能位置搜索）"""
    search_dirs = [
        os.path.join(os.path.expanduser("~"), "AppData", "Local", "ms-playwright"),
        os.path.join(os.path.dirname(sys.executable), "browsers"),
        os.path.join(os.getcwd(), "browsers"),
    ]
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        search_dirs.insert(0, os.environ["PLAYWRIGHT_BROWSERS_PATH"])

    for d in search_dirs:
        if os.path.isdir(d):
            for name in os.listdir(d):
                if name.startswith("chromium-"):
                    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = d
                    return True
    return False


def main():
    setup()

    if not _check_chromium():
        print("=" * 55)
        print("  未找到 Chromium 浏览器内核，请先运行：")
        print("    playwright install chromium")
        print("  下载约 150MB，只需运行一次。")
        print("=" * 55)
        sys.exit(1)

    # CLI 模式：python main.py --cli
    if "--cli" in sys.argv:
        from run_cli import run_cli
        run_cli()
        return

    # 默认 GUI 模式
    from gui import main as gui_main
    gui_main()


if __name__ == "__main__":
    main()
