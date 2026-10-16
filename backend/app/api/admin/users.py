"""Admin user management (Flow 9, docs/api-contract.md section 9).

GET   /api/users       -> paginated {items, total, page, size}
PATCH /api/users/{id}  -> body any subset of {role, is_active}; returns
                          the updated user

Each user's role is taken from user_role/role via
app.services.auth_service.USER_SELECT (highest-privilege role, lower
case), so this screen agrees with what login returns. Changing the role
replaces all of the user's role rows with the single new one. is_active
comes from 007_user_account_is_active.sql; a disabled account can't log
in and its existing tokens stop working on the next request. The
contract's access_status is not stored separately -- it would only
restate is_active -- so it's left out.

An admin can't change their own role or disable themselves: one careless
click would otherwise leave the museum with no administrator.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.errors import ApiError
from app.db.session import get_session
from app.schemas.user import AdminUserOut, UserListOut, UserUpdateIn
from app.services.auth_service import USER_SELECT, to_admin_user

router = APIRouter(prefix="/api", tags=["admin-users"])


@router.get("/users", response_model=UserListOut)
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(require_admin),
):
    offset = (page - 1) * size
    total = (await db.execute(text("SELECT COUNT(*) FROM user_account"))).scalar_one()
    rows = (
        await db.execute(
            text(USER_SELECT + "ORDER BY u.user_id LIMIT :limit OFFSET :offset"),
            {"limit": size, "offset": offset},
        )
    ).all()
    return UserListOut(
        items=[to_admin_user(row) for row in rows], total=total, page=page, size=size
    )


async def _load(db: AsyncSession, user_id: int):
    return (
        await db.execute(text(USER_SELECT + "WHERE u.user_id = :user_id"), {"user_id": user_id})
    ).first()


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: int,
    body: UserUpdateIn,
    db: AsyncSession = Depends(get_session),
    admin: dict = Depends(require_admin),
):
    if user_id == int(admin["sub"]) and (body.role is not None or body.is_active is not None):
        raise ApiError(409, "You cannot change your own role or access", "CANNOT_MODIFY_SELF")

    if await _load(db, user_id) is None:
        raise ApiError(404, "User not found", "USER_NOT_FOUND")

    if body.role is not None:
        role_id = (
            await db.execute(
                text("SELECT role_id FROM role WHERE lower(role_name) = :role"),
                {"role": body.role},
            )
        ).scalar_one_or_none()
        if role_id is None:
            raise ApiError(422, "Invalid input data", "VALIDATION_ERROR")
        await db.execute(text("DELETE FROM user_role WHERE user_id = :user_id"), {"user_id": user_id})
        await db.execute(
            text("INSERT INTO user_role (user_id, role_id) VALUES (:user_id, :role_id)"),
            {"user_id": user_id, "role_id": role_id},
        )

    if body.is_active is not None:
        await db.execute(
            text("UPDATE user_account SET is_active = :is_active WHERE user_id = :user_id"),
            {"is_active": body.is_active, "user_id": user_id},
        )

    await db.commit()
    return to_admin_user(await _load(db, user_id))
