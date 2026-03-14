"""Availability range handler — collect user time ranges for range mode."""
import logging
import re
from datetime import date, datetime

import pytz
from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler

from bot.handlers.party import PENDING_GAME_KEY, PENDING_DATE_KEY
from bot.keyboards.builders import availability_kb, confirm_kb
from db.models import Availability, Game, User
from db.session import AsyncSessionFactory
from services.planner import find_best_slot_for_game

logger = logging.getLogger(__name__)

AWAITING_RANGE = "awaiting_range"  # conversation state key in user_data
TIME_RANGE_RE = re.compile(r"^(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})$")


async def availability_add_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle availability:add callback — prompt user for their time range."""
    query = update.callback_query
    await query.answer()

    context.user_data[AWAITING_RANGE] = True  # flag for the message handler below
    await query.message.reply_text(
        "📩 Please send your available time range, e.g. `20:00-23:00`\n"
        "(Use 24-hour format, times in your local timezone)",
        parse_mode="Markdown",
    )


async def availability_text_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Parse free-text availability range like '20:00-23:00' and store it."""
    if not context.user_data.get(AWAITING_RANGE):
        return  # not awaiting input from this user

    user = update.effective_user
    chat = update.effective_chat
    text = (update.message.text or "").strip()

    match = TIME_RANGE_RE.match(text)
    if not match:
        await update.message.reply_text(
            "❌ Format not recognised. Please send a range like `20:00-23:00`.",
            parse_mode="Markdown",
        )
        return

    start_str, end_str = match.group(1), match.group(2)
    game_id = context.chat_data.get(PENDING_GAME_KEY)
    today_str = context.chat_data.get(PENDING_DATE_KEY, date.today().isoformat())

    async with AsyncSessionFactory() as session:
        # Get user timezone
        user_result = await session.execute(
            select(User).where(User.telegram_id == user.id)
        )
        db_user = user_result.scalar_one_or_none()
        tz_str = (db_user.timezone if db_user else None) or "UTC"
        tz = pytz.timezone(tz_str)

        # Parse times and convert to UTC
        start_naive = datetime.strptime(f"{today_str} {start_str}", "%Y-%m-%d %H:%M")
        end_naive = datetime.strptime(f"{today_str} {end_str}", "%Y-%m-%d %H:%M")
        start_utc = tz.localize(start_naive).astimezone(pytz.utc)
        end_utc = tz.localize(end_naive).astimezone(pytz.utc)

        # Upsert availability
        avail_result = await session.execute(
            select(Availability).where(
                Availability.game_id == game_id,
                Availability.user_id == user.id,
            )
        )
        avail = avail_result.scalar_one_or_none()
        if avail is None:
            avail = Availability(
                game_id=game_id,
                user_id=user.id,
                start_time_utc=start_utc.isoformat(),
                end_time_utc=end_utc.isoformat(),
            )
            session.add(avail)
        else:
            avail.start_time_utc = start_utc.isoformat()
            avail.end_time_utc = end_utc.isoformat()
        await session.commit()

        # Compute best slot so far
        best = await find_best_slot_for_game(session, game_id)

    context.user_data[AWAITING_RANGE] = False  # clear flag

    await update.message.reply_text(
        f"✅ Got it, *{user.first_name}*! Your range: *{start_str}–{end_str}* saved.\n\n"
        f"{'🏆 Best overlap so far: *' + best['slot_utc'][11:16] + '* UTC (' + ', '.join(best['users']) + ')' if best else 'Waiting for more responses…'}\n\n"
        "Others can still add availability.",
        parse_mode="Markdown",
        reply_markup=availability_kb() if best is None else confirm_kb(),
    )
