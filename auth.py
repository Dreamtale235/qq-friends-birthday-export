"""QQ 邮箱登录与可选的会话持久化。"""
import logging
import os
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from config import QQ_MAIL_URL, SESSION_FILE, LOGIN_TIMEOUT, PAGE_GOTO_TIMEOUT

logger = logging.getLogger(__name__)


def clear_saved_session() -> bool:
    """删除本工具保存的唯一会话文件；返回删除前是否存在。"""
    existed = SESSION_FILE.exists()
    SESSION_FILE.unlink(missing_ok=True)
    return existed

# 已登录的页面特征（满足任一即认为已登录）
LOGGED_IN_INDICATORS = [
    "text=收件箱",
    "text=写信",
    "text=收信",
    '[class*="mailbox"]',
    '[class*="inbox"]',
    '[id*="mailbox"]',
    "text=日程",
    '[class*="user-name"]',
    '[class*="avatar"]',
]

# 未登录的页面特征（满足任一即认为在登录页）
LOGIN_PAGE_INDICATORS = [
    "text=扫码登录",
    "text=密码登录",
    '[class*="qrcode"]',
    '[id*="qrcode"]',
    'input[type="password"]',
    "text=QQ登录",
    '[class*="login"]',
    "text=快捷登录",
]


class AuthManager:
    """管理 QQ 邮箱的浏览器登录会话"""

    def __init__(self, headless: bool = False, persist_session: bool = False):
        self.headless = headless
        self.persist_session = persist_session
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def session_exists(self) -> bool:
        return SESSION_FILE.exists()

    def check_session_valid(self) -> bool:
        """检查已保存的会话是否仍然有效

        通过检测页面 DOM 元素判断登录态，而非 URL 关键字。
        """
        if not self.persist_session or not self.session_exists():
            return False
        pw = None
        browser = None
        context = None
        try:
            pw = sync_playwright().start()
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(SESSION_FILE))
            page = context.new_page()
            page.goto(QQ_MAIL_URL, timeout=PAGE_GOTO_TIMEOUT, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            valid = self._is_logged_in(page)
            return valid
        except Exception:
            logger.exception("检查会话有效性失败")
            return False
        finally:
            if context:
                try:
                    context.close()
                except Exception:
                    pass
            if browser:
                try:
                    browser.close()
                except Exception:
                    pass
            if pw:
                try:
                    pw.stop()
                except Exception:
                    pass

    def _is_logged_in(self, page: Page) -> bool:
        """检测页面是否处于已登录状态"""
        # 检查已登录特征
        for indicator in LOGGED_IN_INDICATORS:
            try:
                if page.query_selector(indicator):
                    logger.debug(f"  登录态检测：找到已登录特征 '{indicator}'")
                    return True
            except Exception:
                continue

        # 检查未登录特征（确认是否在登录页）
        for indicator in LOGIN_PAGE_INDICATORS:
            try:
                if page.query_selector(indicator):
                    logger.debug(f"  登录态检测：找到未登录特征 '{indicator}'")
                    return False
            except Exception:
                continue

        # 兜底：取页面文本判断
        try:
            body_text = (page.text_content("body") or "")[:2000]
            if "收件箱" in body_text or "写信" in body_text:
                return True
            if "扫码登录" in body_text or "密码登录" in body_text:
                return False
        except Exception:
            pass

        logger.debug("  登录态检测：无法确定，假定未登录")
        return False

    def _is_on_login_page(self, page: Page) -> bool:
        """检测页面是否为登录页"""
        for indicator in LOGIN_PAGE_INDICATORS:
            try:
                if page.query_selector(indicator):
                    return True
            except Exception:
                continue
        return False

    def start_browser(self, use_saved_session: bool | None = None) -> Page:
        """启动浏览器并返回页面对象"""
        if use_saved_session is None:
            use_saved_session = self.persist_session
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
        )
        if self.persist_session and use_saved_session and self.session_exists():
            logger.info("加载已保存的会话...")
            self._context = self._browser.new_context(
                storage_state=str(SESSION_FILE)
            )
        else:
            self._context = self._browser.new_context()

        self._page = self._context.new_page()
        return self._page

    def login(self, page: Page, status_callback=None) -> bool:
        """打开 QQ 邮箱登录页，等待用户扫码登录

        Returns:
            True 表示登录成功，False 表示超时或失败
        """
        def update_status(msg: str):
            logger.info(msg)
            if status_callback:
                status_callback(msg)

        update_status("正在打开 QQ 邮箱登录页...")

        try:
            page.goto(QQ_MAIL_URL, timeout=PAGE_GOTO_TIMEOUT, wait_until="domcontentloaded")
        except Exception as e:
            update_status(f"无法访问 QQ 邮箱（{e}）")
            return False

        update_status("页面已打开，等待加载...")
        page.wait_for_timeout(3000)

        # 如果已经登录（极少情况），直接返回
        if self._is_logged_in(page):
            update_status("检测到已登录，无需扫码")
            self._save_session(update_status)
            return True

        # 确认在登录页
        if not self._is_on_login_page(page):
            update_status("警告：未检测到登录页面，请手动确认是否需要登录")
            page.wait_for_timeout(2000)

        update_status("请使用 QQ 手机版扫描屏幕上的二维码...")

        # 轮询等待登录成功（检测已登录特征出现）
        elapsed = 0
        poll_interval = 2000  # 每 2 秒检测一次
        while elapsed < LOGIN_TIMEOUT:
            page.wait_for_timeout(poll_interval)
            elapsed += poll_interval

            if self._is_logged_in(page):
                update_status("登录成功！")
                self._save_session(update_status)
                return True

        update_status(f"登录超时（{LOGIN_TIMEOUT // 1000} 秒内未检测到登录成功）")
        return False

    def _save_session(self, update_status=None) -> None:
        """仅在用户明确选择时保存登录状态。"""
        if not self.persist_session:
            if update_status:
                update_status("本次运行不会保存登录状态")
            return

        self._context.storage_state(path=str(SESSION_FILE))
        try:
            os.chmod(SESSION_FILE, 0o600)
        except OSError:
            logger.warning("无法收紧会话文件权限，请确保本机账户安全")
        logger.info("会话已保存至 %s", SESSION_FILE)
        if update_status:
            update_status("会话已保存；可随时在工具中清除")

    @staticmethod
    def clear_saved_session() -> bool:
        return clear_saved_session()

    def close(self):
        """关闭浏览器和 Playwright"""
        if self._context:
            try:
                self._context.close()
            except Exception:
                logger.debug("关闭浏览器上下文失败", exc_info=True)
            self._context = None
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                logger.debug("关闭浏览器失败", exc_info=True)
            self._browser = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                logger.debug("停止 Playwright 失败", exc_info=True)
            self._playwright = None
        logger.info("浏览器已关闭")

    @property
    def page(self) -> Page | None:
        return self._page

    @property
    def context(self) -> BrowserContext | None:
        return self._context
