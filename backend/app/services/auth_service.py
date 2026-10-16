"""Authentication service for the login (Flow 1) and register flows.

authenticate() loads the account by email, verifies the password, and
returns the public-facing UserOut. Email-not-found and wrong-password
both raise the same AUTH_INVALID error so the response can't be used to
probe which emails are registered. A disabled account only gets
ACCOUNT_DISABLED (403) after the password matched, for the same reason.
get_user_by_id() runs the same SELECT by user_id for GET /api/auth/me and
the role gates (via app.api.deps); it treats a disabled account like a
deleted one, so an admin disabling an account takes effect immediately
rather than when the token expires.

register() creates an account with the Visitor role. Promoting it to
member/staff/admin is an admin action (PATCH /api/users/{id}).

The role is the account's highest-privilege role_name (admin > staff >
member > visitor, ranked by name rather than role_id). An account with no
role at all is treated as a visitor -- the least privilege.
"""

from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.core.security import hash_password, verify_password
from app.schemas.auth import RegisterIn
from app.schemas.user import AdminUserOut, UserOut

DEFAULT_ROLE = "visitor"

# Shared by authenticate() (by email), get_user_by_id() (by id) and the
# admin user endpoints so login, /api/auth/me and the admin screens always
# agree on the user and role.
USER_SELECT = (
    "SELECT u.user_id, u.email, u.first_name, u.last_name, "
    " u.password_hash, u.is_active, "
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
        role=(row.role_name or DEFAULT_ROLE).lower(),
    )


def to_admin_user(row) -> AdminUserOut:
    return AdminUserOut(**_to_user(row).model_dump(), is_active=row.is_active)


async def authenticate(db: AsyncSession, email: str, password: str) -> UserOut:
    row = (
        await db.execute(
            text(USER_SELECT + "WHERE lower(u.email) = lower(:email)"),
            {"email": email},
        )
    ).first()

    if row is None or not verify_password(password, row.password_hash):
        raise ApiError(401, "Incorrect email or password", "AUTH_INVALID")
    if not row.is_active:
        raise ApiError(
            403,
            "This account has been disabled. Contact the museum for help.",
            "ACCOUNT_DISABLED",
        )

    return _to_user(row)


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[UserOut]:
    """Load an active user for an already-issued token; None if the account
    is gone or disabled."""
    row = (
        await db.execute(
            text(USER_SELECT + "WHERE u.user_id = :user_id"),
            {"user_id": user_id},
        )
    ).first()
    if row is None or not row.is_active:
        return None
    return _to_user(row)


async def register(db: AsyncSession, body: RegisterIn) -> UserOut:
    email = body.email.lower()
    taken = (
        await db.execute(
            text("SELECT 1 FROM user_account WHERE lower(email) = :email"),
            {"email": email},
        )
    ).first()
    if taken is not None:
        raise ApiError(409, "An account with this email already exists", "CONFLICT")

    try:
        user_id = (
            await db.execute(
                text(
                    "INSERT INTO user_account "
                    "(email, password_hash, first_name, last_name, phone) "
                    "VALUES (:email, :password_hash, :first_name, :last_name, :phone) "
                    "RETURNING user_id"
                ),
                {
                    "email": email,
                    "password_hash": hash_password(body.password),
                    "first_name": body.first_name.strip(),
                    "last_name": body.last_name.strip(),
                    "phone": body.phone or None,
                },
            )
        ).scalar_one()
        await db.execute(
            text(
                "INSERT INTO user_role (user_id, role_id) "
                "SELECT :user_id, role_id FROM role WHERE lower(role_name) = :role"
            ),
            {"user_id": user_id, "role": DEFAULT_ROLE},
        )
        await db.commit()
    except IntegrityError:
        # Lost a race with a concurrent registration for the same email.
        await db.rollback()
        raise ApiError(409, "An account with this email already exists", "CONFLICT")

    return UserOut(
        id=user_id,
        email=email,
        display_name=f"{body.first_name.strip()} {body.last_name.strip()}",
        role=DEFAULT_ROLE,
    )
