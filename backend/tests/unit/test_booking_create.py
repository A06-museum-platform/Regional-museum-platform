"""POST /api/bookings (docs/decisions.md, "Booking and membership").

The rules and messages follow the demo's mock createBooking in
frontend/src/api/bookings.js. A fake DB dispatches on the SQL text; its
ticket types and opening hours follow database/seed/seed.sql (Saturday
10:00-16:00, Sunday closed), and "today" is Wednesday 2026-10-21, 08:00.
"""

import importlib
import re
from datetime import date, datetime, time, timedelta, timezone
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


TICKETS = [
    _row(ticket_type_id=1, ticket_name="Adult", description="", price=Decimal("15.00")),
    _row(ticket_type_id=2, ticket_name="Concession", description="", price=Decimal("10.00")),
    _row(ticket_type_id=3, ticket_name="Child", description="", price=Decimal("7.50")),
    _row(ticket_type_id=4, ticket_name="Member", description="", price=Decimal("0.00")),
]
HOURS = {"Saturday": (time(10), time(16)), "Sunday": None}
CREATED_AT = datetime(2026, 10, 21, 0, 30, tzinfo=timezone.utc)


def _membership(plan="Individual", status="Active"):
    return {
        "membership_type": plan, "application_date": date(2026, 7, 1),
        "start_date": date(2026, 7, 2),
        "expiry_date": date.today() + timedelta(days=200), "status": status,
        # Family and Patron plans cover 2 adults; these members registered 3 children.
        "children_covered": 3 if plan in ("Family", "Patron") else 0,
    }


class _FakeDB:
    def __init__(self, membership=None, taken=None, used_references=0):
        self.membership = membership      # membership columns, or None for no row
        self.taken = taken or {}          # visit_time -> non-cancelled tickets
        self.used_references = used_references  # booking inserts that hit a used reference
        self.queries, self.bookings, self.lines = [], [], []
        self.lock = None
        self.committed = self.rolled_back = False

    async def execute(self, statement, params=None):
        sql, params = str(statement), params or {}
        self.queries.append(sql)
        if sql.startswith("SELECT u.user_id"):
            return _Result([_row(user_id=5, email="grace@example.com", first_name="Grace",
                                 last_name="Hopper", password_hash="x", is_active=True,
                                 role_name="Visitor")])
        if sql.startswith("SELECT m.membership_id"):
            if self.membership is None:
                return _Result()
            return _Result([_row(membership_id=1, user_id=5, email="grace@example.com",
                                 first_name="Grace", last_name="Hopper", **self.membership)])
        if sql.startswith("SELECT tt.ticket_type_id"):
            return _Result(TICKETS)
        if sql.startswith("SELECT pg_advisory_xact_lock"):
            self.lock = params
            return _Result()
        if "AT TIME ZONE" in sql:
            return _Result([_row(today=date(2026, 10, 21), now_time=time(8))])
        if "FROM opening_hours_override" in sql:
            return _Result()  # no dated exception: the weekly pattern applies
        if sql.startswith("SELECT oh.open_time"):
            span = HOURS.get(params["day"])
            if span is None:
                return _Result([_row(open_time=None, close_time=None, is_closed=True)])
            return _Result([_row(open_time=span[0], close_time=span[1], is_closed=False)])
        if sql.startswith("SELECT tr.visit_time"):
            return _Result([_row(visit_time=t, taken=n) for t, n in self.taken.items()])
        if sql.startswith("INSERT INTO booking"):
            if self.used_references:
                self.used_references -= 1
                return _Result()  # ON CONFLICT DO NOTHING: no row back
            self.bookings.append(params)
            return _Result([_row(
                booking_id=len(self.bookings), booking_reference=params["reference"],
                user_id=params["user_id"], visit_date=params["visit_date"],
                window_start=params["window_start"], window_end=params["window_end"],
                visitor_first_name=params["first_name"], visitor_last_name=params["last_name"],
                visitor_email=params["email"], visitor_mobile=params["mobile"],
                accessibility=params["accessibility"], status="Reserved", created_at=CREATED_AT,
            )])
        if sql.startswith("INSERT INTO ticket_reservation"):
            self.lines.append(params)
            return _Result()
        raise AssertionError(f"unexpected SQL: {sql}")

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


def _client(db):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(bookings_router.router)

    async def fake_session():
        yield db

    app.dependency_overrides[session_mod.get_session] = fake_session
    return TestClient(app)


