"""SQLAlchemy ORM models matching the DB schema from the PRD."""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )




class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    created_by: Mapped[int] = mapped_column(BigInteger)  # telegram_id
    # ISO date string e.g. "2026-03-14"
    date: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # "fixed" or "range"
    mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # "active" | "confirmed" | "cancelled"
    status: Mapped[str] = mapped_column(String(16), default="active")
    # Confirmed slot in UTC ISO format
    confirmed_time_utc: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    availabilities: Mapped[list["Availability"]] = relationship(back_populates="game")
    votes: Mapped[list["Vote"]] = relationship(back_populates="game")


class Availability(Base):
    __tablename__ = "availabilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger)  # telegram_id
    start_time_utc: Mapped[str] = mapped_column(String(32))  # ISO UTC datetime
    end_time_utc: Mapped[str] = mapped_column(String(32))

    game: Mapped["Game"] = relationship(back_populates="availabilities")


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger)  # telegram_id
    slot_time_utc: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(
        Enum("going", "maybe", "no", name="vote_status")
    )

    game: Mapped["Game"] = relationship(back_populates="votes")
