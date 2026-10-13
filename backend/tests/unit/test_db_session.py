"""The API accepts the same libpq-style staging URL as the ops scripts."""
import ssl
from types import SimpleNamespace
from unittest.mock import Mock

from app.db import session


def test_staging_sslmode_is_translated_for_asyncpg(monkeypatch):
    engine = Mock()
    monkeypatch.setattr(session, "_SessionFactory", None)
    monkeypatch.setattr(session, "_engine", None)
    monkeypatch.setattr(session, "create_async_engine", engine)
    monkeypatch.setattr(session, "async_sessionmaker", Mock())
    monkeypatch.setattr(session, "get_settings", lambda: SimpleNamespace(
        database_url="postgresql://test:test@example.invalid:5432/postgres?sslmode=require"
    ))
    session._factory()
    args, kwargs = engine.call_args
    assert args[0].drivername == "postgresql+asyncpg"
    assert "sslmode" not in args[0].query
    assert isinstance(kwargs["connect_args"]["ssl"], ssl.SSLContext)
    assert kwargs["connect_args"]["ssl"].minimum_version >= ssl.TLSVersion.TLSv1_2


def test_local_database_keeps_default_connection_settings(monkeypatch):
    engine = Mock()
    monkeypatch.setattr(session, "_SessionFactory", None)
    monkeypatch.setattr(session, "_engine", None)
    monkeypatch.setattr(session, "create_async_engine", engine)
    monkeypatch.setattr(session, "async_sessionmaker", Mock())
    monkeypatch.setattr(session, "get_settings", lambda: SimpleNamespace(
        database_url="postgresql://museum:museum@db:5432/museum"
    ))
    session._factory()
    assert engine.call_args[1]["connect_args"] == {}
