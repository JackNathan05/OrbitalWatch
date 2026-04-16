import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.async_database_url, echo=False, pool_size=20, max_overflow=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db():
    # Try to enable TimescaleDB in its own transaction — optional.
    # Railway's plain Postgres doesn't have this extension; that's fine.
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"))
        logger.info("TimescaleDB extension enabled.")
    except Exception as e:
        logger.info(f"TimescaleDB extension not available (using plain Postgres): {type(e).__name__}")

    # Create tables (works on any Postgres)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
