"""A server exception must remain readable only by the approved browser origins."""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.core import errors

PAGES = "https://regional-museum-platform.pages.dev"


@pytest.mark.parametrize("origin,allowed", [
    (PAGES, True),
    ("http://localhost:5173", True),
    ("https://unrelated.example", False),
    (None, False),
])
def test_unhandled_error_keeps_cors_policy_and_safe_json(monkeypatch, origin, allowed):
    monkeypatch.setattr(errors, "get_settings", lambda: SimpleNamespace(frontend_origin=PAGES))
    app = FastAPI()
    errors.install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[PAGES, "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post("/login")
    async def broken_login():
        raise RuntimeError("private database diagnostic")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/login", headers={"Origin": origin} if origin else {})

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Something went wrong on our side. Please try again.",
        "code": "INTERNAL_ERROR",
    }
    assert "private database diagnostic" not in response.text
    if allowed:
        assert response.headers["access-control-allow-origin"] == origin
        assert response.headers["access-control-allow-credentials"] == "true"
        assert "Origin" in response.headers["vary"]
    else:
        assert "access-control-allow-origin" not in response.headers
