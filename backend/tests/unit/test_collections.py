"""Public collection endpoints (shape of frontend/src/api/collections.js)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.public import collections as collections_router
from app.core.errors import ApiError, api_error_handler
from app.db import session as session_mod
from app.services.collection_service import slugify


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


def _row(item_id, name, exhibition_id=None, exhibition_title=None):
    return type("Row", (), {
        "item_id": item_id, "exhibition_id": exhibition_id, "item_name": name,
        "description": "desc", "historical_period": "19th Century",
        "is_highlight": False, "image_url": None, "exhibition_title": exhibition_title,
    })()


class _FakeDB:
    def __init__(self):
        self.rows = [_row(1, "Historic Farming Tool", 1, "Stories of South Australia"),
                     _row(2, "Settler Diary")]
        self.queries = []

    async def execute(self, statement, params=None):
        sql, params = str(statement), params or {}
        self.queries.append((sql, params))
        if sql.startswith("SELECT COUNT(*)"):
            return _Result(scalar=len(self.rows))
        if "WHERE c.item_id = :item_id" in sql:
            return _Result([r for r in self.rows if r.item_id == params["item_id"]])
        return _Result(self.rows[: params["limit"]])


def _client(db):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(collections_router.router)

    async def fake_session():
        yield db

    app.dependency_overrides[session_mod.get_session] = fake_session
    return TestClient(app)


def test_slugify():
    assert slugify("Historic Farming Tool", 1) == "historic-farming-tool-1"
    assert slugify("!!!", 9) == "9"


def test_search_shape():
    resp = _client(_FakeDB()).get("/api/collection-items?page_size=4")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["page_size"] == 4 and body["total"] == 2
    item = body["items"][0]
    assert item["slug"] == "historic-farming-tool-1"
    assert item["title"] == "Historic Farming Tool"
    assert item["category"] == "uncategorised"
    assert item["period_text"] == "19th Century"


def test_search_escapes_like_wildcards():
    db = _FakeDB()
    _client(db).get("/api/collection-items?q=100%25_off")
    count_sql, params = db.queries[0]
    assert params["q"] == "%100\\%\\_off%"


def test_filters_on_missing_data_match_nothing():
    client = _client(_FakeDB())
    for qs in ("gallery=telegraph", "category=mineral", "family_friendly=true"):
        body = client.get(f"/api/collection-items?{qs}").json()
        assert body["items"] == [] and body["total"] == 0, qs
    assert client.get("/api/collection-items?category=uncategorised").json()["total"] == 2


def test_detail_by_slug_with_exhibition():
    resp = _client(_FakeDB()).get("/api/collection-items/historic-farming-tool-1")
    assert resp.status_code == 200, resp.text
    assert resp.json()["exhibition"] == {
        "id": 1, "title": "Stories of South Australia", "slug": "stories-of-south-australia-1",
    }


def test_detail_wrong_slug_404():
    client = _client(_FakeDB())
    assert client.get("/api/collection-items/settler-diary-1").status_code == 404
    assert client.get("/api/collection-items/no-such-thing").status_code == 404
