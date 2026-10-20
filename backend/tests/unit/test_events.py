"""Public event endpoints (docs/api-contract.md section 3)."""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.public import events as events_router
from app.core.errors import ApiError, api_error_handler
from app.db import session as session_mod


class _Result:
    def __init__(self, rows=(), scalar=None):
        self._rows = list(rows)
        self._scalar = scalar

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows

    def scalar_one(self):
        return self._scalar


def _row(event_id, title, event_time):
    return type("Row", (), {
        "event_id": event_id, "title": title, "description": "desc",
        "location": "Activity Room", "event_time": event_time, "thumbnail_url": None,
    })()


class _FakeDB:
    def __init__(self):
        self.rows = [
            _row(1, "Heritage Photography Workshop",
                 datetime(2026, 10, 18, 2, 30, tzinfo=timezone.utc)),
            _row(2, "Family Craft Morning",
                 datetime(2026, 10, 25, 23, 30, tzinfo=timezone.utc)),
        ]
        self.queries = []

    async def execute(self, statement, params=None):
        sql, params = str(statement), params or {}
        self.queries.append((sql, params))
        if sql.startswith("SELECT COUNT(*)"):
            return _Result(scalar=len(self.rows))
        if "WHERE ev.event_id = :event_id" in sql:
            return _Result([r for r in self.rows if r.event_id == params["event_id"]])
        return _Result(self.rows[: params["limit"]])


def _client(db):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(events_router.router)

    async def fake_session():
        yield db

    app.dependency_overrides[session_mod.get_session] = fake_session
    return TestClient(app)


def test_search_shape():
    resp = _client(_FakeDB()).get("/api/events?page=1&size=4")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"items", "total", "page", "size"}
    assert body["size"] == 4 and body["page"] == 1 and body["total"] == 2
    assert body["items"][0] == {
        "id": 1,
        "display_name": "Heritage Photography Workshop",
        "event_time": "2026-10-18T02:30:00Z",
        "description": "desc",
        "location": "Activity Room",
        "thumbnail_url": None,
    }


def test_search_paginates():
    db = _FakeDB()
    _client(db).get("/api/events?page=3&size=5")
    _sql, params = db.queries[-1]
    assert params["limit"] == 5 and params["offset"] == 10


def test_search_escapes_like_wildcards():
    db = _FakeDB()
    _client(db).get("/api/events?q=100%25_off")
    _count_sql, params = db.queries[0]
    assert params["q"] == "%100\\%\\_off%"


def test_tag_filter_matches_nothing():
    db = _FakeDB()
    body = _client(db).get("/api/events?tag=family").json()
    assert body["items"] == [] and body["total"] == 0
    assert db.queries == []


def test_detail_by_id():
    resp = _client(_FakeDB()).get("/api/events/2")
    assert resp.status_code == 200, resp.text
    assert resp.json()["display_name"] == "Family Craft Morning"


def test_detail_missing_404():
    resp = _client(_FakeDB()).get("/api/events/99")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Event not found", "code": "NOT_FOUND"}
