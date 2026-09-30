"""Authentication service for the login flow (Flow 1).

authenticate() loads the account by email, verifies the password, and
returns the public-facing UserOut. Email-not-found and wrong-password
both raise the same AUTH_INVALID error so the response can't be used to
probe which emails are registered. get_user_by_id() runs the same SELECT
by user_id for GET /api/auth/me (via app.api.deps.get_current_user).

The role is the account's highest-privilege role_name (admin > staff >
member > visitor, ranked by name rather than role_id), matching the rule
in app/api/admin/users.py. The contract's ACCOUNT_DISABLED (403) path is not
implemented here: user_account in 001_initial_schema.sql has no is_active
column yet, so there is nothing to disable against -- left out rather
than faked, as in the admin user listing.
"""

from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.core.security import verify_password
from app.schemas.user import UserOut


# Shared by authenticate() (by email) and get_user_by_id() (by id) so the
# login response and /api/auth/me always agree on the user and role.
_USER_SELECT = (
    "SELECT u.user_id, u.email, u.first_name, u.last_name, "
    " u.password_hash, "
    " (SELECT r.role_name FROM user_role ur "
    "   JOIN role r ON r.role_id = ur.role_id "
    "  WHERE ur.user_id = u.user_id "
    "  ORDER BY CASE lower(r.role_name) "
    "    WHEN 'admin' THEN 4 WHEN 'staff' THEN 3 "
    "    WHEN 'member' THEN 2 ELSE 1 END DESC "
    "  LIMIT 1) AS role_name "
    "FROM user_account u "
)


def _to_user(row) -> UserOut:
    # The role table stores capitalised names ("Admin"), but the API
    # contract and the require_staff/require_admin gates in app.api.deps
    # use lower case ("admin"), so normalise at the boundary.
    return UserOut(
        id=row.user_id,
        email=row.email,
        display_name=f"{row.first_name} {row.last_name}",
        role=(row.role_name or "member").lower(),
    )


async def authenticate(db: AsyncSession, email: str, password: str) -> UserOut:
    row = (
        await db.execute(
            text(_USER_SELECT + "WHERE u.email = :email"),
            {"email": email},
        )
    ).first()

    if row is None or not verify_password(password, row.password_hash):
        raise ApiError(401, "Incorrect email or password", "AUTH_INVALID")

    return _to_user(row)


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[UserOut]:
    """Load a user for an already-issued token; None if the account is gone."""
    row = (
        await db.execute(
            text(_USER_SELECT + "WHERE u.user_id = :user_id"),
            {"user_id": user_id},
        )
    ).first()
    return _to_user(row) if row is not None else None
