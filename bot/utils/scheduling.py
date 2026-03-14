"""Overlap calculation for availability ranges (pure, DB-free logic)."""
from datetime import datetime, timedelta

import pytz


def _parse_utc(iso: str) -> datetime:
    """Parse an ISO UTC string into a UTC-aware datetime."""
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.utc)
    return dt


def compute_slots(
    availabilities: list[dict],
    slot_minutes: int = 60,
) -> list[dict]:
    """Compute time slots and count overlapping participants.

    Args:
        availabilities: List of dicts with keys:
            - user_id (int)
            - username (str)
            - start_time_utc (ISO string)
            - end_time_utc (ISO string)
        slot_minutes: Slot duration in minutes (default 60 per PRD §6).

    Returns:
        List of dicts sorted by participant count (desc), each with:
            - slot_utc (ISO string of slot start)
            - count (int)
            - users (list of usernames/ids)
    """
    if not availabilities:
        return []

    delta = timedelta(minutes=slot_minutes)

    # Build a map: slot_start_utc -> list of user identifiers present
    slot_map: dict[datetime, list[str]] = {}

    for avail in availabilities:
        start = _parse_utc(avail["start_time_utc"])
        end = _parse_utc(avail["end_time_utc"])
        label = avail.get("username") or str(avail["user_id"])

        # Normalise to slot boundaries
        slot = start.replace(minute=(start.minute // slot_minutes) * slot_minutes,
                              second=0, microsecond=0)
        while slot < end:
            slot_map.setdefault(slot, []).append(label)
            slot += delta

    results = [
        {
            "slot_utc": slot.isoformat(),
            "count": len(users),
            "users": users,
        }
        for slot, users in slot_map.items()
    ]

    # Sort by count desc, then by time asc for tie-breaking
    results.sort(key=lambda r: (-r["count"], r["slot_utc"]))
    return results


def best_slot(availabilities: list[dict], slot_minutes: int = 60) -> dict | None:
    """Return the single best slot or None if no availability data."""
    slots = compute_slots(availabilities, slot_minutes)
    return slots[0] if slots else None
