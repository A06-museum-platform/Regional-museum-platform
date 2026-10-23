"""Admin user management tests (docs/api-contract.md section 9).

Rows "Revoke member access" and "Assign or change user roles" of the
role-permission matrix: only an admin may call these endpoints, and the
role is read from the database, not the token, so a demoted or disabled
admin loses access on the next request. A fake in-memory DB stands in for
Postgres, dispatching on the SQL text.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.admin import users as users_router
from app.core.errors import ApiError, api_error_handler
from app.core.security import create_access_token
from app.db import session as session_mod

ROLES = {"visitor": 1, "member": 2, "staff": 3, "admin": 4}


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

    def scalar_one_or_none(self):
        return self._scalar


class _FakeDB:
    def __init__(self):
        # user_id -> [email, first, last, is_active, role]
        self.users = {
            1: ["admin@museum.org", "James", "Anderson", True, "Admin"],
            2: ["alice@example.com", "Alice", "Brown", True, "Visitor"],
        }
        self.committed = False

    def _row(self, user_id):
        email, first, last, active, role = self.users[user_id]
        return type(
            "Row",
            (),
            {
                "user_id": user_id,
                "email": email,
                "first_name": first,
                "last_name": last,
                "password_hash": "unused",
                "is_active": active,
                "role_name": role,
            },
        )()

    async def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        if sql.startswith("SELECT COUNT(*)"):
            return _Result(scalar=len(self.users))
        if sql.startswith("SELECT x.*"):  # filtered listing wraps USER_SELECT
            return _Result([self._row(uid) for uid in sorted(self.users)])
        if sql.startswith("SELECT u.user_id"):
            if "WHERE u.user_id" in sql:
                uid = params["user_id"]
                return _Result([self._row(uid)] if uid in self.users else [])
            return _Result([self._row(uid) for uid in sorted(self.users)])
        if sql.startswith("SELECT role_id FROM role"):
            return _Result(scalar=ROLES.get(params["role"]))
        if sql.startswith("DELETE FROM user_role"):
            return _Result()
        if sql.startswith("INSERT INTO user_role") and "role_id" not in params:
            return _Result()  # baseline Visitor / kept Member rows
        if sql.startswith("INSERT INTO user_role"):
            name = {v: k for k, v in ROLES.items()}[params["role_id"]]
            self.users[params["user_id"]][4] = name.capitalize()
            return _Result()
        if sql.startswith("UPDATE user_account SET is_active"):
            self.users[params["user_id"]][3] = params["is_active"]
            return _Result()
        raise AssertionError(f"unexpected SQL: {sql}")

    async def commit(self):
        self.committed = True


def _client(db):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(users_router.router)

    async def fake_session():
        yield db

    app.dependency_overrides[session_mod.get_session] = fake_session
    return TestClient(app)


def _auth(user_id, role):
    return {"Authorization": f"Bearer {create_access_token(user_id=user_id, role=role)}"}


ADMIN = _auth(1, "admin")


def test_list_users_includes_status():
    resp = _client(_FakeDB()).get("/api/users", headers=ADMIN)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    assert body["items"][1] == {
        "id": 2,
        "email": "alice@example.com",
        "display_name": "Alice Brown",
        "role": "visitor",
        "is_active": True,
    }


def test_admin_changes_role():
    db = _FakeDB()
    resp = _client(db).patch("/api/users/2", json={"role": "member"}, headers=ADMIN)
    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "member"
    assert db.committed


def test_admin_disables_and_restores():
    db = _FakeDB()
    client = _client(db)
    resp = client.patch("/api/users/2", json={"is_active": False}, headers=ADMIN)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    resp = client.patch("/api/users/2", json={"is_active": True}, headers=ADMIN)
    assert resp.json()["is_active"] is True


def test_admin_cannot_modify_self():
    db = _FakeDB()
    resp = _client(db).patch("/api/users/1", json={"is_active": False}, headers=ADMIN)
    assert resp.status_code == 409
    assert resp.json()["code"] == "CANNOT_MODIFY_SELF"
    assert db.users[1][3] is True


def test_unknown_user_404():
    resp = _client(_FakeDB()).patch("/api/users/99", json={"role": "staff"}, headers=ADMIN)
    assert resp.status_code == 404
    assert resp.json()["code"] == "USER_NOT_FOUND"


def test_invalid_role_422():
    resp = _client(_FakeDB()).patch("/api/users/2", json={"role": "superuser"}, headers=ADMIN)
    assert resp.status_code == 422


def test_non_admin_forbidden_403():
    db = _FakeDB()
    resp = _client(db).patch("/api/users/1", json={"role": "visitor"}, headers=_auth(2, "visitor"))
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_forged_admin_claim_uses_database_role_403():
    # Token says admin, but the database says Alice is a visitor (e.g. she
    # was demoted after the token was issued).
    resp = _client(_FakeDB()).get("/api/users", headers=_auth(2, "admin"))
    assert resp.status_code == 403


def test_disabled_admin_token_rejected_401():
    db = _FakeDB()
    db.users[1][3] = False
    resp = _client(db).get("/api/users", headers=ADMIN)
    assert resp.status_code == 401


def test_anonymous_401():
    resp = _client(_FakeDB()).get("/api/users")
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_REQUIRED"
