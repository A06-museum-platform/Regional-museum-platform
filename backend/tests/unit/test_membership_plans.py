"""GET /api/membership-plans tests (docs/api-contract.md section 6)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.public import membership_plans as plans_router


def _client():
    app = FastAPI()
    app.include_router(plans_router.router)
    return TestClient(app)


def test_lists_plans_publicly():
    resp = _client().get("/api/membership-plans")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert [p["key"] for p in body["items"]] == ["individual", "family", "patron"]
    family = body["items"][1]
    assert family["price_cents"] == 12000
    assert family["featured"] is True
    assert family["max_children"] == 3


def test_pagination():
    body = _client().get("/api/membership-plans?page=2&size=2").json()
    assert body["total"] == 3
    assert [p["key"] for p in body["items"]] == ["patron"]
