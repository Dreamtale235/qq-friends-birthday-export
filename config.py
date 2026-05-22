from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SESSION_DIR = BASE_DIR / "sessions"
DATA_DIR = BASE_DIR / "data"
SESSION_FILE = SESSION_DIR / "state.json"

# QQ 邮箱
QQ_MAIL_URL = "https://wx.mail.qq.com/"
LOGIN_TIMEOUT = 180_000        # 扫码等待超时 (ms) — 3 分钟
PAGE_GOTO_TIMEOUT = 60_000     # 首次页面加载超时 (ms)
PAGE_LOAD_TIMEOUT = 30_000     # 一般页面加载超时 (ms)

# 爬取
MONTH_SWITCH_DELAY_MIN = 0.3   # 切月最小间隔 (s)
MONTH_SWITCH_DELAY_MAX = 0.8   # 切月最大间隔 (s)

# 调试
DEBUG = False                  # True 时写入调试 HTML/截图到 data/

# 确保目录存在
SESSION_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
