"""POST /api/auth/register tests (docs/api-contract.md section 10).

Same dependency-override approach as test_auth_login.py; the fake DB
dispatches on the SQL text and records what was written, so no live
database is needed.
"""

from fastapi import FastAPI
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api import deps
from app.api.public import auth as auth_router
from app.core.errors import ApiError, api_error_handler
from app.core.security import verify_password
from app.db import session as session_mod


class _Result:
    def __init__(self, row=None, scalar=None):
        self._row = row
        self._scalar = scalar

    def first(self):
        return self._row

    def scalar_one(self):
        return self._scalar


class _FakeDB:
    def __init__(self, email_taken=False, race=False):
        self.email_taken = email_taken
        self.race = race
        self.inserted = None
        self.role_insert = None
        self.committed = False
        self.rolled_back = False

    async def execute(self, statement, params=None):
        sql = str(statement)
        if sql.startswith("SELECT 1 FROM user_account"):
            return _Result(row=(1,) if self.email_taken else None)
        if sql.startswith("INSERT INTO user_account"):
            if self.race:
                raise IntegrityError(sql, params, Exception("duplicate key"))
            self.inserted = params
            return _Result(scalar=57)
        if sql.startswith("INSERT INTO user_role"):
            self.role_insert = params
            return _Result()
        raise AssertionError(f"unexpected SQL: {sql}")

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


def _client(db):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(auth_router.router)

    async def fake_session():
        yield db

    app.dependency_overrides[session_mod.get_session] = fake_session
    return TestClient(app)


BODY = {
    "email": "New.Visitor@Example.com",
    "password": "longenough",
    "first_name": "Grace",
    "last_name": "Hopper",
}


def test_register_creates_visitor_and_signs_in():
    db = _FakeDB()
    resp = _client(db).post("/api/auth/register", json=BODY)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"] == {
        "id": 57,
        "email": "new.visitor@example.com",
        "display_name": "Grace Hopper",
        "role": "visitor",
    }
    assert db.committed

    # Stored lower-cased, with a real bcrypt hash rather than the password.
    assert db.inserted["email"] == "new.visitor@example.com"
    assert db.inserted["password_hash"] != "longenough"
    assert verify_password("longenough", db.inserted["password_hash"])
    assert db.role_insert == {"user_id": 57, "role": "visitor"}

    payload = deps._decode(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=body["access_token"])
    )
    assert payload["sub"] == "57"
    assert payload["role"] == "visitor"


def test_register_email_taken_409():
    db = _FakeDB(email_taken=True)
    resp = _client(db).post("/api/auth/register", json=BODY)
    assert resp.status_code == 409
    assert resp.json()["code"] == "CONFLICT"
    assert db.inserted is None


def test_register_concurrent_duplicate_409():
    db = _FakeDB(race=True)
    resp = _client(db).post("/api/auth/register", json=BODY)
    assert resp.status_code == 409
    assert resp.json()["code"] == "CONFLICT"
    assert db.rolled_back and not db.committed


def test_register_short_password_422():
    resp = _client(_FakeDB()).post("/api/auth/register", json={**BODY, "password": "short"})
    assert resp.status_code == 422


def test_register_bad_email_422():
    resp = _client(_FakeDB()).post("/api/auth/register", json={**BODY, "email": "not-an-email"})
    assert resp.status_code == 422
