"""Permission matrix tests for the staff media endpoints.

Uses dependency overrides so no live database or Supabase bucket is
needed: only routing, require_staff gating and validation are exercised.
Row 1 of the role-permission matrix: privileged endpoints must be
unreachable without the required role.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.staff import media as media_router
from app.core.errors import ApiError, api_error_handler

STAFF = {"sub": "7", "role": "staff"}


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return self._rows


class _FakeDB:
    """Mimics the AsyncSession surface the router uses."""

    def __init__(self, owner_exists=True, media_rows=None):
        self.owner_exists = owner_exists
        self.media_rows = media_rows or []
        self.committed = False

    async def execute(self, *args, **kwargs):
        sql = str(args[0])
        if sql.startswith("SELECT 1 FROM"):
            return _Rows([(1,)] if self.owner_exists else [])
        if "RETURNING media_id" in sql:
            row = type(
                "Row",
                (),
                {
                    "media_id": 9,
                    "collection_item_id": 1,
                    "exhibition_id": None,
                    "event_id": None,
                    "url": "https://cdn.example/9.jpg",
                    "media_type": "image",
                    "storage": "supabase",
                    "sort_order": 0,
                    "is_primary": True,
                    "created_at": None,
                },
            )()
            return _Rows([row])
        if sql.startswith("SELECT media_id"):
            return _Rows(self.media_rows)
        return _Rows([])

    async def commit(self):
        self.committed = True


class _FakeStorage:
    async def upload(self, key, data, content_type):
        return "https://cdn.example/9.jpg"

    async def remove(self, key):
        return None


def _client(staff=None, db=None, storage=None):
    from app.api import deps
    from app.api.staff import media as m
    from app.db import session as session_mod

    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)
    app.include_router(m.router)

    async def fake_session():
        yield db or _FakeDB()

    async def fake_staff():
        if staff is None:
            raise ApiError(401, "Not authenticated", "AUTH_REQUIRED")
        if staff.get("role") not in ("staff", "admin"):
            raise ApiError(403, "Staff role required", "FORBIDDEN")
        return staff

    app.dependency_overrides[session_mod.get_session] = fake_session
    app.dependency_overrides[deps.require_staff] = fake_staff
    m._storage = lambda: (storage or _FakeStorage(), "supabase")  # noqa: E731
    return TestClient(app)


def _row(media_id=3):
    return type(
        "Row",
        (),
        {
            "media_id": media_id,
            "url": "https://cdn.example/3.jpg",
            "storage": "supabase",
        },
    )()


def test_anon_upload_rejected_401():
    client = _client(staff=None)
    resp = client.post(
        "/api/staff/collection-items/1/media",
        files={"file": ("a.jpg", b"data", "image/jpeg")},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "AUTH_REQUIRED"


def test_member_upload_rejected_403():
    client = _client(staff={"sub": "2", "role": "member"})
    resp = client.post(
        "/api/staff/collection-items/1/media",
        files={"file": ("a.jpg", b"data", "image/jpeg")},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_staff_upload_ok_201():
    client = _client(staff=STAFF)
    resp = client.post(
        "/api/staff/collection-items/1/media?is_primary=true",
        files={"file": ("a.jpg", b"data", "image/jpeg")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["media"]["media_id"] == 9
    assert body["thumbnail_url"] == "https://cdn.example/9.jpg"


def test_staff_upload_wrong_type_400():
    client = _client(staff=STAFF)
    resp = client.post(
        "/api/staff/events/1/media",
        files={"file": ("a.exe", b"data", "application/x-msdownload")},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_staff_upload_oversize_413():
    client = _client(staff=STAFF)
    resp = client.post(
        "/api/staff/events/1/media",
        files={"file": ("big.jpg", b"x" * (6 * 1024 * 1024), "image/jpeg")},
    )
    assert resp.status_code == 413
    assert resp.json()["code"] == "FILE_TOO_LARGE"


def test_staff_upload_unknown_owner_404():
    client = _client(staff=STAFF)
    resp = client.post(
        "/api/staff/paintings/1/media",
        files={"file": ("a.jpg", b"data", "image/jpeg")},
    )
    assert resp.status_code == 404


def test_staff_upload_missing_owner_404():
    client = _client(staff=STAFF, db=_FakeDB(owner_exists=False))
    resp = client.post(
        "/api/staff/exhibitions/999/media",
        files={"file": ("a.jpg", b"data", "image/jpeg")},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


def test_anon_list_rejected_401():
    client = _client(staff=None)
    assert client.get("/api/staff/events/1/media").status_code == 401


def test_staff_delete_missing_404():
    client = _client(staff=STAFF, db=_FakeDB(media_rows=[]))
    assert client.delete("/api/staff/media/999").status_code == 404


def test_staff_delete_ok_204():
    client = _client(staff=STAFF, db=_FakeDB(media_rows=[_row()]))
    assert client.delete("/api/staff/media/3").status_code == 204
