"""Handler for /start command and first-time timezone onboarding."""
import logging

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select

from bot.keyboards.builders import timezone_list_kb
from db.models import User
from db.session import AsyncSessionFactory

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command.

    If the user has no stored timezone, show the timezone picker.
    Otherwise show a welcome back message.
    """
    user = update.effective_user
    if user is None:
        return

    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == user.id)
        )
        db_user = result.scalar_one_or_none()

        if db_user is None:
            # First interaction — create user record
            db_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
            )
            session.add(db_user)
        else:
            # Update user info to keep it fresh
            db_user.username = user.username
            db_user.first_name = user.first_name
            
        await session.commit()
        await session.refresh(db_user)

    if db_user.timezone is None:
        await update.message.reply_text(
            "👋 Welcome to *PartyTime Bot!*\n\n"
            "I help your group find the best time to play online games together. 🎮\n\n"
            "First, let's set your timezone so I can show you times correctly:",
            parse_mode="Markdown",
            reply_markup=timezone_list_kb(),
        )
    else:
        await update.message.reply_text(
            f"👋 Welcome back, *{user.first_name}!*\n\n"
            "Use /party to start planning a gaming session. 🎮",
            parse_mode="Markdown",
        )
