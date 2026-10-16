"""Login flow tests (docs/api-contract.md section 1).

Dependency overrides + a fake DB so no live database is needed, matching
the media permission tests. The real security helpers run: the stored
hash is produced by hash_password and checked by verify_password, and the
issued token is decoded with app.api.deps to prove the role claim is
readable by the staff/admin gates.
"""

from fastapi import FastAPI
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.api import deps
from app.api.public import auth as auth_router
from app.core.errors import ApiError, api_error_handler
from app.core.security import hash_password
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


def _row(email="member@example.com", password="s3cret", role="admin", is_active=True):
    return type(
        "Row",
        (),
        {
            "user_id": 42,
            "email": email,
            "first_name": "Ada",
            "last_name": "Lovelace",
            "password_hash": hash_password(password),
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


def test_login_ok_returns_token_and_user():
    client = _client(_row())
    resp = client.post(
        "/api/auth/login",
        json={"email": "member@example.com", "password": "s3cret"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["user"] == {
        "id": 42,
        "email": "member@example.com",
        "display_name": "Ada Lovelace",
        "role": "admin",
    }

    # The issued token must carry a role claim the gates can read back.
    payload = deps._decode(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=body["access_token"])
    )
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"


def test_login_wrong_password_401():
    client = _client(_row(password="s3cret"))
    resp = client.post(
        "/api/auth/login",
        json={"email": "member@example.com", "password": "nope"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_INVALID"


def test_login_unknown_email_401():
    client = _client(None)
    resp = client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "whatever"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_INVALID"


def test_login_lowercases_capitalised_db_role():
    # The role table stores "Admin"; the token and user must carry "admin"
    # so the require_admin / require_staff gates (which compare lower case)
    # accept it. Regression guard for the casing mismatch.
    client = _client(_row(role="Admin"))
    resp = client.post(
        "/api/auth/login",
        json={"email": "member@example.com", "password": "s3cret"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["user"]["role"] == "admin"

    token = resp.json()["access_token"]
    payload = deps._decode(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    )
    assert payload["role"] == "admin"


def test_login_disabled_account_403():
    client = _client(_row(is_active=False))
    resp = client.post(
        "/api/auth/login",
        json={"email": "member@example.com", "password": "s3cret"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ACCOUNT_DISABLED"


def test_login_disabled_account_wrong_password_still_401():
    # Don't reveal that a disabled account exists without the password.
    client = _client(_row(is_active=False))
    resp = client.post(
        "/api/auth/login",
        json={"email": "member@example.com", "password": "nope"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_INVALID"
