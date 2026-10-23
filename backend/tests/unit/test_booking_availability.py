"""GET /api/bookings/availability (docs/decisions.md, "Booking and membership").

A fake DB dispatches on the SQL text. Its opening hours follow
database/seed/seed.sql: weekdays 09:00-17:00, Saturday 10:00-16:00, Sunday
closed. "Today" is Wednesday 2026-10-21 unless a test says otherwise.
"""

import importlib
from datetime import date, time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.public import bookings as bookings_router
from app.core import config
from app.core.errors import ApiError, api_error_handler
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


WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
SEED_HOURS = {
    **{day: (time(9), time(17)) for day in WEEKDAYS},
    "Saturday": (time(10), time(16)),
    "Sunday": None,  # is_closed
}


class _FakeDB:
    def __init__(self, today=date(2026, 10, 21), now=time(8, 0), hours=SEED_HOURS, taken=None):
        self.today, self.now, self.hours = today, now, hours
        self.taken = taken or {}  # visit_time -> non-cancelled tickets
        self.queries = []

    async def execute(self, statement, params=None):
        sql, params = str(statement), params or {}
        self.queries.append((sql, params))
        if "AT TIME ZONE" in sql:
            return _Result([_row(today=self.today, now_time=self.now)])
        if "FROM opening_hours_override" in sql:
            return _Result()  # no dated exception: the weekly pattern applies
        if sql.startswith("SELECT oh.open_time"):
            if params["day"] not in self.hours:
                return _Result()
            span = self.hours[params["day"]]
            if span is None:
                return _Result([_row(open_time=None, close_time=None, is_closed=True)])
            return _Result([_row(open_time=span[0], close_time=span[1], is_closed=False)])
        if sql.startswith("SELECT tr.visit_time"):
            return _Result([_row(visit_time=t, taken=n) for t, n in self.taken.items()])
        raise AssertionError(f"unexpected SQL: {sql}")


def _client(db):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(bookings_router.router)

    async def fake_session():
        yield db

    app.dependency_overrides[session_mod.get_session] = fake_session
    return TestClient(app)


def _get(db, visit_date):
    resp = _client(db).get(f"/api/bookings/availability?date={visit_date}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _starts(body):
    return [window["start"] for window in body["windows"]]


def test_open_saturday_shape_and_windows():
    db = _FakeDB()
    assert _get(db, "2026-10-24") == {
        "date": "2026-10-24", "is_closed": False, "opens_at": "10:00",
        "closes_at": "16:00", "note": "",
        "windows": [
            {"start": "10:00", "end": "12:00", "places_left": 60},
            {"start": "12:00", "end": "14:00", "places_left": 60},
            {"start": "14:00", "end": "16:00", "places_left": 60},
        ],
    }
    hours_params = next(p for sql, p in db.queries if sql.startswith("SELECT oh.open_time"))
    assert hours_params["day"] == "Saturday"


def test_weekday_windows_fill_the_day():
    body = _get(_FakeDB(), "2026-10-22")  # Thursday, 09:00-17:00
    assert [(w["start"], w["end"]) for w in body["windows"]] == [
        ("09:00", "11:00"), ("11:00", "13:00"), ("13:00", "15:00"), ("15:00", "17:00"),
    ]


def test_places_left_counts_reservations_inside_each_window():
    db = _FakeDB(taken={time(10): 2, time(11, 30): 5, time(12): 70})
    body = _get(db, "2026-10-24")
    assert [w["places_left"] for w in body["windows"]] == [53, 0, 60]
    taken_sql = next(sql for sql, _ in db.queries if sql.startswith("SELECT tr.visit_time"))
    assert "tr.status <> 'Cancelled'" in taken_sql


def test_no_window_that_would_run_past_closing():
    hours = {**SEED_HOURS, "Saturday": (time(10), time(15, 30))}
    assert _starts(_get(_FakeDB(hours=hours), "2026-10-24")) == ["10:00", "12:00"]


@pytest.mark.parametrize("hours", [SEED_HOURS, {}], ids=["closed-sunday", "no-row"])
def test_closed_day(hours):
    assert _get(_FakeDB(hours=hours), "2026-10-25") == {
        "date": "2026-10-25", "is_closed": True, "opens_at": None,
        "closes_at": None, "note": "", "windows": [],
    }


def test_past_date_is_closed_after_one_query():
    db = _FakeDB()
    body = _get(db, "2026-10-20")
    assert body["is_closed"] and body["windows"] == []
    assert body["note"] == "That date has passed."
    assert len(db.queries) == 1  # only the clock


def test_booking_horizon_is_60_days():
    db = _FakeDB(today=date(2026, 10, 22))  # 60 days on is Monday 2026-12-21
    assert _starts(_get(db, "2026-12-21")) == ["09:00", "11:00", "13:00", "15:00"]
    body = _get(db, "2026-12-22")
    assert body["is_closed"] and body["note"] == "Bookings open 60 days ahead."


def test_today_hides_windows_that_have_started():
    # Wednesday 09:00-17:00: at 12:30 the 09:00 and 11:00 windows have begun,
    # and at 13:00 so has the one starting that minute.
    assert _starts(_get(_FakeDB(now=time(12, 30)), "2026-10-21")) == ["13:00", "15:00"]
    assert _starts(_get(_FakeDB(now=time(13, 0)), "2026-10-21")) == ["15:00"]


def test_today_after_last_window():
    body = _get(_FakeDB(now=time(15, 0)), "2026-10-21")
    assert body["is_closed"] and body["windows"] == []
    assert body["note"] == "Today's last arrival time has passed."
    assert body["opens_at"] == "09:00" and body["closes_at"] == "17:00"


def test_today_is_judged_in_museum_local_time():
    db = _FakeDB()
    _get(db, "2026-10-24")
    clock_sql = db.queries[0][0]
    assert "now() AT TIME ZONE 'Australia/Adelaide'" in clock_sql


@pytest.mark.parametrize("query", [
    "", "?date=", "?date=2026-13-01", "?date=2026-02-30", "?date=21/10/2026",
    "?date=20261024", "?date=2026-W43-6",
], ids=["missing", "empty", "month-13", "feb-30", "dd-mm-yyyy", "basic-format", "week-date"])
def test_bad_date_is_400(query):
    resp = _client(_FakeDB()).get(f"/api/bookings/availability{query}")
    assert resp.status_code == 400
    assert resp.json() == {"detail": "date must be YYYY-MM-DD", "code": "VALIDATION_ERROR"}


def test_route_is_registered_on_the_app(monkeypatch, tmp_path):
    settings = config.Settings(_env_file=None, local_upload_dir=str(tmp_path))
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    main = importlib.import_module("app.main")
    assert "/api/bookings/availability" in {route.path for route in main.app.routes}
