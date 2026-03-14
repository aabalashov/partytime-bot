"""Voting handler — Going / Maybe / Can't (PRD §4, §9.4)."""
import logging

from sqlalchemy import select
from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers.party import PENDING_GAME_KEY
from bot.keyboards.builders import vote_kb, confirm_kb
from db.models import Game, Vote, User
from db.session import AsyncSessionFactory


async def _tally_text(session: AsyncSessionFactory, votes: list[Vote], slot_label: str) -> str:
    """Build the vote tally string for the message using display names."""
    # Fetch all users who voted to get their display names
    user_ids = [v.user_id for v in votes]
    result = await session.execute(
        select(User).where(User.telegram_id.in_(user_ids))
    )
    users = {u.telegram_id: u.first_name or u.username or str(u.telegram_id) for u in result.scalars().all()}

    def get_name(user_id):
        return users.get(user_id, str(user_id))

    going = [get_name(v.user_id) for v in votes if v.status == "going"]
    maybe = [get_name(v.user_id) for v in votes if v.status == "maybe"]
    no = [get_name(v.user_id) for v in votes if v.status == "no"]

    lines = [f"🎮 *{slot_label}*\n"]
    if going:
        lines.append(f"✅ Going ({len(going)}): {', '.join(going)}")
    if maybe:
        lines.append(f"🤔 Maybe ({len(maybe)}): {', '.join(maybe)}")
    if no:
        lines.append(f"❌ Can't ({len(no)}): {', '.join(no)}")
    lines.append("\nWho can join?")
    return "\n".join(lines)


async def vote_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle vote:<going|maybe|no> callbacks.

    Upserts the user's vote and edits the message in place (PRD §9.4).
    """
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    chat = update.effective_chat

    # Patterns: vote:going, confirm_ui:trigger, confirm_ui:cancel_trigger
    if query.data.startswith("confirm_ui:"):
        action = query.data.split(":", 1)[1]
        
        game_id = context.chat_data.get(PENDING_GAME_KEY)
        if game_id:
            async with AsyncSessionFactory() as session:
                game_result = await session.execute(select(Game).where(Game.id == game_id))
                game = game_result.scalar_one_or_none()
                if game and game.created_by != user.id:
                    await query.answer("Only the session organizer can do this.", show_alert=True)
                    return

        from bot.handlers.cancel import confirm_command, cancel_command
        if action == "trigger":
            await confirm_command(update, context)
        elif action == "cancel_trigger":
            await cancel_command(update, context)
        return

    status = query.data.split(":", 1)[1]  # "going", "maybe", or "no"
    game_id = context.chat_data.get(PENDING_GAME_KEY)

    if game_id is None:
        await query.answer("No active game session.", show_alert=True)
        return

    async with AsyncSessionFactory() as session:
        # Fetch game to check organizer and get label
        game_result = await session.execute(select(Game).where(Game.id == game_id))
        game: Game | None = game_result.scalar_one_or_none()
        if game is None:
            await query.answer("Game not found.", show_alert=True)
            return

        slot_label = "TBD"
        if game.confirmed_time_utc:
            # Format time in the organizer's timezone for the general chat
            creator_result = await session.execute(select(User).where(User.telegram_id == game.created_by))
            creator = creator_result.scalar_one_or_none()
            if creator and creator.timezone:
                from bot.utils.timezone import format_local_time
                local_time = format_local_time(game.confirmed_time_utc, creator.timezone)
                slot_label = f"{local_time} ({creator.timezone})"
            else:
                slot_label = f"{game.confirmed_time_utc[:16].replace('T', ' ')} (UTC)"

        # Upsert vote
        vote_result = await session.execute(
            select(Vote).where(
                Vote.game_id == game_id,
                Vote.user_id == user.id,
            )
        )
        vote = vote_result.scalar_one_or_none()
        if vote is None:
            vote = Vote(
                game_id=game_id,
                user_id=user.id,
                slot_time_utc=game.confirmed_time_utc or "TBD",
                status=status,
            )
            session.add(vote)
        else:
            vote.status = status
        await session.commit()

        # Reload all votes for this game
        all_votes_result = await session.execute(
            select(Vote).where(Vote.game_id == game_id)
        )
        all_votes = all_votes_result.scalars().all()
        
        text = await _tally_text(session, all_votes, slot_label)

    from telegram.error import BadRequest
    # Edit the existing message in place (PRD §9.4)
    try:
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=vote_kb(),
        )
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise e


async def vote_tz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle vote_tz:check callback. Shows the game time in the user's own timezone."""
    query = update.callback_query
    user = update.effective_user
    
    game_id = context.chat_data.get(PENDING_GAME_KEY)
    if not game_id:
        await query.answer("No active game session.", show_alert=True)
        return
        
    async with AsyncSessionFactory() as session:
        game_result = await session.execute(select(Game).where(Game.id == game_id))
        game: Game | None = game_result.scalar_one_or_none()
        if not game or not game.confirmed_time_utc:
            await query.answer("Game or time not found.", show_alert=True)
            return
            
        user_result = await session.execute(select(User).where(User.telegram_id == user.id))
        db_user = user_result.scalar_one_or_none()
        if not db_user or not db_user.timezone:
            await query.answer("You haven't set your timezone yet. Send /start to the bot in private messages to set it up!", show_alert=True)
            return
            
        tz_str = db_user.timezone
        from bot.utils.timezone import format_local_time
        local_time_str = format_local_time(game.confirmed_time_utc, tz_str)
        
        await query.answer(f"In your timezone ({tz_str}), the game starts at: {local_time_str}", show_alert=True)
