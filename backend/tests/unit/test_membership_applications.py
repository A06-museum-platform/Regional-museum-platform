"""Membership application + /api/memberships/me tests (Flow 6).

A fake in-memory DB dispatches on the SQL text, as in the admin user tests.
"""

from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.member import membership as membership_router
from app.core.errors import ApiError, api_error_handler
from app.core.security import create_access_token
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


class _FakeDB:
    def __init__(self, role="Visitor", memberships=None):
        self.role = role
        # membership_id -> dict
        self.memberships = memberships or {}
        self.committed = False

    def _user_row(self):
        return type("Row", (), {
            "user_id": 5, "email": "grace@example.com", "first_name": "Grace",
            "last_name": "Hopper", "password_hash": "x", "is_active": True,
            "role_name": self.role,
        })()

    def _m_row(self, mid):
        m = self.memberships[mid]
        return type("Row", (), {
            "membership_id": mid, "user_id": 5, "email": "grace@example.com",
            "first_name": "Grace", "last_name": "Hopper", **m,
        })()

    async def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        if sql.startswith("SELECT u.user_id"):
            return _Result([self._user_row()])
        if "FOR UPDATE" in sql:
            return _Result()
        if sql.startswith("SELECT m.membership_id"):
            if "m.membership_id = :membership_id" in sql:
                return _Result([self._m_row(params["membership_id"])])
            ids = sorted(self.memberships, reverse=True)
            return _Result([self._m_row(i) for i in ids])
        if sql.startswith("INSERT INTO membership"):
            mid = max(self.memberships, default=0) + 1
            self.memberships[mid] = {
                "membership_type": params["membership_type"],
                "application_date": date.today(), "start_date": None,
                "expiry_date": None, "status": "Pending",
            }
            return _Result(scalar=mid)
        raise AssertionError(f"unexpected SQL: {sql}")

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass


def _client(db):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(membership_router.router)

    async def fake_session():
        yield db

    app.dependency_overrides[session_mod.get_session] = fake_session
    return TestClient(app)


AUTH = {"Authorization": f"Bearer {create_access_token(user_id=5, role='visitor')}"}


def _active(expiry=None):
    return {
        "membership_type": "Individual", "application_date": date(2026, 7, 1),
        "start_date": date(2026, 7, 2),
        "expiry_date": expiry or date.today() + timedelta(days=200), "status": "Active",
    }


def test_visitor_applies_creates_pending_row():
    db = _FakeDB()
    resp = _client(db).post(
        "/api/membership-applications", json={"plan_id": 2, "children_covered": 2}, headers=AUTH
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["tier"] == "family"
    assert body["plan"] == {"id": 2, "display_name": "Family"}
    assert body["member_ref"] == "SA-0001"
    assert body["adults_covered"] == 2 and body["children_covered"] == 2
    assert db.memberships[1]["membership_type"] == "Family"
    assert db.committed


def test_apply_requires_sign_in_401():
    resp = _client(_FakeDB()).post("/api/membership-applications", json={"plan_id": 1})
    assert resp.status_code == 401


def test_staff_cannot_apply_403():
    resp = _client(_FakeDB(role="Staff")).post(
        "/api/membership-applications", json={"plan_id": 1}, headers=AUTH
    )
    assert resp.status_code == 403


def test_unknown_plan_404():
    resp = _client(_FakeDB()).post(
        "/api/membership-applications", json={"plan_id": 99}, headers=AUTH
    )
    assert resp.status_code == 404


def test_too_many_children_400():
    resp = _client(_FakeDB()).post(
        "/api/membership-applications", json={"plan_id": 1, "children_covered": 1}, headers=AUTH
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_REQUEST"


def test_second_application_while_pending_409():
    db = _FakeDB()
    client = _client(db)
    client.post("/api/membership-applications", json={"plan_id": 1}, headers=AUTH)
    resp = client.post("/api/membership-applications", json={"plan_id": 3}, headers=AUTH)
    assert resp.status_code == 409
    assert resp.json()["code"] == "MEMBERSHIP_ACTIVE"
    assert len(db.memberships) == 1


def test_apply_while_active_409():
    db = _FakeDB(role="Member", memberships={1: _active()})
    resp = _client(db).post("/api/membership-applications", json={"plan_id": 1}, headers=AUTH)
    assert resp.status_code == 409


def test_me_none_404():
    resp = _client(_FakeDB()).get("/api/memberships/me", headers=AUTH)
    assert resp.status_code == 404


def test_me_returns_active_record():
    db = _FakeDB(role="Member", memberships={1: _active()})
    body = _client(db).get("/api/memberships/me", headers=AUTH).json()
    assert body["status"] == "active"
    assert body["tier"] == "individual"
    assert body["full_name"] == "Grace Hopper"


def test_active_past_expiry_reads_expired_and_can_reapply():
    db = _FakeDB(role="Member", memberships={1: _active(expiry=date(2026, 1, 1))})
    client = _client(db)
    assert client.get("/api/memberships/me", headers=AUTH).json()["status"] == "expired"
    resp = client.post("/api/membership-applications", json={"plan_id": 1}, headers=AUTH)
    assert resp.status_code == 200


def test_rejected_reads_revoked():
    db = _FakeDB(memberships={1: {**_active(), "status": "Rejected"}})
    assert _client(db).get("/api/memberships/me", headers=AUTH).json()["status"] == "revoked"
