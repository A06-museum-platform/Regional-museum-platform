"""Admin user listing (Flow 9, docs/api-contract.md section 9).

GET /api/users -> paginated {items, total, page, size}

Each user's role is taken from user_role/role (a user can hold more
than one role; this picks the lowest role_id, i.e. the first one
assigned). is_active / access_status from the contract aren't in
database/migrations/001_initial_schema.sql yet -- user_account has no
such column -- so they're left out here rather than faked.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_session
from app.schemas.user import UserListOut, UserOut

router = APIRouter(prefix="/api", tags=["admin-users"])


@router.get("/users", response_model=UserListOut)
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    _admin: dict = Depends(require_admin),
):
    offset = (page - 1) * size
    rows = (
        await db.execute(
            text(
                "SELECT u.user_id, u.email, u.first_name, u.last_name, "
                " (SELECT r.role_name FROM user_role ur "
                "   JOIN role r ON r.role_id = ur.role_id "
                "  WHERE ur.user_id = u.user_id "
                "  ORDER BY r.role_id LIMIT 1) AS role_name, "
                " COUNT(*) OVER() AS total_count "
                "FROM user_account u "
                "ORDER BY u.user_id "
                "LIMIT :limit OFFSET :offset"
            ),
            {"limit": size, "offset": offset},
        )
    ).all()

    total = rows[0].total_count if rows else 0
    items = [
        UserOut(
            id=row.user_id,
            email=row.email,
            display_name=f"{row.first_name} {row.last_name}",
            role=row.role_name or "member",
        )
        for row in rows
    ]
    return UserListOut(items=items, total=total, page=page, size=size)
