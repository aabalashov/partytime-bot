"""Timezone conversion utilities."""
from datetime import datetime

import pytz


def local_to_utc(naive_dt: datetime, tz_str: str) -> datetime:
    """Convert a naive local datetime to UTC.

    Args:
        naive_dt: A naive datetime representing the user's local time.
        tz_str: Timezone string, e.g. "Asia/Tashkent" or "Europe/Moscow".

    Returns:
        A UTC-aware datetime.
    """
    tz = pytz.timezone(tz_str)
    local_dt = tz.localize(naive_dt)
    return local_dt.astimezone(pytz.utc)


def utc_to_local(utc_dt: datetime, tz_str: str) -> datetime:
    """Convert a UTC-aware datetime to the user's local timezone.

    Args:
        utc_dt: A timezone-aware UTC datetime.
        tz_str: Target timezone string.

    Returns:
        A timezone-aware datetime in the target timezone.
    """
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)
    tz = pytz.timezone(tz_str)
    return utc_dt.astimezone(tz)


def format_local_time(utc_iso: str, tz_str: str) -> str:
    """Format a UTC ISO string as a human-readable local time HH:MM."""
    utc_dt = datetime.fromisoformat(utc_iso).replace(tzinfo=pytz.utc)
    local = utc_to_local(utc_dt, tz_str)
    return local.strftime("%H:%M")


# Common timezone choices shown to users
COMMON_TIMEZONES: list[tuple[str, str]] = [
    ("Europe/London", "UTC+0 — London"),
    ("Europe/Berlin", "UTC+1 — Berlin"),
    ("Europe/Athens", "UTC+2 — Athens"),
    ("Europe/Moscow", "UTC+3 — Moscow"),
    ("Asia/Dubai", "UTC+4 — Dubai"),
    ("Asia/Tashkent", "UTC+5 — Tashkent"),
    ("Asia/Almaty", "UTC+6 — Almaty"),
    ("Asia/Bangkok", "UTC+7 — Bangkok"),
    ("Asia/Shanghai", "UTC+8 — Shanghai"),
    ("Asia/Tokyo", "UTC+9 — Tokyo"),
    ("Australia/Sydney", "UTC+10 — Sydney"),
    ("Pacific/Auckland", "UTC+12 — Auckland"),
    ("America/Los_Angeles", "UTC-8 — Los Angeles"),
    ("America/Chicago", "UTC-6 — Chicago"),
    ("America/New_York", "UTC-5 — New York"),
]
