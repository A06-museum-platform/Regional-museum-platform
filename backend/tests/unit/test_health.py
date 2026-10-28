"""Liveness and readiness probes use a fake session, never a database."""

import asyncio
import importlib
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.db import session as session_mod


@pytest.fixture
def health_client(monkeypatch, tmp_path):
    settings = config.Settings(_env_file=None, local_upload_dir=str(tmp_path))
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    main = importlib.import_module("app.main")
    session = Mock(execute=AsyncMock(), close=AsyncMock())
    factory = Mock(return_value=session)
    monkeypatch.setattr(session_mod, "_factory", lambda: factory)
    with TestClient(main.app) as client:
        yield client, session, factory, main


def test_readiness_healthy(health_client):
    client, session, _, _ = health_client
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok", "database": "ok", "service": "museum-api",
    }
    assert str(session.execute.call_args.args[0]) == "SELECT 1"
    session.execute.assert_awaited_once()
    session.close.assert_awaited_once()


def test_readiness_query_failure(health_client):
    client, session, _, _ = health_client
    session.execute.side_effect = RuntimeError("secret connection string")
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded", "database": "unavailable", "service": "museum-api",
    }
    session.close.assert_awaited_once()


def test_readiness_session_creation_failure(health_client):
    client, _, factory, _ = health_client
    factory.side_effect = RuntimeError("secret connection string")
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"
    assert "secret" not in response.text


def test_readiness_timeout(health_client, monkeypatch):
    client, session, _, main = health_client
    wait_for = asyncio.wait_for

    async def short_wait(awaitable, timeout):
        assert timeout == 2.0
        return await wait_for(awaitable, timeout=0.01)

    async def stalled_query(*args):
        await asyncio.Event().wait()

    monkeypatch.setattr(main.asyncio, "wait_for", short_wait)
    session.execute.side_effect = stalled_query
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"
    session.close.assert_awaited_once()


def test_liveness_does_not_access_database(health_client):
    client, _, factory, _ = health_client
    factory.side_effect = AssertionError("Liveness must not open a DB session")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    factory.assert_not_called()
