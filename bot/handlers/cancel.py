"""Handler for /cancel command — cancels the active planning session."""
from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.party import PENDING_GAME_KEY
from bot.keyboards.builders import confirm_kb
from db.models import Game, Vote, User
from db.session import AsyncSessionFactory


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/cancel — cancel the active planning session in this chat."""
    chat = update.effective_chat
    user = update.effective_user

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Game)
            .where(Game.chat_id == chat.id, Game.status == "active")
            .order_by(Game.created_at.desc())
        )
        game = result.scalars().first()

        if game is None:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "ℹ️ No active planning session in this chat."
                )
            return

        game.status = "cancelled"
        await session.commit()

    context.chat_data.pop(PENDING_GAME_KEY, None)

    if update.effective_message:
        await update.effective_message.reply_text(
            f"❌ Planning session cancelled by {user.first_name}.\n"
            "Use /party to start a new one."
        )


async def confirm_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/confirm — show confirmation screen for the active session."""
    chat = update.effective_chat

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Game)
            .where(Game.chat_id == chat.id, Game.status == "active")
            .order_by(Game.created_at.desc())
        )
        game: Game | None = result.scalars().first()

        if game is None:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "ℹ️ No active planning session in this chat."
                )
            return

        # Fetch all votes and corresponding users for names
        votes_result = await session.execute(
            select(Vote).where(Vote.game_id == game.id)
        )
        votes = votes_result.scalars().all()
        
        user_ids = [v.user_id for v in votes]
        users_result = await session.execute(
            select(User).where(User.telegram_id.in_(user_ids))
        )
        users = users_result.scalars().all()
        
        user_info = {}
        for u in users:
            name = u.first_name or u.username or str(u.telegram_id)
            user_info[u.telegram_id] = (name, u.timezone or "UTC")

    going = [user_info.get(v.user_id, (str(v.user_id), "UTC"))[0] for v in votes if v.status == "going"]
    maybe = [user_info.get(v.user_id, (str(v.user_id), "UTC"))[0] for v in votes if v.status == "maybe"]
    
    slot_utc_str = game.confirmed_time_utc or ""
    
    # Group by timezone for breakdown
    tz_groups = {}
    for v in votes:
        if v.status in ["going", "maybe"]:
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
            tz_lines.append(f"• *{local_time}* ({tz_str}): {', '.join(players)}")
            
    time_breakdown_text = "\n".join(tz_lines) if tz_lines else "TBD"

    summary = (
        f"🎮 *Ready to confirm the game?*\n\n"
        f"⏰ *Local Times:*\n{time_breakdown_text}\n\n"
        f"✅ *Going:* {', '.join(going) if going else '—'}\n"
        f"🤔 *Maybe:* {', '.join(maybe) if maybe else '—'}\n"
    )

    if update.effective_message:
        await update.effective_message.reply_text(
            summary,
            parse_mode="Markdown",
            reply_markup=confirm_kb(),
        )

