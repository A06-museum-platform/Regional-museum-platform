"""Integration tests against a real PostgreSQL database.

Every test gets a freshly built database: the public schema is dropped, all
of database/migrations/*.sql are applied in order and database/seed/seed.sql
is loaded, exactly as a new local setup would be. The API then runs
in-process (Starlette TestClient), so these tests exercise the real SQL.

Where the database comes from:
  TEST_DATABASE_URL, else DATABASE_URL, else the local default
  postgresql://museum:museum@localhost:5432/museum_test

The database name must end in "_test" because the schema is wiped: a
pointer to any other database (such as the backend container's own
DATABASE_URL) is never touched, the integration suite is skipped instead.
It is also skipped when nothing is listening, so `pytest` still works on a
laptop without Postgres. CI provides museum_test.
"""

import asyncio
import os
from pathlib import Path

import asyncpg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

REPO = Path(__file__).resolve().parents[3]
MIGRATIONS = sorted((REPO / "database" / "migrations").glob("0*.sql"))
SEED = REPO / "database" / "seed" / "seed.sql"

DEFAULT_URL = "postgresql://museum:museum@localhost:5432/museum_test"
DB_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL") or DEFAULT_URL

PASSWORDS = {
    "alice@example.com": "Visitor123!",
    "ben@example.com": "Member123!",
    "staff@museum.org": "Staff123!",
    "admin@museum.org": "Admin123!",
}


def _check_url():
    name = make_url(DB_URL).database or ""
    if not name.endswith("_test"):
        pytest.skip(
            f"integration tests need a *_test database (got {name!r}); "
            "set TEST_DATABASE_URL, e.g. postgresql://museum:museum@localhost:5432/museum_test"
        )


async def _rebuild():
    conn = await asyncpg.connect(DB_URL.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        for path in MIGRATIONS:
            await conn.execute(path.read_text())
        await conn.execute(SEED.read_text())
    finally:
        await conn.close()


async def _reachable() -> bool:
    try:
        conn = await asyncpg.connect(
            DB_URL.replace("postgresql+asyncpg://", "postgresql://"), timeout=3
        )
    except Exception:
        return False
    await conn.close()
    return True


@pytest.fixture(scope="session")
def database_available():
    _check_url()
    if not asyncio.run(_reachable()):
        pytest.skip(f"no test database at {make_url(DB_URL).render_as_string(hide_password=True)}")


@pytest.fixture
def client(database_available, monkeypatch, tmp_path):
    """A TestClient on a freshly rebuilt and seeded database."""
    asyncio.run(_rebuild())

    monkeypatch.setenv("DATABASE_URL", DB_URL)
    # The container default (/app/uploads) doesn't exist on a CI runner.
    monkeypatch.setenv("LOCAL_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("MEDIA_BACKEND", "local")
    from app.core.config import get_settings
    from app.db import session as session_mod

    get_settings.cache_clear()
    # A new engine per test: pooled connections belong to the event loop of
    # the TestClient that opened them.
    session_mod._engine = None
    session_mod._SessionFactory = None

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    session_mod._engine = None
    session_mod._SessionFactory = None
    get_settings.cache_clear()


@pytest.fixture
def login(client):
    """login("ben@example.com") -> Authorization headers for that demo account."""

    def _login(email: str) -> dict:
        resp = client.post("/api/auth/login", json={"email": email, "password": PASSWORDS[email]})
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _login


def db_query(sql: str, *args):
    """Run one query on the test database and return its rows (for setup
    and assertions the API doesn't expose)."""

    async def _run():
        conn = await asyncpg.connect(DB_URL.replace("postgresql+asyncpg://", "postgresql://"))
        try:
            return await conn.fetch(sql, *args)
        finally:
            await conn.close()

    return asyncio.run(_run())
