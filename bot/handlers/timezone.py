"""Timezone selection and confirmation callback handlers."""
import logging

from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.builders import (
    date_selection_kb,
    timezone_confirm_kb,
    timezone_list_kb,
)
from db.models import User
from db.session import AsyncSessionFactory

logger = logging.getLogger(__name__)


async def tz_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle tz_select:<tz_key> — save the chosen timezone to DB."""
    query = update.callback_query
    await query.answer()

    tz_key = query.data.split(":", 1)[1]
    user = update.effective_user

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == user.id)
        )
        db_user = result.scalar_one_or_none()
        if db_user is None:
            db_user = User(
                telegram_id=user.id,
                username=user.username or user.first_name,
                timezone=tz_key,
            )
            session.add(db_user)
        else:
            db_user.timezone = tz_key
        await session.commit()

    await query.edit_message_text(
        f"✅ Timezone set to *{tz_key}*.\n\n"
        "Use /party to start planning a gaming session! 🎮",
        parse_mode="Markdown",
    )


async def tz_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle tz_confirm:yes / tz_confirm:change during /party flow."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":", 1)[1]

    if action == "yes":
        # Proceed to date selection
        await query.edit_message_text(
            "📅 *When do you want to play?*",
            parse_mode="Markdown",
            reply_markup=date_selection_kb(),
        )
    elif action == "change":
        await query.edit_message_text(
            "Choose your timezone:",
            reply_markup=timezone_list_kb(),
        )
