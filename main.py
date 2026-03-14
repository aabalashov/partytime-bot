"""Bot application entry point — registers handlers and starts polling."""
import asyncio
import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import config
from bot.handlers.availability import availability_add_callback, availability_text_handler
from bot.handlers.cancel import cancel_command, confirm_command
from bot.handlers.confirm import confirm_callback
from bot.handlers.party import date_callback, party_command, time_callback
from bot.handlers.start import start_handler
from bot.handlers.timezone import tz_confirm_callback, tz_select_callback
from bot.handlers.voting import vote_callback, vote_tz_callback
from db.session import init_db

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Initialise the database on startup."""
    logger.info("Initialising database…")
    await init_db()
    logger.info("Database ready.")


def build_application() -> Application:
    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Commands
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler(["party", "game"], party_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("confirm", confirm_command))

    # Timezone callbacks
    app.add_handler(CallbackQueryHandler(tz_select_callback, pattern=r"^tz_select:"))
    app.add_handler(CallbackQueryHandler(tz_confirm_callback, pattern=r"^tz_confirm:"))

    # Planning flow callbacks
    app.add_handler(CallbackQueryHandler(date_callback, pattern=r"^date:"))
    app.add_handler(CallbackQueryHandler(time_callback, pattern=r"^time:"))

    # Voting callbacks
    app.add_handler(CallbackQueryHandler(vote_callback, pattern=r"^(vote:|confirm_ui:)"))
    app.add_handler(CallbackQueryHandler(vote_tz_callback, pattern=r"^vote_tz:"))

    # Availability callbacks
    app.add_handler(CallbackQueryHandler(availability_add_callback, pattern=r"^availability:add"))

    # Confirmation callbacks
    app.add_handler(CallbackQueryHandler(confirm_callback, pattern=r"^confirm:"))

    # Free-text message for availability range input
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, availability_text_handler)
    )

    return app


def main() -> None:
    logger.info("Starting PartyTime Bot…")
    app = build_application()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
