"""Async SQLAlchemy engine + session factory."""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    """Yields a single async session (context-manager friendly)."""
    async with AsyncSessionFactory() as session:
        yield session


async def init_db() -> None:
    """Create all tables (used in development / first-run).

    In production prefer proper Alembic migrations.
    """
    from db.models import Base  # local import to avoid circular deps at import time

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
