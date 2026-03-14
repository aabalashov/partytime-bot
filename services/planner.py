"""Planner service — loads DB rows and delegates to scheduling utils."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.scheduling import best_slot
from db.models import Availability, User


async def find_best_slot_for_game(
    session: AsyncSession, game_id: int
) -> dict | None:
    """Load all availabilities for a game and return the best overlapping slot.

    Returns a dict with keys: slot_utc, count, users — or None if no data.
    """
    result = await session.execute(
        select(Availability).where(Availability.game_id == game_id)
    )
    availabilities = result.scalars().all()

    if not availabilities:
        return None

    # Enrich with usernames where available
    rows: list[dict] = []
    for avail in availabilities:
        user_result = await session.execute(
            select(User).where(User.telegram_id == avail.user_id)
        )
        user = user_result.scalar_one_or_none()
        rows.append(
            {
                "user_id": avail.user_id,
                "username": user.username if user else str(avail.user_id),
                "start_time_utc": avail.start_time_utc,
                "end_time_utc": avail.end_time_utc,
            }
        )

    return best_slot(rows)