# A signed-up account with no membership: the role a new visitor has.
AUTH = {"Authorization": f"Bearer {create_access_token(user_id=5, role='visitor')}"}


def _body(**changes):
    body = {
        "visit_date": "2026-10-24",  # Saturday
        "arrival_window": {"start": "10:00", "end": "12:00"},
        "lines": [{"ticket_type_id": 1, "quantity": 2}, {"ticket_type_id": 3, "quantity": 1}],
        "visitor": {"first_name": "Grace", "last_name": "Hopper",
                    "email": "grace@example.com", "mobile": ""},
        "accessibility": ["step_free"],
        "payment_acknowledged": True,
    }
    return {**body, **changes}


def _post(db, body, headers=AUTH):
    return _client(db).post("/api/bookings", json=body, headers=headers)


def _lines(*pairs):
    return [{"ticket_type_id": type_id, "quantity": quantity} for type_id, quantity in pairs]


def _error(resp, status, code, detail=None):
    assert resp.status_code == status, resp.text
    assert resp.json()["code"] == code
    if detail is not None:
        assert resp.json()["detail"] == detail


def test_creates_booking_with_reference_lines_and_total():
    db = _FakeDB()
    resp = _post(db, _body())
    assert resp.status_code == 201, resp.text
    booking = resp.json()
    assert re.fullmatch(r"SARHN-\d{5}", booking["reference"])
    assert booking == {
        "id": 1, "reference": booking["reference"], "user_id": 5, "visit_date": "2026-10-24",
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
        "checked_in": False,
        "created_at": "2026-10-21T00:30:00Z",
    }
    assert db.committed and not db.rolled_back
    saved = db.bookings[0]
    assert (saved["window_start"], saved["window_end"], saved["mobile"]) == (time(10), time(12), None)
    # One ticket_reservation row per type, under the booking, at the window's start.
    assert [(row["ticket_type_id"], row["quantity"], row["unit_price"]) for row in db.lines] == [
        (1, 2, Decimal("15.00")), (3, 1, Decimal("7.50")),
    ]
    assert all(row["booking_id"] == 1 and row["visit_date"] == date(2026, 10, 24)
               and row["visit_time"] == time(10) for row in db.lines)


def test_places_are_counted_only_after_the_window_lock():
    db = _FakeDB()
    _post(db, _body())
    lock_at = next(i for i, sql in enumerate(db.queries) if "pg_advisory_xact_lock" in sql)
    count_at = next(i for i, sql in enumerate(db.queries) if sql.startswith("SELECT tr.visit_time"))
    assert lock_at < count_at
    assert db.lock == {"day": date(2026, 10, 24).toordinal(), "minute": 600}


@pytest.mark.parametrize("acknowledged", [False, None], ids=["false", "missing"])
def test_payment_must_be_acknowledged(acknowledged):
    body = _body(payment_acknowledged=acknowledged)
    if acknowledged is None:
        del body["payment_acknowledged"]
    _error(_post(_FakeDB(), body), 400, "VALIDATION_ERROR",
           "Confirm that you understand no payment will be taken.")


@pytest.mark.parametrize("lines", [[], _lines((1, 0), (3, 0))], ids=["none", "all-zero"])
def test_needs_at_least_one_ticket(lines):
    _error(_post(_FakeDB(), _body(lines=lines)), 400, "VALIDATION_ERROR",
           "Choose at least one ticket.")


@pytest.mark.parametrize("lines", [_lines((1, 6), (3, 5)), _lines((1, 6), (1, 5))],
                         ids=["two-types", "one-type-split"])
def test_more_than_ten_tickets_is_409(lines):
    _error(_post(_FakeDB(), _body(lines=lines)), 409, "BOOKING_LIMIT_EXCEEDED",
           "One booking can hold up to 10 tickets. "
           "Make a second booking for the rest of your group.")


def test_unknown_ticket_type_is_400():
    _error(_post(_FakeDB(), _body(lines=_lines((99, 1)))), 400, "VALIDATION_ERROR",
           "That ticket type does not exist.")


@pytest.mark.parametrize("membership", [None, _membership(status="Pending")],
                         ids=["none", "pending"])
def test_member_ticket_needs_an_active_membership(membership):
    db = _FakeDB(membership=membership)
    _error(_post(db, _body(lines=_lines((4, 1)))), 403, "FORBIDDEN",
           "Member tickets need an active membership on this account.")
    assert db.bookings == []


