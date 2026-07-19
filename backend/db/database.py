import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import get_settings

logger = logging.getLogger(__name__)

url = get_settings().DATABASE_URL
is_postgres = "postgresql" in url
connect_args = {"check_same_thread": False} if "sqlite" in url else {}
engine = create_async_engine(url, echo=False, connect_args=connect_args)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    # Import models so their tables register on Base.metadata before create_all runs.
    from db import models  # noqa: F401

    async with engine.begin() as conn:
        if is_postgres:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        await conn.run_sync(Base.metadata.create_all)

    if is_postgres:
        # Separate transaction: if hypertable conversion fails for any reason, it must
        # not roll back the table/extension creation that just committed above.
        try:
            async with engine.begin() as conn:
                await conn.execute(text(
                    "SELECT create_hypertable('sensor_readings', 'ts', if_not_exists => TRUE, "
                    "migrate_data => TRUE)"
                ))
        except Exception as exc:  # pragma: no cover — extension unavailable in some envs
            logger.warning("Could not create Timescale hypertable for sensor_readings: %s", exc)


async def get_db():
    async with async_session() as session:
        yield session
