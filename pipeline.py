"""QQ 好友生日导出 — 统一工作流编排（GUI / CLI 共用）"""
import logging
from pathlib import Path
from typing import Callable

from auth import AuthManager
from crawler import QQMailCrawler
from exporter import export_csv
from config import QQ_MAIL_URL, PAGE_GOTO_TIMEOUT

logger = logging.getLogger(__name__)


def run_pipeline(
    on_status: Callable[[str], None],
    on_progress: Callable[[int, int], None],
    on_log: Callable[[str], None],
    on_done: Callable[[Path, int, list[dict]], None],
    on_error: Callable[[str], None],
    is_cancelled: Callable[[], bool],
) -> None:
    """执行 登录 → 导航 → 爬取 → 导出 → 关闭 全流程

    所有 UI 交互通过回调注入，与 GUI/CLI 解耦。
    """
    mgr = None
    try:
        on_status("正在检测登录状态...")
        on_log("检测已有会话...")

        mgr = AuthManager(headless=False)
        session_valid = mgr.check_session_valid()

        on_status("正在启动浏览器...")
        on_log("启动浏览器...")
        page = mgr.start_browser(use_saved_session=session_valid)

        if session_valid:
            on_log("会话有效，直接进入邮箱...")
            try:
                page.goto(QQ_MAIL_URL, timeout=PAGE_GOTO_TIMEOUT, wait_until="domcontentloaded")
            except Exception:
                on_log("警告：加载邮箱页面超时，但会话可能仍有效，继续尝试...")
            page.wait_for_timeout(2000)
        else:
            on_log("需要登录，请扫描二维码...")
            success = mgr.login(page, status_callback=on_log)
            if not success:
                mgr.close()
                on_error("登录超时或失败")
                return

        if is_cancelled():
            on_log("用户取消操作")
            mgr.close()
            on_error("用户取消")
            return

        on_status("正在爬取好友生日...")
        crawler = QQMailCrawler(page, callbacks={
            "on_status": on_log,
            "on_progress": on_progress,
            "on_cancel_check": is_cancelled,
        })

        crawler.navigate_to_calendar()

        if is_cancelled():
            on_log("用户取消操作")
            mgr.close()
            on_error("用户取消")
            return

        friends = crawler.crawl_all_months()

        if not friends:
            on_log("未获取到任何好友生日数据")
            on_log("可能原因：")
            on_log("  1. 未找到「生日日历」入口")
            on_log("  2. 日历 DOM 结构与预设选择器不匹配")
            on_log("  3. 好友未公开生日信息")
            on_log("请检查浏览器页面并反馈，以便调整选择器")
            on_error("未获取到数据，请查看日志")
            return

        on_status("正在导出 CSV...")
        on_log(f"共获取 {len(friends)} 位好友生日，正在生成 CSV...")
        output_path = export_csv(friends)
        on_log(f"CSV 已保存至 {output_path}")

        mgr.close()
        on_log("浏览器已关闭")

        on_done(output_path, len(friends), friends)

    except Exception as e:
        logger.exception("导出过程异常")
        msg = str(e)
        if "closed" in msg.lower() or "target" in msg.lower():
            on_error("浏览器已关闭，导出中断")
        else:
            on_error(f"程序异常：{e}")
        if mgr:
            try:
                mgr.close()
            except Exception:
                pass
