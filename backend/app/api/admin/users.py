"""Admin user management (Flow 9, docs/api-contract.md section 9).

GET   /api/users?q=&role=staff,admin -> paginated {items, total, page, size}
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

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.errors import ApiError
from app.db.session import get_session
from app.schemas.user import AdminUserOut, UserListOut, UserUpdateIn
from app.services.auth_service import USER_SELECT, to_admin_user
from app.services.content_common import like_pattern

router = APIRouter(prefix="/api", tags=["admin-users"])


@router.get("/users", response_model=UserListOut)
async def list_users(
    q: Optional[str] = None,
    role: Optional[str] = Query(None, description="comma-separated, e.g. staff,admin"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(require_admin),
):
    """Every account, or those with one of the given roles (highest role
    counts) and/or whose name or email contains q."""
    clauses, params = [], {}
    if role:
        roles = [r.strip().lower() for r in role.split(",") if r.strip()]
        if not set(roles) <= {"visitor", "member", "staff", "admin"}:
            raise ApiError(422, "Unknown role filter", "VALIDATION_ERROR")
        clauses.append("lower(x.role_name) = ANY(:roles)")
        params["roles"] = roles
    if q and q.strip():
        clauses.append("((x.first_name || ' ' || x.last_name) ILIKE :q OR x.email ILIKE :q)")
        params["q"] = like_pattern(q)
    where = f"WHERE {' AND '.join(clauses)} " if clauses else ""
    base = f"FROM ({USER_SELECT}) x {where}"
    total = (await db.execute(text(f"SELECT COUNT(*) {base}"), params)).scalar_one()
    rows = (
        await db.execute(
            text(f"SELECT x.* {base}ORDER BY x.user_id LIMIT :limit OFFSET :offset"),
            {**params, "limit": size, "offset": (page - 1) * size},
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
        # Every account is at least a Visitor, and an active membership keeps
        # its Member role -- taking away a staff role mustn't take that too.
        await db.execute(
            text("INSERT INTO user_role (user_id, role_id) SELECT :user_id, role_id FROM role "
                 "WHERE lower(role_name) = 'visitor' ON CONFLICT DO NOTHING"),
            {"user_id": user_id},
        )
        if body.role in ("visitor", "member"):
            await db.execute(
                text("INSERT INTO user_role (user_id, role_id) SELECT :user_id, r.role_id FROM role r "
                     "WHERE lower(r.role_name) = 'member' AND EXISTS (SELECT 1 FROM membership m "
                     "WHERE m.user_id = :user_id AND m.status = 'Active') ON CONFLICT DO NOTHING"),
                {"user_id": user_id},
            )

    if body.is_active is not None:
        await db.execute(
            text("UPDATE user_account SET is_active = :is_active WHERE user_id = :user_id"),
            {"is_active": body.is_active, "user_id": user_id},
        )

    await db.commit()
    updated = to_admin_user(await _load(db, user_id))
    from app.services import activity_service
    if body.role is not None:
        await activity_service.record(db, admin, "role.changed", f"{updated.email} → {body.role}",
                                      subject_user_id=user_id)
    if body.is_active is not None:
        await activity_service.record(db, admin, "access.restored" if body.is_active else "access.disabled",
                                      updated.email, subject_user_id=user_id)
    return updated
