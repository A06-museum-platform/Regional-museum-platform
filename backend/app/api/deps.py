"""Shared FastAPI dependencies.

get_current_user verifies the JWT and loads the account from the
database, so a token for a deleted or disabled user is rejected. Every
failure is a 401 -- the front end clears its stored token only on 401,
never on 404/500.

require_staff / require_admin build on it and check the role from the
database rather than the token's role claim, so an admin changing a
role or disabling an account takes effect on the next request instead
of when the token expires. They return {sub, role} like a token payload.

get_optional_user is for public endpoints that show a signed-in caller
more (GET /api/ticket-types): a token get_current_user would reject
counts as an anonymous caller there, never a 401.
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


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_session),
) -> Optional[UserOut]:
    """The signed-in user, or None for no token or a rejected one."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except ApiError:
        return None


async def require_staff(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user = await get_current_user(credentials, db)
    if user.role not in STAFF_ROLES:
        raise ApiError(403, "Staff role required", "FORBIDDEN")
    return {"sub": str(user.id), "role": user.role}


async def require_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_session),
) -> dict:
    user = await get_current_user(credentials, db)
    if user.role != "admin":
        raise ApiError(403, "Admin access required", "FORBIDDEN")
    return {"sub": str(user.id), "role": user.role}
