"""Async SQLAlchemy engine / session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.engine import make_url
import ssl

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
        parsed = make_url(url)
        connect_args = {}
        sslmode = parsed.query.get("sslmode")
        if sslmode is not None:
            # libpq URLs use sslmode; asyncpg expects its ssl argument instead.
            # Session pooling supports prepared statements, so keep defaults.
            parsed = parsed.difference_update_query(["sslmode"])
            if sslmode == "require":
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                connect_args["ssl"] = context
            else:
                connect_args["ssl"] = sslmode
        _engine = create_async_engine(parsed, pool_pre_ping=True, connect_args=connect_args)
        _SessionFactory = async_sessionmaker(_engine, expire_on_commit=False)
    return _SessionFactory


async def get_session():
    session = _factory()()
    try:
        yield session
    finally:
        await session.close()
