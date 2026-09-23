"""Shared FastAPI dependencies.

require_staff is the minimal role gate for the staff media endpoints.
It verifies the JWT signature and the role claim only — the full login
/ user-loading auth flow is Ray's M4 stream (backend/api/ray) and
supersedes this stub when it merges; these endpoints keep working
because they depend on the same function name.
"""

from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.errors import ApiError

_bearer = HTTPBearer(auto_error=False)

STAFF_ROLES = {"staff", "admin"}


def require_staff(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    if credentials is None:
        raise ApiError(401, "Not authenticated", "AUTH_REQUIRED")
    try:
        payload = jwt.decode(
            credentials.credentials,
            get_settings().secret_key,
            algorithms=["HS256"],
        )
    except JWTError:
        raise ApiError(401, "Invalid or expired token", "AUTH_INVALID")
    if payload.get("role") not in STAFF_ROLES:
        raise ApiError(403, "Staff role required", "FORBIDDEN")
    return payload
