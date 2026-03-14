"""Session manager — enforces one active game per chat."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Game


async def get_active_game(session: AsyncSession, chat_id: int) -> Game | None:
    """Return the active game for a chat, or None if no session is live."""
    result = await session.execute(
        select(Game).where(Game.chat_id == chat_id, Game.status == "active")
    )
    return result.scalar_one_or_none()


async def create_game(
    session: AsyncSession,
    chat_id: int,
    created_by: int,
) -> Game:
    """Create and persist a new active game.

    Caller MUST check get_active_game() first to enforce the one-session rule.
    """
    game = Game(chat_id=chat_id, created_by=created_by, status="active")
    session.add(game)
    await session.commit()
    await session.refresh(game)
    return game
