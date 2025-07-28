from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import db_config

engine = create_async_engine(
    db_config.URL,
    echo=db_config.ECHO,
    pool_pre_ping=db_config.POOL_PRE_PING,
    pool_recycle=db_config.POOL_RECYCLE,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
