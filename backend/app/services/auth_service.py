"""Authentication service for the login flow (Flow 1).

authenticate() loads the account by email, verifies the password, and
returns the public-facing UserOut. Email-not-found and wrong-password
both raise the same AUTH_INVALID error so the response can't be used to
probe which emails are registered.

The role is the account's lowest-role_id role_name, matching the rule in
app/api/admin/users.py. The contract's ACCOUNT_DISABLED (403) path is not
implemented here: user_account in 001_initial_schema.sql has no is_active
column yet, so there is nothing to disable against -- left out rather
than faked, as in the admin user listing.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.core.security import verify_password
from app.schemas.user import UserOut


async def authenticate(db: AsyncSession, email: str, password: str) -> UserOut:
    row = (
        await db.execute(
            text(
                "SELECT u.user_id, u.email, u.first_name, u.last_name, "
                " u.password_hash, "
                " (SELECT r.role_name FROM user_role ur "
                "   JOIN role r ON r.role_id = ur.role_id "
                "  WHERE ur.user_id = u.user_id "
                "  ORDER BY r.role_id LIMIT 1) AS role_name "
                "FROM user_account u "
                "WHERE u.email = :email"
            ),
            {"email": email},
        )
    ).first()

    if row is None or not verify_password(password, row.password_hash):
        raise ApiError(401, "Incorrect email or password", "AUTH_INVALID")

    # The role table stores capitalised names ("Admin"), but the API
    # contract and the require_staff/require_admin gates in app.api.deps
    # use lower case ("admin"), so normalise at the boundary.
    return UserOut(
        id=row.user_id,
        email=row.email,
        display_name=f"{row.first_name} {row.last_name}",
        role=(row.role_name or "member").lower(),
    )
