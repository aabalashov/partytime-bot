"""Unit tests for bot/utils/timezone.py."""
from datetime import datetime

import pytz

from bot.utils.timezone import local_to_utc, utc_to_local


class TestLocalToUtc:
    def test_utcplus5_to_utc(self):
        naive = datetime(2026, 3, 14, 21, 0, 0)  # 21:00 in UTC+5
        result = local_to_utc(naive, "Asia/Tashkent")
        assert result.hour == 16  # 21 - 5 = 16 UTC
        assert result.tzinfo == pytz.utc

    def test_utcplus3_to_utc(self):
        naive = datetime(2026, 3, 14, 21, 0, 0)  # 21:00 Moscow (UTC+3)
        result = local_to_utc(naive, "Europe/Moscow")
        assert result.hour == 18  # 21 - 3 = 18 UTC

    def test_utcminus5_to_utc(self):
        # Use January (EST = UTC-5) to avoid DST ambiguity
        naive = datetime(2026, 1, 14, 15, 0, 0)  # 15:00 New York in winter (EST = UTC-5)
        result = local_to_utc(naive, "America/New_York")
        assert result.hour == 20  # 15 + 5 = 20 UTC


class TestUtcToLocal:
    def test_utc_to_utcplus5(self):
        utc_dt = pytz.utc.localize(datetime(2026, 3, 14, 16, 0, 0))
        result = utc_to_local(utc_dt, "Asia/Tashkent")
        assert result.hour == 21  # 16 + 5 = 21

    def test_round_trip_identity(self):
        naive = datetime(2026, 3, 14, 20, 30, 0)
        tz_str = "Asia/Tashkent"
        utc = local_to_utc(naive, tz_str)
        local_back = utc_to_local(utc, tz_str)
        assert local_back.hour == naive.hour
        assert local_back.minute == naive.minute

    def test_naive_utc_input_handled(self):
        """utc_to_local should handle naive datetimes as UTC."""
        naive_utc = datetime(2026, 3, 14, 12, 0, 0)
        result = utc_to_local(naive_utc, "Europe/Berlin")
        # Berlin in March is UTC+1
        assert result.hour == 13
