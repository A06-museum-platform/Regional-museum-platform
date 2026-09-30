"""Shared FastAPI dependencies.

require_staff / require_admin are role gates that verify the JWT
signature and the role claim only, without a database round trip.

get_current_user additionally loads the account from the database, so a
token for a deleted user is rejected. Every failure is a 401 -- the
front end clears its stored token only on 401, never on 404/500.
"""

from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.session import get_session
from app.schemas.user import UserOut
from app.services.auth_service import get_user_by_id

_bearer = HTTPBearer(auto_error=False)

STAFF_ROLES = {"staff", "admin"}


def _decode(credentials: Optional[HTTPAuthorizationCredentials]) -> dict:
    if credentials is None:
        raise ApiError(401, "Not authenticated", "AUTH_REQUIRED")
    try:
        return jwt.decode(
            credentials.credentials,
            get_settings().secret_key,
            algorithms=["HS256"],
        )
    except JWTError:
        raise ApiError(401, "Invalid or expired token", "AUTH_INVALID")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_session),
) -> UserOut:
    payload = _decode(credentials)
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise ApiError(401, "Invalid or expired token", "AUTH_INVALID")
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise ApiError(401, "Invalid or expired token", "AUTH_INVALID")
    return user


def require_staff(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    payload = _decode(credentials)
    if payload.get("role") not in STAFF_ROLES:
        raise ApiError(403, "Staff role required", "FORBIDDEN")
    return payload


def require_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> dict:
    payload = _decode(credentials)
    if payload.get("role") != "admin":
        raise ApiError(403, "Admin access required", "FORBIDDEN")
    return payload
