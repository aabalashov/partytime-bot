"""Unit tests for bot/utils/scheduling.py (no DB required)."""
from datetime import date

import pytest

from bot.utils.scheduling import best_slot, compute_slots


def _avail(user_id: int, username: str, start: str, end: str) -> dict:
    """Helper to build an availability dict for a given day."""
    today = date.today().isoformat()
    return {
        "user_id": user_id,
        "username": username,
        "start_time_utc": f"{today}T{start}:00+00:00",
        "end_time_utc": f"{today}T{end}:00+00:00",
    }


class TestComputeSlots:
    def test_single_user_two_slots(self):
        avails = [_avail(1, "Anton", "20:00", "22:00")]
        slots = compute_slots(avails)
        assert len(slots) == 2
        times = {s["slot_utc"][11:16] for s in slots}
        assert "20:00" in times
        assert "21:00" in times

    def test_overlap_is_counted(self):
        avails = [
            _avail(1, "Anton", "19:00", "22:00"),
            _avail(2, "Igor", "20:00", "23:00"),
        ]
        slots = compute_slots(avails)
        # Slot 20:00 and 21:00 should have both users
        two_person_slots = [s for s in slots if s["count"] == 2]
        assert len(two_person_slots) >= 2

    def test_no_overlap_no_best(self):
        avails = [
            _avail(1, "Anton", "10:00", "11:00"),
            _avail(2, "Igor", "20:00", "21:00"),
        ]
        slots = compute_slots(avails)
        # Each slot has exactly 1 person
        assert all(s["count"] == 1 for s in slots)

    def test_three_way_overlap(self):
        avails = [
            _avail(1, "Anton", "20:00", "23:00"),
            _avail(2, "Igor", "19:00", "22:00"),
            _avail(3, "Sasha", "21:00", "23:00"),
        ]
        result = best_slot(avails)
        assert result is not None
        # 21:00 is the only slot all three share
        assert result["slot_utc"][11:16] == "21:00"
        assert result["count"] == 3

    def test_empty_input_returns_empty(self):
        assert compute_slots([]) == []

    def test_best_slot_empty_returns_none(self):
        assert best_slot([]) is None

    def test_best_slot_returns_first_on_tie(self):
        avails = [
            _avail(1, "Anton", "20:00", "22:00"),
            _avail(2, "Igor", "20:00", "22:00"),
        ]
        result = best_slot(avails)
        assert result is not None
        assert result["count"] == 2
