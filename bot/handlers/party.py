"""Handler for /party command and date/time selection callbacks."""
import logging
from datetime import date, timedelta

from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.builders import (
    date_selection_kb,
    time_selection_kb,
    timezone_confirm_kb,
    vote_kb,
    availability_kb,
)
from db.models import Game, User
from db.session import AsyncSessionFactory
from services.session_manager import create_game, get_active_game

logger = logging.getLogger(__name__)

# We store the pending game_id in context.chat_data during the flow
PENDING_GAME_KEY = "pending_game_id"
PENDING_DATE_KEY = "pending_date"


async def party_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/party — entry point.

    1. Enforce one active session per chat.
    2. Confirm the initiator's timezone.
    3. If confirmed → date selection.
    """
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return

    async with AsyncSessionFactory() as session:
        # Enforce one-session-per-chat rule (PRD §9.5)
        active = await get_active_game(session, chat.id)
        if active is not None:
            await update.message.reply_text(
                "⚠️ A planning session is already active in this chat.\n"
                "Wait for it to finish or be cancelled."
            )
            return

        # Fetch user timezone
        result = await session.execute(
            select(User).where(User.telegram_id == user.id)
        )
        db_user = result.scalar_one_or_none()

        if db_user is None or db_user.timezone is None:
            await update.message.reply_text(
                "Please set your timezone first via /start."
            )
            return

        tz = db_user.timezone

    await update.message.reply_text(
        f"Your timezone is *{tz}*. Is this correct?",
        parse_mode="Markdown",
        reply_markup=timezone_confirm_kb(),
    )

    # Store initiator so tz_confirm can create the game later
    context.chat_data["initiator_id"] = user.id


async def date_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle date:<today|tomorrow|custom> callbacks."""
    query = update.callback_query
    await query.answer()
    chat = update.effective_chat
    user = update.effective_user

    choice = query.data.split(":", 1)[1]

    if choice == "custom":
        # TODO: implement ConversationHandler for custom date input
        await query.edit_message_text(
            "📆 Custom date not yet implemented in MVP.\n"
            "Please pick Today or Tomorrow.",
            reply_markup=date_selection_kb(),
        )
        return

    today = date.today()
    selected_date = today if choice == "today" else today + timedelta(days=1)
    label = "Today" if choice == "today" else "Tomorrow"

    # Create the game record now that we know the date
    initiator_id = context.chat_data.get("initiator_id", user.id)
    async with AsyncSessionFactory() as session:
        game = await create_game(session, chat.id, initiator_id)
        game.date = selected_date.isoformat()
        await session.commit()
        context.chat_data[PENDING_GAME_KEY] = game.id
        context.chat_data[PENDING_DATE_KEY] = selected_date.isoformat()

    await query.edit_message_text(
        f"🕐 *Pick a time* for *{label}* ({selected_date.strftime('%d %b')})",
        parse_mode="Markdown",
        reply_markup=time_selection_kb(),
    )


async def time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle time:<HH:MM> or time:range callbacks."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    chat = update.effective_chat

    choice = query.data.split(":", 1)[1]

    game_id = context.chat_data.get(PENDING_GAME_KEY)

    if choice == "range":
        # Switch to availability range mode
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(Game).where(Game.id == game_id))
            game = result.scalar_one_or_none()
            if game:
                game.mode = "range"
                await session.commit()

        await query.edit_message_text(
            f"📋 *{user.first_name}* is looking for a common time!\n\n"
            "Add your available time range (e.g. `20:00-23:00`).\n"
            "Others can add their availability too.",
            parse_mode="Markdown",
            reply_markup=availability_kb(),
        )
        return

    # Fixed time proposal (e.g. "21:00")
    time_label = choice  # e.g. "21:00"
    game_date = context.chat_data.get(PENDING_DATE_KEY, date.today().isoformat())

    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Game).where(Game.id == game_id))
        game = result.scalar_one_or_none()
        if game:
            game.mode = "fixed"
            
            # Fetch organizer's timezone to convert to UTC
            user_res = await session.execute(select(User).where(User.telegram_id == game.created_by))
            db_user = user_res.scalar_one_or_none()
            tz_str = db_user.timezone if db_user and db_user.timezone else "UTC"
            
            from datetime import datetime
            from bot.utils.timezone import local_to_utc
            
            # Create a naive local datetime
            naive_dt = datetime.fromisoformat(f"{game_date}T{time_label}:00")
            utc_dt = local_to_utc(naive_dt, tz_str)
            
            game.confirmed_time_utc = utc_dt.isoformat()
            await session.commit()

    # Post voting message to chat
    await query.edit_message_text(
        f"🎮 *{user.first_name}* wants to play at *{time_label}* on *{game_date}*\n\n"
        "Who can join?",
        parse_mode="Markdown",
        reply_markup=vote_kb(),
    )