@pytest.mark.parametrize("lines", [_lines((4, 2)), _lines((4, 1), (4, 1))],
                         ids=["one-line", "split-over-two-lines"])
def test_member_tickets_limited_to_the_people_covered(lines):
    db = _FakeDB(membership=_membership("Individual"))  # covers 1
    _error(_post(db, _body(lines=lines)), 400, "VALIDATION_ERROR",
           "Your membership covers 1 Member ticket per visit.")


def test_family_member_books_free_member_tickets():
    db = _FakeDB(membership=_membership("Family"))  # covers 2 adults + 3 children
    resp = _post(db, _body(lines=_lines((4, 5), (3, 1))))
    assert resp.status_code == 201, resp.text
    assert [(line["name"], line["unit_price_cents"]) for line in resp.json()["lines"]] == [
        ("Member", 0), ("Child", 750),
    ]
    assert resp.json()["total_cents"] == 750


@pytest.mark.parametrize("visit_date, start", [
    ("2026-10-24", "11:00"),  # not a window start
    ("2026-10-25", "10:00"),  # Sunday: closed
    ("2026-10-20", "10:00"),  # yesterday
    ("2026-10-24", "10am"),   # not HH:MM
], ids=["not-a-window", "closed-day", "past-date", "malformed"])
def test_arrival_window_must_be_on_offer(visit_date, start):
    db = _FakeDB()
    body = _body(visit_date=visit_date, arrival_window={"start": start, "end": "12:00"})
    _error(_post(db, body), 400, "VALIDATION_ERROR",
           "That arrival time is not available on this date.")
    assert db.bookings == [] and db.lines == [] and not db.committed


def test_not_enough_places_left_is_400():
    db = _FakeDB(taken={time(10): 58})
    _error(_post(db, _body()), 400, "INSUFFICIENT_TICKETS",
           "Only 2 places are left in that arrival window. "
           "Choose another time or fewer tickets.")
    assert db.bookings == [] and db.rolled_back and not db.committed


def test_exactly_the_places_left_can_be_booked():
    resp = _post(_FakeDB(taken={time(10): 57}), _body())  # 3 left, 3 tickets
    assert resp.status_code == 201, resp.text


def test_a_used_reference_is_skipped():
    db = _FakeDB(used_references=2)
    resp = _post(db, _body())
    assert resp.status_code == 201, resp.text
    assert sum(sql.startswith("INSERT INTO booking") for sql in db.queries) == 3


def test_gives_up_after_ten_used_references():
    db = _FakeDB(used_references=10)
    _error(_post(db, _body()), 500, "INTERNAL_ERROR")
    assert db.rolled_back and not db.committed


def test_accessibility_stored_once_and_names_trimmed():
    db = _FakeDB()
    body = _body(accessibility=["hearing_loop", "hearing_loop"],
                 visitor={"first_name": "  Grace ", "last_name": "Hopper",
                          "email": "grace@example.com", "mobile": " 0400 000 000 "})
    booking = _post(db, body).json()
    assert booking["accessibility"] == ["hearing_loop"]
    assert booking["visitor"]["first_name"] == "Grace"
    assert booking["visitor"]["mobile"] == "0400 000 000"


def test_sign_in_required():
    _error(_post(_FakeDB(), _body(), headers={}), 401, "AUTH_REQUIRED")


@pytest.mark.parametrize("changes", [
    {"visitor": {"first_name": " ", "last_name": "Hopper", "email": "grace@example.com"}},
    {"visitor": {"first_name": "Grace", "last_name": "Hopper", "email": "grace.example.com"}},
    {"visitor": {"first_name": "Grace", "last_name": "Hopper", "email": "grace@example.com",
                 "mobile": "call me"}},
    {"accessibility": ["guide_dog"]},
    {"lines": _lines((1, -1))},
    {"visit_date": "24/10/2026"},
], ids=["blank-name", "bad-email", "bad-mobile", "unknown-need", "negative-quantity", "bad-date"])
def test_malformed_body_is_rejected(changes):
    db = _FakeDB()
    assert _post(db, _body(**changes)).status_code == 422
    assert db.bookings == []


def test_route_is_registered_on_the_app(monkeypatch, tmp_path):
    settings = config.Settings(_env_file=None, local_upload_dir=str(tmp_path))
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    main = importlib.import_module("app.main")
    assert any(route.path == "/api/bookings" and "POST" in route.methods
               for route in main.app.routes)
