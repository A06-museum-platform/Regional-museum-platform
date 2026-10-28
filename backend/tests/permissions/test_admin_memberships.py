"""Admin membership approval tests (docs/api-contract.md section 10).

Role-permission matrix row "Approve or reject membership applications":
admin only. A fake in-memory DB dispatches on the SQL text.
"""

from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin import memberships as admin_router
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
    def __init__(self, caller_role="Admin"):
        self.caller_role = caller_role
        self.memberships = {
            7: {"user_id": 5, "membership_type": "Family", "status": "Pending",
                "application_date": date(2026, 10, 1), "start_date": None, "expiry_date": None},
        }
        self.role_grants = []
        self.committed = False

    def _m_row(self, mid):
        return type("Row", (), {
            "membership_id": mid, "email": "grace@example.com",
            "first_name": "Grace", "last_name": "Hopper", **self.memberships[mid],
        })()

    async def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        if sql.startswith("SELECT u.user_id"):
            return _Result([type("Row", (), {
                "user_id": 1, "email": "admin@museum.org", "first_name": "A", "last_name": "B",
                "password_hash": "x", "is_active": True, "role_name": self.caller_role,
            })()])
        if sql.startswith("SELECT COUNT(*)"):
            return _Result(scalar=len(self.memberships))
        if sql.startswith("SELECT m.membership_id"):
            if "m.membership_id = :membership_id" in sql:
                mid = params["membership_id"]
                return _Result([self._m_row(mid)] if mid in self.memberships else [])
            return _Result([self._m_row(mid) for mid in sorted(self.memberships)])
        if sql.startswith("UPDATE membership"):
            m = self.memberships[params["membership_id"]]
            if m["status"] != "Pending":
                return _Result()
            if "'Active'" in sql:
                m.update(status="Active", start_date=date.today(),
                         expiry_date=date(date.today().year + 1, date.today().month, 1))
            else:
                m["status"] = "Rejected"
            return _Result([(m["user_id"],)])
        if sql.startswith("INSERT INTO user_role"):
            self.role_grants.append(params["user_id"])
            return _Result()
        raise AssertionError(f"unexpected SQL: {sql}")

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass


def _client(db):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(admin_router.router)

    async def fake_session():
        yield db

    app.dependency_overrides[session_mod.get_session] = fake_session
    return TestClient(app)


AUTH = {"Authorization": f"Bearer {create_access_token(user_id=1, role='admin')}"}
URL = "/api/membership-applications"


def test_list_pending():
    body = _client(_FakeDB()).get(f"{URL}?status=pending", headers=AUTH).json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "pending"
    assert body["items"][0]["tier"] == "family"


def test_invalid_status_filter_422():
    assert _client(_FakeDB()).get(f"{URL}?status=bogus", headers=AUTH).status_code == 422


def test_approve_activates_and_grants_member_role():
    db = _FakeDB()
    resp = _client(db).post(f"{URL}/7/approve", headers=AUTH)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["approved_at"] == date.today().isoformat()
    assert body["expires_at"] is not None
    assert db.role_grants == [5]
    assert db.committed


def test_reject():
    db = _FakeDB()
    resp = _client(db).post(f"{URL}/7/reject", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"
    assert db.role_grants == []


def test_decide_twice_409():
    db = _FakeDB()
    client = _client(db)
    client.post(f"{URL}/7/approve", headers=AUTH)
    resp = client.post(f"{URL}/7/reject", headers=AUTH)
    assert resp.status_code == 409
    assert resp.json()["code"] == "NOT_PENDING"
    assert db.memberships[7]["status"] == "Active"


def test_unknown_application_404():
    resp = _client(_FakeDB()).post(f"{URL}/999/approve", headers=AUTH)
    assert resp.status_code == 404


def test_staff_cannot_approve_403():
    db = _FakeDB(caller_role="Staff")
    resp = _client(db).post(f"{URL}/7/approve", headers=AUTH)
    assert resp.status_code == 403
    assert db.memberships[7]["status"] == "Pending"


def test_anonymous_list_401():
    assert _client(_FakeDB()).get(URL).status_code == 401


# --- /api/admin/members (the admin Members screen's request shape) ---

from app.api.admin import members as members_router  # noqa: E402


def _members_client(db):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(members_router.router)

    async def fake_session():
        yield db

    app.dependency_overrides[session_mod.get_session] = fake_session
    return TestClient(app)


def test_members_screen_staff_403():
    resp = _members_client(_FakeDB(caller_role="Staff")).get("/api/admin/members", headers=AUTH)
    assert resp.status_code == 403


def test_members_screen_revoke_requires_reason_422():
    resp = _members_client(_FakeDB()).post(
        "/api/admin/members/7/revoke", json={"reason": "  "}, headers=AUTH
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "REASON_REQUIRED"


def test_members_screen_approve_shares_contract_logic():
    db = _FakeDB()
    resp = _members_client(db).post("/api/admin/members/7/approve", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"
    assert db.role_grants == [5]
