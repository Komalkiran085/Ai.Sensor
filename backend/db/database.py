from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import get_settings

url = get_settings().DATABASE_URL
connect_args = {"check_same_thread": False} if "sqlite" in url else {}
engine = create_async_engine(url, echo=False, connect_args=connect_args)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session() as session:
        yield session
