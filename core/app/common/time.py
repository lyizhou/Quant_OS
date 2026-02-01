"""Time and timezone utilities."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


def get_timezone(tz_name: str = "Asia/Taipei") -> ZoneInfo:
    """Get timezone object.

    Args:
        tz_name: Timezone name (e.g., 'Asia/Taipei', 'America/New_York')

    Returns:
        ZoneInfo object
    """
    return ZoneInfo(tz_name)


def now(tz: str | ZoneInfo = "Asia/Taipei") -> datetime:
    """Get current datetime in specified timezone.

    Args:
        tz: Timezone name or ZoneInfo object

    Returns:
        Current datetime with timezone
    """
    if isinstance(tz, str):
        tz = get_timezone(tz)
    return datetime.now(tz)


def today(tz: str | ZoneInfo = "Asia/Taipei") -> datetime:
    """Get today's date at midnight in specified timezone.

    Args:
        tz: Timezone name or ZoneInfo object

    Returns:
        Today's date at 00:00:00
    """
    return now(tz).replace(hour=0, minute=0, second=0, microsecond=0)


def parse_time(time_str: str) -> time:
    """Parse time string in HH:MM format.

    Args:
        time_str: Time string (e.g., '08:30', '14:00')

    Returns:
        time object

    Raises:
        ValueError: If time string is invalid
    """
    try:
        hour, minute = map(int, time_str.split(":"))
        return time(hour=hour, minute=minute)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM") from e


def is_market_day(date: datetime, market: str = "US") -> bool:
    """Check if given date is a market trading day.

    Args:
        date: Date to check
        market: Market identifier ('US' or 'CN')

    Returns:
        True if it's a trading day

    Note:
        This is a simplified version. For production, use a proper
        market calendar library (e.g., pandas_market_calendars)
    """
    # Simplified: exclude weekends
    # TODO: Add holiday calendar support
    if market == "US":
        # US markets: Monday-Friday
        return date.weekday() < 5
    elif market == "CN":
        # CN markets: Monday-Friday
        return date.weekday() < 5
    else:
        raise ValueError(f"Unknown market: {market}")


def get_last_market_day(reference_date: datetime | None = None, market: str = "US") -> datetime:
    """Get the last market trading day on or before reference date.

    Args:
        reference_date: Reference date (default: today)
        market: Market identifier ('US' or 'CN')

    Returns:
        Last trading day with available data

    Note:
        For CN market, if today is a trading day but before 15:00 (market close),
        returns previous trading day to ensure data availability.
    """
    if reference_date is None:
        reference_date = today()

    current = reference_date

    # 对于中国市场，如果是今天且还没到收盘时间，使用昨天的数据
    if market == "CN":
        cn_now = now("Asia/Shanghai")
        # 如果是今天且在15:00之前（收盘时间），使用上一个交易日
        if current.date() == cn_now.date() and cn_now.hour < 15:
            current = current - timedelta(days=1)

    # Check if reference_date itself is a market day
    while not is_market_day(current, market):
        current -= timedelta(days=1)
    return current


def get_next_market_day(reference_date: datetime | None = None, market: str = "US") -> datetime:
    """Get the next market trading day after reference date.

    Args:
        reference_date: Reference date (default: today)
        market: Market identifier ('US' or 'CN')

    Returns:
        Next trading day
    """
    if reference_date is None:
        reference_date = today()

    current = reference_date + timedelta(days=1)
    while not is_market_day(current, market):
        current += timedelta(days=1)
    return current


def us_market_close_time(date: datetime) -> datetime:
    """Get US market close time for given date (4:00 PM ET).

    Args:
        date: Date to get close time for

    Returns:
        Datetime of market close in US/Eastern timezone
    """
    et_tz = get_timezone("America/New_York")
    return date.replace(hour=16, minute=0, second=0, microsecond=0, tzinfo=et_tz)


def cn_market_open_time(date: datetime) -> datetime:
    """Get CN market open time for given date (9:30 AM CST).

    Args:
        date: Date to get open time for

    Returns:
        Datetime of market open in Asia/Shanghai timezone
    """
    cn_tz = get_timezone("Asia/Shanghai")
    return date.replace(hour=9, minute=30, second=0, microsecond=0, tzinfo=cn_tz)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string.

    Args:
        dt: Datetime to format
        fmt: Format string

    Returns:
        Formatted datetime string
    """
    return dt.strftime(fmt)


def format_date(dt: datetime) -> str:
    """Format datetime to date string (YYYY-MM-DD).

    Args:
        dt: Datetime to format

    Returns:
        Formatted date string
    """
    return format_datetime(dt, "%Y-%m-%d")
