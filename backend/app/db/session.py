"""Async SQLAlchemy engine / session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_engine = None
_SessionFactory = None


def _factory() -> async_sessionmaker[AsyncSession]:
    global _engine, _SessionFactory
    if _SessionFactory is None:
        url = get_settings().database_url
        # SQLAlchemy asyncio needs the asyncpg driver scheme.
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        _engine = create_async_engine(url, pool_pre_ping=True)
        _SessionFactory = async_sessionmaker(_engine, expire_on_commit=False)
    return _SessionFactory


async def get_session():
    session = _factory()()
    try:
        yield session
    finally:
        await session.close()
