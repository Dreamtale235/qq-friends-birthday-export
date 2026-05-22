"""工具函数：星座、日期计算"""
from datetime import date, datetime


def calc_zodiac(month: int, day: int) -> str:
    """根据月日计算星座"""
    zodiacs = [
        ("摩羯座", (1, 19)), ("水瓶座", (2, 18)), ("双鱼座", (3, 20)),
        ("白羊座", (4, 19)), ("金牛座", (5, 20)), ("双子座", (6, 21)),
        ("巨蟹座", (7, 22)), ("狮子座", (8, 22)), ("处女座", (9, 22)),
        ("天秤座", (10, 23)), ("天蝎座", (11, 22)), ("射手座", (12, 21)),
        ("摩羯座", (12, 31)),
    ]
    for name, (end_month, end_day) in zodiacs:
        if (month == end_month and day <= end_day) or month < end_month:
            return name
    return "摩羯座"


def calc_days_until_birthday(month: int, day: int) -> int:
    """计算距离下次生日的天数（0 = 今天，正数 = 未来天数）"""
    today = date.today()
    this_year_bday = date(today.year, month, day)
    if this_year_bday < today:
        this_year_bday = date(today.year + 1, month, day)
    return (this_year_bday - today).days


def clean_name(raw: str) -> str:
    """清洗好友昵称"""
    return raw.strip().replace("\n", " ").replace("\r", "")


def parse_birthday_date(date_str: str) -> tuple[int, int] | None:
    """解析日期字符串为 (month, day)，支持 MM-DD / M月D日 等格式"""
    import re
    # MM-DD 或 MM/DD
    m = re.match(r"(\d{1,2})[/-](\d{1,2})", date_str)
    if m:
        return int(m.group(1)), int(m.group(2))
    # M月D日
    m = re.match(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", date_str)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None
