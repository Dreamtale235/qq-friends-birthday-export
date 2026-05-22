"""QQ 邮箱生日爬虫 — 基于真实 DOM 结构（.grid-schedule-bar-subject）"""
import logging
import random
import re
import time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import Page

from config import DEBUG, MONTH_SWITCH_DELAY_MIN, MONTH_SWITCH_DELAY_MAX, DATA_DIR
from utils import clean_name, calc_zodiac, calc_days_until_birthday

logger = logging.getLogger(__name__)

# 星期几 → 列号
WEEKDAY_TO_COL = {"周日": 0, "周一": 1, "周二": 2, "周三": 3, "周四": 4, "周五": 5, "周六": 6}


class QQMailCrawler:
    """QQ 邮箱生日爬虫"""

    def __init__(self, page: Page, callbacks: dict | None = None):
        self.page = page
        self.callbacks = callbacks or {}
        self.friends: dict[str, dict] = {}

    def _status(self, msg: str):
        logger.info(msg)
        if cb := self.callbacks.get("on_status"):
            cb(msg)

    def _progress(self, current: int, total: int):
        if cb := self.callbacks.get("on_progress"):
            cb(current, total)

    def _random_delay(self):
        time.sleep(random.uniform(MONTH_SWITCH_DELAY_MIN, MONTH_SWITCH_DELAY_MAX))

    # ── 调试 ──

    def _debug_screenshot(self, name: str = "debug"):
        if not DEBUG:
            return
        path = DATA_DIR / f"{name}.png"
        self.page.screenshot(path=str(path), full_page=False)
        logger.info(f"截图已保存: {path}")

    def _debug_html(self, name: str = "debug"):
        if not DEBUG:
            return
        path = DATA_DIR / f"{name}.html"
        html = self.page.content()
        path.write_text(html, encoding="utf-8")
        logger.info(f"HTML 已保存: {path}")

    # ── 导航到日历 ──

    def navigate_to_birthday_calendar(self) -> bool:
        """导航到 QQ 邮箱日历页面（兼容旧方法名）"""
        return self.navigate_to_calendar()

    def navigate_to_calendar(self) -> bool:
        """导航到 QQ 邮箱日历页面"""
        self._status("正在进入 QQ 邮箱日历...")
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(2000)

        self._debug_screenshot("01_mailbox_home")
        self._debug_html("01_mailbox_home")

        # 路径 A：点击「日历」导航项
        cal_selectors = [
            "text=日历",
            '[title*="日历"]',
            'a:has-text("日历")',
            'span:has-text("日历")',
            '[class*="calendar"]',
        ]
        clicked = False
        for sel in cal_selectors:
            try:
                self.page.click(sel, timeout=5000)
                clicked = True
                self._status("已点击日历入口")
                break
            except Exception:
                continue

        if not clicked:
            self._status("未找到日历入口，尝试直接访问 URL...")
            try:
                self.page.goto("https://wx.mail.qq.com/home/index#/calendar", timeout=15000)
            except Exception:
                pass

        self.page.wait_for_timeout(2000)
        self._debug_screenshot("02_calendar_loaded")
        self._debug_html("02_calendar_page")
        return True

    # ── 遍历 12 个月 ──

    def crawl_all_months(self) -> list[dict]:
        self._status("开始遍历 1–12 月生日日历...")

        for month in range(1, 13):
            # 检查取消标志
            if self._is_cancelled():
                self._status("用户取消操作")
                break

            # 检查页面是否仍然打开
            if self._page_closed():
                self._status("浏览器页面已关闭，停止爬取")
                break

            self._status(f"正在处理 {month} 月...")
            self._progress(month - 1, 12)

            try:
                self._navigate_to_month(month)
                self.page.wait_for_timeout(2500)

                # 保存当前月份的 HTML 用于调试
                self._debug_html(f"month_{month:02d}")

                entries = self._parse_current_month(month)
                for entry in entries:
                    key = f"{entry['name']}|{entry['birthday']}"
                    if key not in self.friends:
                        self.friends[key] = entry

                logger.info(f"  {month} 月：提取 {len(entries)} 条，累计 {len(self.friends)} 条")
            except Exception as e:
                msg = str(e)
                if "closed" in msg.lower() or "target" in msg.lower():
                    self._status("浏览器已关闭，停止爬取")
                    break
                logger.warning(f"  {month} 月处理异常: {e}")
                continue

            self._random_delay()

        self._progress(12, 12)
        self._status(f"爬取完成，共获取 {len(self.friends)} 位好友生日")
        return list(self.friends.values())

    def _is_cancelled(self) -> bool:
        if cb := self.callbacks.get("on_cancel_check"):
            try:
                return cb()
            except Exception:
                pass
        return False

    def _page_closed(self) -> bool:
        try:
            return self.page.is_closed()
        except Exception:
            return True

    # ── 月份导航 ──

    def _navigate_to_month(self, target_month: int):
        """切换到指定月份"""
        current = self._get_current_month_year()
        if current and current[0] == target_month:
            return

        # 策略 1：使用月份选择器直接点击
        if self._try_month_picker(target_month):
            return

        # 策略 2：使用 prev/next 按钮
        if current:
            cm, cy = current
            clicks = (target_month - cm) + (12 if target_month < cm else 0)
            if clicks > 6:
                clicks = clicks - 12  # 反方向更短
            direction = "next" if clicks > 0 else "prev"
            logger.debug(f"  从 {cm} 月 → {target_month} 月，需点击 {direction} x{abs(clicks)}")
            for _ in range(abs(clicks)):
                if not self._click_nav_button(direction):
                    logger.warning(f"  月份切换失败")
                    break
                self.page.wait_for_timeout(1000)
        else:
            # 无法检测当前月份，从 1 月开始暴力尝试
            self._navigate_unknown_to_month(target_month)

    def _try_month_picker(self, target_month: int) -> bool:
        """尝试使用月份选择器（点击年/月文字弹出选择面板）"""
        # 点击年月标签打开月份选择器
        header_selectors = [
            ".calendar-body-head-time",
            '[class*="calendar-body-head-time"]',
            '[class*="head-time"]',
        ]
        for sel in header_selectors:
            try:
                el = self.page.query_selector(sel)
                if el:
                    el.click(timeout=3000)
                    self.page.wait_for_timeout(800)
                    break
            except Exception:
                continue

        # 在月份选择面板中点击目标月份
        month_texts = [
            f"text={target_month}月",
            f"text={target_month}",
        ]
        for mt in month_texts:
            try:
                self.page.click(mt, timeout=3000)
                return True
            except Exception:
                continue

        # 尝试点击 .month-picker-item
        try:
            items = self.page.query_selector_all('[class*="month-picker-item"]')
            for item in items:
                text = (item.inner_text() or "").strip()
                if str(target_month) in text:
                    item.click(timeout=2000)
                    return True
        except Exception:
            pass

        return False

    def _click_nav_button(self, direction: str) -> bool:
        """点击月份左右箭头"""
        switch_sel = '[class*="calendar-body-head-switch"]'
        try:
            switch = self.page.query_selector(switch_sel)
            if switch:
                buttons = switch.query_selector_all("div, button, span, svg")
                idx = 0 if direction == "prev" else 1
                if idx < len(buttons):
                    try:
                        buttons[idx].click(timeout=2000)
                        return True
                    except Exception:
                        pass
        except Exception:
            pass

        # 回退：通用选择器
        nav_selectors = [
            f'[class*="switch"] div:first-child' if direction == "prev" else f'[class*="switch"] div:last-child',
            f'[aria-label*="{"上" if direction == "prev" else "下"}"]',
            f'[aria-label*="{"prev" if direction == "prev" else "next"}"]',
        ]
        for sel in nav_selectors:
            try:
                el = self.page.query_selector(sel)
                if el and el.is_visible():
                    el.click(timeout=2000)
                    return True
            except Exception:
                continue

        # 终极回退：键盘
        try:
            key = "ArrowLeft" if direction == "prev" else "ArrowRight"
            self.page.keyboard.press(key)
            return True
        except Exception:
            pass

        return False

    def _navigate_unknown_to_month(self, target_month: int):
        """当无法检测当前月份时的回退导航"""
        # 先回到 1 月（连续点击 prev 直到不能再点）
        for _ in range(12):
            self._click_nav_button("prev")
            self.page.wait_for_timeout(500)

        # 再前进到目标月份
        for _ in range(target_month - 1):
            self._click_nav_button("next")
            self.page.wait_for_timeout(500)

    def _get_current_month_year(self) -> tuple[int, int] | None:
        """从日历头部获取当前年月，返回 (month, year)"""
        try:
            el = self.page.query_selector('[class*="calendar-body-head-time"]')
            if el:
                text = (el.text_content() or "").strip()
                # "2026年5月" 或 "2026年05月"
                m = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月", text)
                if m:
                    return int(m.group(2)), int(m.group(1))
            # 备选：从 grid-cell 的第一个 currentMonthDate 推断
            dates = self.page.query_selector_all(".currentMonthDate")
            if dates:
                first_date = (dates[0].text_content() or "").strip()
                if first_date.isdigit():
                    day = int(first_date)
                    # 假设是当前年，取第一个 currentMonth 日期反推月份
                    # 第一个日期是 1 的话就是该月的 1 号
                    return None  # 需要更多信息
        except Exception:
            pass
        return None

    # ── 解析当前月份的生日数据 ──

    def _parse_current_month(self, month: int) -> list[dict]:
        """解析当前月份日历中的所有生日条目

        关键认知：
        - .grid-schedule-bar-subject 文本如 "29王梓涵生日" 中，"29王梓涵" 是备注/全名，
          "生日" 是事件类型标记；日期必须从 schedule bar 在 grid 中的位置推算。
        - grid 有 6 行 × 7 列，可能包含前月/后月的填充日，只有落在当月 1~31 的才计入。
        """
        entries = []
        my = self._get_current_month_year()
        year = my[1] if my else datetime.now().year

        subjects = self.page.query_selector_all(".grid-schedule-bar-subject")
        if not subjects:
            subjects = self.page.query_selector_all('[class*="schedule-bar-subject"]')

        for subj in subjects:
            try:
                text = (subj.text_content() or "").strip()
                if "生日" not in text:
                    continue

                # 从文本提取名字（去掉"生日"后缀，剩余即全名/备注）
                name = re.sub(r"生日$", "", text).strip()
                name = clean_name(name)
                if not name:
                    continue

                # 从 schedule bar 的 grid 位置推算实际日期
                day = self._get_day_from_schedule_position(subj)
                if day is None:
                    continue

                # 只保留落在当月范围内的日期
                if day < 1 or day > 31:
                    continue

                birthday = f"{month:02d}-{day:02d}"
                entries.append({
                    "name": name,
                    "birthday": birthday,
                    "birth_year": "",
                    "zodiac": calc_zodiac(month, day),
                    "days_until_birthday": calc_days_until_birthday(month, day),
                    "remark": "",
                })
            except Exception as e:
                logger.info(f"  解析日程异常: {e}")
                continue

        return entries

    def _get_day_from_schedule_position(self, subject_el) -> int | None:
        """遍历所有 grid-cell，找到 bounding rect 包含 schedule bar 中心点的那个"""
        try:
            day = subject_el.evaluate("""el => {
                const bar = el.closest('.grid-schedule-bar');
                if (!bar) return null;

                const rect = bar.getBoundingClientRect();
                const midX = rect.left + rect.width / 2;
                const midY = rect.top + rect.height / 2;

                for (const cell of document.querySelectorAll('.grid-cell')) {
                    const c = cell.getBoundingClientRect();
                    if (midX >= c.left && midX <= c.right &&
                        midY >= c.top && midY <= c.bottom) {
                        // 只取当月格子（有 currentMonth class）
                        if (!cell.classList.contains('currentMonth')) return null;
                        const d = cell.querySelector('.time-date');
                        if (d) {
                            const t = d.textContent || '';
                            const m = t.match(/(\\d{1,2})\\s*$/);
                            if (m) return parseInt(m[1], 10);
                        }
                    }
                }
                return null;
            }""")
            if isinstance(day, int) and 1 <= day <= 31:
                return day
        except Exception:
            pass
        return None
