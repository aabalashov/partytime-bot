"""Confirm / Change / Cancel callbacks (PRD §9.2 - Confirmation)."""
import logging
from datetime import datetime, timezone

import pytz
from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.party import PENDING_GAME_KEY
from bot.keyboards.builders import date_selection_kb
from db.models import Game, Vote, User
from db.session import AsyncSessionFactory
from services.reminder import schedule_reminder

logger = logging.getLogger(__name__)


async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle confirm:game / confirm:change / confirm:cancel."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":", 1)[1]
    game_id = context.chat_data.get(PENDING_GAME_KEY)
    chat = update.effective_chat

    if game_id is None:
        await query.answer("No active game.", show_alert=True)
        return

    if action == "cancel":
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(Game).where(Game.id == game_id))
            game = result.scalar_one_or_none()
            if game:
                game.status = "cancelled"
                await session.commit()
        context.chat_data.pop(PENDING_GAME_KEY, None)
        await query.edit_message_text("❌ Game cancelled. Use /party to start a new session.")
        return

    if action == "change":
        await query.edit_message_text(
            "📅 *When do you want to play?*",
            parse_mode="Markdown",
            reply_markup=date_selection_kb(),
        )
        return

    if action == "game":
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(Game).where(Game.id == game_id))
            game = result.scalar_one_or_none()
            if game is None:
                await query.answer("Game not found.", show_alert=True)
                return

            game.status = "confirmed"
            await session.commit()

            # Gather going/maybe players
            votes_result = await session.execute(
                select(Vote).where(
                    Vote.game_id == game_id, Vote.status.in_(["going", "maybe"])
                )
            )
            votes = votes_result.scalars().all()
            
            user_ids = [v.user_id for v in votes]
            users_result = await session.execute(
                select(User).where(User.telegram_id.in_(user_ids))
            )
            users = users_result.scalars().all()
            
            # Map users: telegram_id -> (name, timezone)
            user_info = {}
            for u in users:
                name = u.first_name or u.username or str(u.telegram_id)
                user_info[u.telegram_id] = (name, u.timezone or "UTC")
                
            slot_utc_str = game.confirmed_time_utc or ""

        # Group players by timezone
        tz_groups = {}
        for v in votes:
            name, tz = user_info.get(v.user_id, (str(v.user_id), "UTC"))
            if tz not in tz_groups:
                tz_groups[tz] = []
            tz_groups[tz].append(name)

        # Build timezone breakdown text
        from bot.utils.timezone import format_local_time
        
        tz_lines = []
        if slot_utc_str:
            for tz_str, players in tz_groups.items():
                local_time = format_local_time(slot_utc_str, tz_str)
                players_str = ", ".join(players)
                tz_lines.append(f"• *{local_time}* ({tz_str}): {players_str}")
        
        time_breakdown_text = "\n".join(tz_lines) if tz_lines else "TBD"

        await query.edit_message_text(
            f"🎮 *Game confirmed!*\n\n"
            f"⏰ *Local Times:*\n{time_breakdown_text}",
            parse_mode="Markdown",
        )
        context.chat_data.pop(PENDING_GAME_KEY, None)

        # Schedule reminder 30 min before game
        if slot_utc_str:
            try:
                game_dt = datetime.fromisoformat(slot_utc_str).replace(tzinfo=pytz.utc)
                schedule_reminder(
                    application=context.application,
                    game_id=game_id,
                    game_time_utc=game_dt,
                    chat_id=chat.id,
                    players=player_ids,
                    slot_label=slot_label,
                )
            except Exception as exc:
                logger.warning("Could not schedule reminder: %s", exc)
