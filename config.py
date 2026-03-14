"""Central configuration loaded from environment variables."""
import os
from dotenv import load_dotenv  # optional; works fine without it too

load_dotenv()  # load .env if present (ignored in Docker where env is injected)

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://partytime:partytime@localhost:5432/partytime",
)
REMINDER_OFFSET_MINUTES: int = int(os.environ.get("REMINDER_OFFSET_MINUTES", "30"))
