"""GET /api/auth/me tests (docs/api-contract.md section 10).

Same fake-DB setup as test_auth_login.py. The front end clears its stored
token only on 401, so every failure here must be 401 -- never 404/500.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.public import auth as auth_router
from app.core.errors import ApiError, api_error_handler
from app.core.security import create_access_token
from app.db import session as session_mod


class _Result:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _FakeDB:
    def __init__(self, row):
        self._row = row

    async def execute(self, *args, **kwargs):
        return _Result(self._row)


def _row(role="Member", is_active=True):
    return type(
        "Row",
        (),
        {
            "user_id": 42,
            "email": "ben@example.com",
            "first_name": "Ben",
            "last_name": "Wilson",
            "password_hash": "unused",
            "role_name": role,
            "is_active": is_active,
        },
    )()


def _client(row):
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(auth_router.router)

    async def fake_session():
        yield _FakeDB(row)

    app.dependency_overrides[session_mod.get_session] = fake_session
    return TestClient(app)


def _auth(user_id=42, role="member"):
    token = create_access_token(user_id=user_id, role=role)
    return {"Authorization": f"Bearer {token}"}


def test_me_valid_token_returns_user():
    client = _client(_row(role="Member"))
    resp = client.get("/api/auth/me", headers=_auth())
    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "id": 42,
        "email": "ben@example.com",
        "display_name": "Ben Wilson",
        "role": "member",
    }


def test_me_without_token_401():
    client = _client(_row())
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_REQUIRED"


def test_me_deleted_user_401():
    # Token is validly signed, but the account no longer exists.
    client = _client(None)
    resp = client.get("/api/auth/me", headers=_auth())
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_INVALID"


def test_me_disabled_user_401():
    # An admin disabled the account after the token was issued.
    client = _client(_row(is_active=False))
    resp = client.get("/api/auth/me", headers=_auth())
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_INVALID"
