"""GET /api/ticket-types (docs/decisions.md, "Booking and membership").

A fake in-memory DB dispatches on the SQL text, as in the membership tests.
"""

import importlib
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.public import ticket_types as ticket_types_router
from app.core import config
from app.core.errors import ApiError, api_error_handler
from app.core.security import create_access_token
from app.db import session as session_mod
from app.services.booking_service import to_cents


class _Result:
    def __init__(self, rows=()):
        self._rows = list(rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


def _ticket(ticket_type_id, name, price):
    return type("Row", (), {
        "ticket_type_id": ticket_type_id, "ticket_name": name,
        "description": f"{name} admission.", "price": Decimal(price),
    })()


# Same names and prices as the ticket_type rows in database/seed/seed.sql.
TICKETS = [
    _ticket(1, "Adult", "15.00"),
    _ticket(2, "Concession", "10.00"),
    _ticket(3, "Child", "7.50"),
    _ticket(4, "Member", "0.00"),
]


class _FakeDB:
    def __init__(self, membership=None, is_active=True):
        self.membership = membership  # membership columns, or None for no row
        self.is_active = is_active
        self.queries = []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.queries.append(sql)
        if sql.startswith("SELECT tt.ticket_type_id"):
            return _Result(TICKETS)
        if sql.startswith("SELECT u.user_id"):
            return _Result([type("Row", (), {
                "user_id": 5, "email": "grace@example.com", "first_name": "Grace",
                "last_name": "Hopper", "password_hash": "x",
                "is_active": self.is_active, "role_name": "Member",
            })()])
        if sql.startswith("SELECT m.membership_id"):
            if self.membership is None:
                return _Result()
            return _Result([type("Row", (), {
                "membership_id": 1, "user_id": 5, "email": "grace@example.com",
                "first_name": "Grace", "last_name": "Hopper", **self.membership,
            })()])
        raise AssertionError(f"unexpected SQL: {sql}")


def _client(db):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(ticket_types_router.router)

    async def fake_session():
        yield db

    app.dependency_overrides[session_mod.get_session] = fake_session
    return TestClient(app)


TOKEN = create_access_token(user_id=5, role="member")
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _membership(plan="Family", status="Active", expiry=None):
    return {
        "membership_type": plan, "application_date": date(2026, 7, 1),
        "start_date": date(2026, 7, 2),
        "expiry_date": expiry or date.today() + timedelta(days=200), "status": status,
        # Family and Patron plans cover 2 adults; these members registered 3 children.
        "children_covered": 3 if plan in ("Family", "Patron") else 0,
    }


def _names(body):
    return [item["name"] for item in body["items"]]


def test_public_list_in_cents_without_member_ticket():
    db = _FakeDB()
    resp = _client(db).get("/api/ticket-types")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"items", "total", "page", "size", "max_per_booking"}
    assert body["total"] == 3 and body["page"] == 1 and body["size"] == 12
    assert body["max_per_booking"] == 10
    assert body["items"][0] == {
        "id": 1, "name": "Adult", "description": "Adult admission.",
        "price_cents": 1500, "members_only": False, "max_quantity": 10,
    }
    assert [item["price_cents"] for item in body["items"]] == [1500, 1000, 750]
    # An anonymous caller costs one query: no user or membership lookup.
    assert len(db.queries) == 1


@pytest.mark.parametrize("plan, limit", [("Individual", 1), ("Family", 5), ("Patron", 5)])
def test_active_member_gets_free_member_ticket(plan, limit):
    db = _FakeDB(membership=_membership(plan=plan))
    body = _client(db).get("/api/ticket-types", headers=AUTH).json()
    assert _names(body) == ["Adult", "Concession", "Child", "Member"]
    assert body["total"] == 4
    assert body["items"][3] == {
        "id": 4, "name": "Member", "description": "Member admission.",
        "price_cents": 0, "members_only": True, "max_quantity": limit,
    }


@pytest.mark.parametrize("membership", [
    None,
    _membership(status="Pending"),
    _membership(status="Rejected"),
    _membership(expiry=date(2026, 1, 1)),  # Active row past its expiry date
], ids=["none", "pending", "rejected", "expired"])
def test_no_member_ticket_without_active_membership(membership):
    body = _client(_FakeDB(membership=membership)).get("/api/ticket-types", headers=AUTH).json()
    assert _names(body) == ["Adult", "Concession", "Child"]
    assert body["total"] == 3


def test_unknown_plan_still_covers_the_holder():
    db = _FakeDB(membership=_membership(plan="Founders"))
    member = _client(db).get("/api/ticket-types", headers=AUTH).json()["items"][-1]
    assert member["name"] == "Member" and member["max_quantity"] == 1


@pytest.mark.parametrize("token, is_active", [
    ("not-a-real-token", True),  # malformed or expired
    (TOKEN, False),              # account disabled since the token was issued
], ids=["bad-token", "disabled-account"])
def test_rejected_token_is_treated_as_anonymous(token, is_active):
    db = _FakeDB(membership=_membership(), is_active=is_active)
    resp = _client(db).get("/api/ticket-types", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert _names(resp.json()) == ["Adult", "Concession", "Child"]


def test_paginates_after_filtering():
    body = _client(_FakeDB()).get("/api/ticket-types?page=2&size=2").json()
    assert _names(body) == ["Child"]
    assert body["total"] == 3 and body["page"] == 2 and body["size"] == 2


@pytest.mark.parametrize("price, cents", [
    (Decimal("15.00"), 1500),
    (Decimal("7.50"), 750),
    (Decimal("19.99"), 1999),
    (Decimal("0.00"), 0),
    (0.29, 29),  # int(0.29 * 100) would give 28
])
def test_to_cents_is_exact(price, cents):
    assert to_cents(price) == cents


def test_route_is_registered_on_the_app(monkeypatch, tmp_path):
    settings = config.Settings(_env_file=None, local_upload_dir=str(tmp_path))
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    main = importlib.import_module("app.main")
    assert "get" in main.app.openapi()["paths"]["/api/ticket-types"]
