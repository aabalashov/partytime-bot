"""Reminder scheduling via PTB JobQueue."""
import logging
from datetime import datetime, timedelta, timezone

from telegram.ext import ContextTypes

from config import REMINDER_OFFSET_MINUTES

logger = logging.getLogger(__name__)


async def _send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """JobQueue callback — fires 30 min before the game."""
    job = context.job
    data: dict = job.data  # type: ignore[assignment]
    chat_id: int = data["chat_id"]
    players: list[str] = data.get("players", [])
    slot_label: str = data["slot_label"]

    player_list = "\n".join(f"• {p}" for p in players) if players else "—"
    text = (
        f"⏰ *Game starts in {REMINDER_OFFSET_MINUTES} minutes!*\n\n"
        f"🕹 Scheduled for: *{slot_label}*\n\n"
        f"*Players:*\n{player_list}"
    )
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")


def schedule_reminder(
    application,
    game_id: int,
    game_time_utc: datetime,
    chat_id: int,
    players: list[str],
    slot_label: str,
) -> None:
    """Schedule a reminder job REMINDER_OFFSET_MINUTES before game_time_utc."""
    reminder_time = game_time_utc - timedelta(minutes=REMINDER_OFFSET_MINUTES)
    now = datetime.now(tz=timezone.utc)

    if reminder_time <= now:
        logger.warning(
            "Reminder time %s is in the past for game %d, skipping.", reminder_time, game_id
        )
        return

    application.job_queue.run_once(
        _send_reminder,
        when=reminder_time,
        data={"chat_id": chat_id, "players": players, "slot_label": slot_label},
        name=f"reminder_{game_id}",
    )
    logger.info("Reminder scheduled for game %d at %s UTC", game_id, reminder_time)
