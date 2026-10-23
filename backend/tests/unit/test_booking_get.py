"""GET /api/bookings/{reference} (docs/decisions.md, "Booking and membership").

As in the demo's mock getBooking (frontend/src/api/bookings.js): the owner
sees their booking, staff and admins see any, and anyone else gets the same
404 as for a reference that doesn't exist. A fake DB dispatches on the SQL
text; "today" is Wednesday 2026-10-21 in Adelaide.
"""

import importlib
from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.member import bookings as bookings_router
from app.core import config
from app.core.errors import ApiError, api_error_handler
from app.core.security import create_access_token
from app.db import session as session_mod


class _Result:
    def __init__(self, rows=()):
        self._rows = list(rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


def _row(**columns):
    return type("Row", (), columns)()


def _booking(**changes):
    return {
        "booking_id": 1, "booking_reference": "SARHN-10591", "user_id": 5,
        "visit_date": date(2026, 10, 24), "window_start": time(10), "window_end": time(12),
        "visitor_first_name": "Grace", "visitor_last_name": "Hopper",
        "visitor_email": "grace@example.com", "visitor_mobile": None,
        "accessibility": ["step_free"], "status": "Reserved",
        "created_at": datetime(2026, 10, 21, 0, 30, tzinfo=timezone.utc),
        **changes,
    }


class _FakeDB:
    def __init__(self, caller_id=5, role="Visitor", booking=None):
        self.caller_id, self.role = caller_id, role
        self.booking = booking or _booking()
        self.queries, self.lookups = [], []

    async def execute(self, statement, params=None):
        sql, params = str(statement), params or {}
        self.queries.append(sql)
        if sql.startswith("SELECT u.user_id"):
            return _Result([_row(user_id=self.caller_id, email="caller@example.com",
                                 first_name="Ada", last_name="Lovelace", password_hash="x",
                                 is_active=True, role_name=self.role)])
        if sql.startswith("SELECT booking_id"):
            self.lookups.append(params["reference"])
            if params["reference"] != self.booking["booking_reference"]:
                return _Result()
            return _Result([_row(**self.booking)])
        if sql.startswith("SELECT tr.booking_id, tr.ticket_type_id"):
            assert params["ids"] == [self.booking["booking_id"]]
            booking_id = self.booking["booking_id"]
            return _Result([
                _row(booking_id=booking_id, ticket_type_id=1, ticket_name="Adult",
                     ticket_quantity=2, unit_price=Decimal("15.00")),
                _row(booking_id=booking_id, ticket_type_id=3, ticket_name="Child",
                     ticket_quantity=1, unit_price=Decimal("7.50")),
            ])
        if "AT TIME ZONE" in sql:
            return _Result([_row(today=date(2026, 10, 21), now_time=time(8))])
        raise AssertionError(f"unexpected SQL: {sql}")


def _client(db):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(bookings_router.router)

    async def fake_session():
        yield db

    app.dependency_overrides[session_mod.get_session] = fake_session
    return TestClient(app)


def _get(db, reference="SARHN-10591"):
    token = create_access_token(user_id=db.caller_id, role=db.role.lower())
    return _client(db).get(f"/api/bookings/{reference}",
                           headers={"Authorization": f"Bearer {token}"})


NOT_FOUND = {"detail": "We could not find that booking.", "code": "NOT_FOUND"}


def test_owner_sees_their_booking():
    resp = _get(_FakeDB())
    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "id": 1, "reference": "SARHN-10591", "user_id": 5, "visit_date": "2026-10-24",
        "arrival_window": {"start": "10:00", "end": "12:00"},
        "lines": [
            {"ticket_type_id": 1, "name": "Adult", "quantity": 2, "unit_price_cents": 1500},
            {"ticket_type_id": 3, "name": "Child", "quantity": 1, "unit_price_cents": 750},
        ],
        "total_cents": 3750,
        "visitor": {"first_name": "Grace", "last_name": "Hopper",
                    "email": "grace@example.com", "mobile": ""},
        "accessibility": ["step_free"],
        "status": "reserved",
        "payment": {"method": "simulated", "status": "simulated_paid"},
        "created_at": "2026-10-21T00:30:00Z",
    }


@pytest.mark.parametrize("caller_id, role, reference", [
    (9, "Visitor", "SARHN-10591"),  # someone else's booking
    (9, "Member", "SARHN-10591"),   # a member, but not the owner
    (5, "Visitor", "SARHN-00000"),  # a reference that doesn't exist
], ids=["other-visitor", "other-member", "unknown-reference"])
def test_others_and_unknown_references_get_the_same_404(caller_id, role, reference):
    db = _FakeDB(caller_id=caller_id, role=role)
    resp = _get(db, reference)
    assert resp.status_code == 404
    assert resp.json() == NOT_FOUND
    assert not any(sql.startswith("SELECT tr.ticket_type_id") for sql in db.queries)


@pytest.mark.parametrize("role", ["Staff", "Admin"])
def test_staff_and_admins_see_any_booking(role):
    resp = _get(_FakeDB(caller_id=9, role=role))
    assert resp.status_code == 200, resp.text
    assert resp.json()["user_id"] == 5


def test_reference_case_and_spaces_do_not_matter():
    db = _FakeDB()
    assert _get(db, "sarhn-10591%20").status_code == 200
    assert db.lookups == ["SARHN-10591"]


@pytest.mark.parametrize("visit_date, stored, shown", [
    (date(2026, 10, 20), "Reserved", "completed"),   # yesterday
    (date(2026, 10, 21), "Reserved", "reserved"),    # today: not over yet
    (date(2026, 10, 20), "Cancelled", "cancelled"),  # cancelled stays cancelled
], ids=["past", "today", "past-cancelled"])
def test_a_past_reservation_reads_completed(visit_date, stored, shown):
    db = _FakeDB(booking=_booking(visit_date=visit_date, status=stored))
    assert _get(db).json()["status"] == shown


def test_sign_in_required():
    resp = _client(_FakeDB()).get("/api/bookings/SARHN-10591")
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_REQUIRED"


def test_availability_is_matched_before_a_reference(monkeypatch, tmp_path):
    settings = config.Settings(_env_file=None, local_upload_dir=str(tmp_path))
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    main = importlib.import_module("app.main")
    paths = [route.path for route in main.app.routes]
    assert paths.index("/api/bookings/availability") < paths.index("/api/bookings/{reference}")
