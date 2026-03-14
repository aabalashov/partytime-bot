"""Inline keyboard builders for all bot interactions (PRD §9.2)."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.utils.timezone import COMMON_TIMEZONES

# ---------------------------------------------------------------------------
# Timezone keyboards
# ---------------------------------------------------------------------------


def timezone_confirm_kb() -> InlineKeyboardMarkup:
    """Ask user to confirm their stored timezone."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, that's correct", callback_data="tz_confirm:yes")],
        [InlineKeyboardButton("✏️ Change timezone", callback_data="tz_confirm:change")],
    ])


def timezone_list_kb() -> InlineKeyboardMarkup:
    """Paginated list of common timezones."""
    rows = []
    for tz_key, label in COMMON_TIMEZONES:
        rows.append([InlineKeyboardButton(label, callback_data=f"tz_select:{tz_key}")])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# Planning flow keyboards
# ---------------------------------------------------------------------------


def date_selection_kb() -> InlineKeyboardMarkup:
    """Date picker (PRD §9.2 - Date Selection)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Today", callback_data="date:today")],
        [InlineKeyboardButton("📅 Tomorrow", callback_data="date:tomorrow")],
        [InlineKeyboardButton("📆 Choose date", callback_data="date:custom")],
    ])


def time_selection_kb() -> InlineKeyboardMarkup:
    """Time picker (PRD §9.2 - Time Selection). Expanded to include more hours."""
    # List of common gaming hours or a full grid. Let's provide a reasonable range.
    hours = [f"{h:02d}:00" for h in range(9, 24)]
    
    # Create a grid (3 columns)
    rows = []
    for i in range(0, len(hours), 3):
        row = [InlineKeyboardButton(h, callback_data=f"time:{h}") for h in hours[i:i+3]]
        rows.append(row)
        
    rows.append([InlineKeyboardButton("🔍 Find common time", callback_data="time:range")])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# Voting keyboards
# ---------------------------------------------------------------------------


def vote_kb() -> InlineKeyboardMarkup:
    """Going / Maybe / Can't voting buttons (PRD §9.2 - Voting Buttons).
    
    Includes Finalize and Cancel buttons which are protected by organizer checks in the handler.
    """
    rows = [
        [InlineKeyboardButton("✅ Going", callback_data="vote:going")],
        [InlineKeyboardButton("🤔 Maybe", callback_data="vote:maybe")],
        [InlineKeyboardButton("❌ Can't", callback_data="vote:no")],
        [InlineKeyboardButton("🕒 My Timezone", callback_data="vote_tz:check")],
        [
            InlineKeyboardButton("🏁 Finalize", callback_data="confirm_ui:trigger"),
            InlineKeyboardButton("🛑 Cancel Session", callback_data="confirm_ui:cancel_trigger")
        ]
    ]
        
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# Availability mode keyboard
# ---------------------------------------------------------------------------


def availability_kb() -> InlineKeyboardMarkup:
    """Add availability button (PRD §9.2 - Availability Mode)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add my availability", callback_data="availability:add")],
    ])


# ---------------------------------------------------------------------------
# Confirmation keyboard
# ---------------------------------------------------------------------------


def confirm_kb() -> InlineKeyboardMarkup:
    """Confirm / Change / Cancel buttons (PRD §9.2 - Confirmation)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm", callback_data="confirm:game")],
        [InlineKeyboardButton("🔄 Change", callback_data="confirm:change")],
        [InlineKeyboardButton("❌ Cancel", callback_data="confirm:cancel")],
    ])
