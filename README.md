# PartyTime Bot 🎮

A Telegram bot that helps groups of friends find the best time to play online games together.

## Features

- `/party` — start a new planning session in any group or private chat
- **Fixed time proposal**: propose a specific time → others vote Going/Maybe/Can't
- **Availability range mode**: everyone submits their free windows → bot finds the best overlap
- **Timezone support**: every user stores their timezone; all times converted through UTC
- **One session per chat**: enforced to avoid confusion
- **Reminders**: sent 30 min before the confirmed game time

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Bot framework | python-telegram-bot v21 (async) |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy (async) + asyncpg |
| Reminders | PTB JobQueue (APScheduler) |
| Container | Docker + Docker Compose |

## Quick Start

### 1. Configure credentials

```bash
cd partytime_bot
cp .env.example .env
# Edit .env and set your BOT_TOKEN (from @BotFather on Telegram)
```

### 2. Run with Docker Compose

```bash
docker compose up --build
```

Postgres starts first, then the bot connects and creates the DB tables automatically.

### 3. Local development (no Docker)

```bash
# Create and activate a virtualenv
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set env vars locally
export BOT_TOKEN=your_token_here
export DATABASE_URL=postgresql+asyncpg://partytime:partytime@localhost:5432/partytime

python main.py
```

## Running Tests

Tests do not require a running database or bot token — they only test pure business logic.

```bash
cd partytime_bot
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Project Structure

```
partytime_bot/
├── bot/
│   ├── handlers/       # Telegram update handlers
│   │   ├── start.py    # /start, timezone onboarding
│   │   ├── party.py    # /party command + date/time selection
│   │   ├── timezone.py # tz confirmation & selection callbacks
│   │   ├── voting.py   # Going/Maybe/Can't vote callbacks
│   │   ├── availability.py  # Availability range submission
│   │   └── confirm.py  # Confirm/Change/Cancel callbacks
│   ├── keyboards/
│   │   └── builders.py # All inline keyboard factories
│   └── utils/
│       ├── timezone.py  # local↔UTC conversion helpers
│       └── scheduling.py # Overlap slot calculation (pure)
├── db/
│   ├── models.py        # SQLAlchemy ORM models
│   └── session.py       # Async engine + session factory
├── services/
│   ├── session_manager.py  # One-session-per-chat enforcement
│   ├── planner.py          # Best slot finder (DB → utils)
│   └── reminder.py         # JobQueue reminder scheduler
├── tests/
│   ├── test_scheduling.py
│   └── test_timezone.py
├── main.py              # Entrypoint — registers all handlers
├── config.py            # Env-based config
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Onboard, set timezone |
| `/party` | Start a new planning session |
| `/game` | Alias for `/party` |
| `/cancel` | Cancel the active planning session |
| `/confirm` | Show confirmation screen for the active session |

## Callback Format (PRD §9.3)

| Pattern | Action |
|---------|--------|
| `tz_select:<tz>` | Save selected timezone |
| `tz_confirm:yes\|change` | Confirm or change timezone |
| `date:today\|tomorrow\|custom` | Date selection |
| `time:<HH:MM>\|range` | Time selection or range mode |
| `vote:going\|maybe\|no` | Voting |
| `availability:add` | Add availability range |
| `confirm:game\|change\|cancel` | Confirm/change/cancel game |
