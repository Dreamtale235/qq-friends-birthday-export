"""日志记录模块 — 同时输出到控制台和文件，支持按日期轮转"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

from config import BASE_DIR

LOG_DIR = BASE_DIR / "logs"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5MB 单文件上限
BACKUP_COUNT = 7                 # 保留最近 7 个轮转文件

_fmt = logging.Formatter(
    "%(asctime)s [%(levelname)-5s] %(name)s:%(lineno)d — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_initialized = False


def setup(log_level: int = logging.INFO):
    """初始化日志系统，全局调用一次即可"""
    global _initialized
    if _initialized:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(log_level)

    # 清除已有的 handler（避免重复）
    root.handlers.clear()

    # ── 控制台 handler ──
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console.setFormatter(_fmt)
    root.addHandler(console)

    # ── 文件 handler（按日期命名，自动轮转）──
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"app_{today}.log"
    file_handler = RotatingFileHandler(
        str(log_file), maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)  # 文件记录 DEBUG 及以上所有级别
    file_handler.setFormatter(_fmt)
    root.addHandler(file_handler)

    # ── 错误专用文件（只记录 WARNING 及以上）──
    error_log = LOG_DIR / f"error_{today}.log"
    error_handler = RotatingFileHandler(
        str(error_log), maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(_fmt)
    root.addHandler(error_handler)

    # ── 捕获未处理异常 ──
    def _excepthook(exc_type, exc_value, exc_tb):
        logging.getLogger("unhandled").critical(
            "未捕获的异常", exc_info=(exc_type, exc_value, exc_tb)
        )

    sys.excepthook = _excepthook

    _initialized = True
    logging.getLogger(__name__).info(f"日志系统已初始化，日志目录：{LOG_DIR}")


def get_logger(name: str = "") -> logging.Logger:
    """获取 logger（便捷函数）"""
    return logging.getLogger(name)
