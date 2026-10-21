"""GET /api/opening-hours (docs/api-contract.md section 10).

The fake DB returns rows like database/seed/seed.sql, in table order
(Monday first): weekdays 09:00-17:00, Saturday 10:00-16:00, Sunday closed.
"""

import importlib
from datetime import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.public import opening_hours as opening_hours_router
from app.core import config
from app.core.errors import ApiError, api_error_handler
from app.db import session as session_mod


class _Result:
    def __init__(self, rows=()):
        self._rows = list(rows)

    def all(self):
        return self._rows


def _row(opening_hours_id, day, open_time=None, close_time=None):
    return type("Row", (), {
        "opening_hours_id": opening_hours_id, "day_of_week": day,
        "open_time": open_time, "close_time": close_time, "is_closed": open_time is None,
    })()


SEED_ROWS = [
    _row(1, "Monday", time(9), time(17)),
    _row(2, "Tuesday", time(9), time(17)),
    _row(3, "Wednesday", time(9), time(17)),
    _row(4, "Thursday", time(9), time(17)),
    _row(5, "Friday", time(9), time(17)),
    _row(6, "Saturday", time(10), time(16)),
    _row(7, "Sunday"),
]


class _FakeDB:
    def __init__(self, rows=SEED_ROWS):
        self.rows = rows
        self.queries = []

    async def execute(self, statement, params=None):
        sql = str(statement)
        self.queries.append(sql)
        if sql.startswith("SELECT oh.opening_hours_id"):
            return _Result(self.rows)
        raise AssertionError(f"unexpected SQL: {sql}")


def _client(db):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(opening_hours_router.router)

    async def fake_session():
        yield db

    app.dependency_overrides[session_mod.get_session] = fake_session
    return TestClient(app)


def _open(row_id, day, opens_at, closes_at):
    return {"id": row_id, "day_of_week": day, "opens_at": opens_at,
            "closes_at": closes_at, "is_closed": False, "note": ""}


def test_weekly_pattern_sunday_first_without_sign_in():
    resp = _client(_FakeDB()).get("/api/opening-hours")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "weekly": [
            {"id": 7, "day_of_week": 0, "opens_at": None, "closes_at": None,
             "is_closed": True, "note": ""},
            *[_open(day, day, "09:00", "17:00") for day in range(1, 6)],  # Mon-Fri
            _open(6, 6, "10:00", "16:00"),
        ],
        "overrides": [],
    }


def test_only_stored_days_are_listed_and_seconds_dropped():
    rows = [_row(3, "Wednesday", time(9, 30, 15), time(20)), _row(7, "Sunday")]
    weekly = _client(_FakeDB(rows=rows)).get("/api/opening-hours").json()["weekly"]
    assert [row["day_of_week"] for row in weekly] == [0, 3]
    assert (weekly[1]["opens_at"], weekly[1]["closes_at"]) == ("09:30", "20:00")


def test_reads_one_museums_rows():
    db = _FakeDB()
    _client(db).get("/api/opening-hours")
    assert "oh.museum_info_id = (SELECT MIN(museum_info_id) FROM opening_hours)" in db.queries[0]


def test_route_is_registered_on_the_app(monkeypatch, tmp_path):
    settings = config.Settings(_env_file=None, local_upload_dir=str(tmp_path))
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    main = importlib.import_module("app.main")
    assert "/api/opening-hours" in {route.path for route in main.app.routes}
