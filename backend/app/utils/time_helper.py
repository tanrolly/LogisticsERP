"""
时间工具：统一提供北京时间（UTC+8）
替代已弃用的 datetime.utcnow()，并确保全系统使用一致的时区

注意：返回 naive datetime（不带时区标记），值已为北京时间 UTC+8，
兼容 SQLite 等不支持时区的数据库。
"""
from datetime import datetime, timezone, timedelta

BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now():
    """返回北京时间的 naive datetime（UTC+8，兼容 SQLite）"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)


def beijing_date():
    """返回北京时间对应的日期"""
    return datetime.now(BEIJING_TZ).date()
