"""QQ 邮箱登录 & 会话持久化"""
import logging
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from config import QQ_MAIL_URL, SESSION_FILE, LOGIN_TIMEOUT, PAGE_GOTO_TIMEOUT

logger = logging.getLogger(__name__)

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

    def __init__(self, headless: bool = False):
        self.headless = headless
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
        if not self.session_exists():
            return False
        try:
            pw = sync_playwright().start()
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(SESSION_FILE))
            page = context.new_page()
            page.goto(QQ_MAIL_URL, timeout=PAGE_GOTO_TIMEOUT, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            valid = self._is_logged_in(page)

            context.close()
            browser.close()
            pw.stop()
            return valid
        except Exception:
            return False

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

    def start_browser(self, use_saved_session: bool = True) -> Page:
        """启动浏览器并返回页面对象"""
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
        )
        if use_saved_session and self.session_exists():
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
            self._context.storage_state(path=str(SESSION_FILE))
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
                update_status("登录成功！正在保存会话...")
                self._context.storage_state(path=str(SESSION_FILE))
                logger.info(f"会话已保存至 {SESSION_FILE}")
                update_status("会话已保存，下次启动无需重复登录")
                return True

        update_status(f"登录超时（{LOGIN_TIMEOUT // 1000} 秒内未检测到登录成功）")
        return False

    def close(self):
        """关闭浏览器和 Playwright"""
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        logger.info("浏览器已关闭")

    @property
    def page(self) -> Page | None:
        return self._page

    @property
    def context(self) -> BrowserContext | None:
        return self._context
