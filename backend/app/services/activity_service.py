"""Activity log (migration 010): written by the backend as a side effect of
the action, read by administrators (all entries) and members (their own).

record() never raises: a failed log write must not undo or fail the action
the visitor or staff member just completed.
"""

import logging
from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.content_common import like_pattern

log = logging.getLogger("museum.activity")


class ActivityOut(BaseModel):
    id: int
    created_at: datetime
    actor_name: str
    actor_role: str
    action: str
    target: str
    reason: Optional[str]
    reference: Optional[str]


class ActivityListOut(BaseModel):
    items: list[ActivityOut]
    total: int
    page: int
    size: int


def _actor_id_role(actor) -> tuple[Optional[int], str]:
    """actor is require_staff/require_admin's {sub, role} dict or a UserOut."""
    if actor is None:
        return None, "anonymous"
    if isinstance(actor, dict):
        return int(actor["sub"]), actor.get("role", "visitor")
    return actor.id, actor.role


async def record(
    db: AsyncSession,
    actor: Union[dict, BaseModel, None],
    action: str,
    target: str = "",
    *,
    reason: Optional[str] = None,
    reference: Optional[str] = None,
    subject_user_id: Optional[int] = None,
) -> None:
    user_id, role = _actor_id_role(actor)
    try:
        name = "System"
        if user_id is not None:
            name = (
                await db.execute(
                    text("SELECT first_name || ' ' || last_name FROM user_account WHERE user_id = :id"),
                    {"id": user_id},
                )
            ).scalar_one_or_none() or f"User #{user_id}"
        await db.execute(
            text("INSERT INTO activity_log (actor_user_id, actor_name, actor_role, action, target, "
                 "reason, reference, subject_user_id) VALUES (:uid, :name, :role, :action, :target, "
                 ":reason, :reference, :subject)"),
            {"uid": user_id, "name": name, "role": role, "action": action, "target": target[:300],
             "reason": reason, "reference": reference,
             "subject": subject_user_id if subject_user_id is not None else user_id},
        )
        await db.commit()
    except Exception:  # pragma: no cover - logged, never surfaced
        await db.rollback()
        log.exception("Could not write activity log entry %s", action)


async def list_activity(
    db: AsyncSession,
    *,
    q: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    page: int = 1,
    size: int = 50,
) -> tuple[list[ActivityOut], int]:
    """Newest first. user_id limits to entries the user did or that were about
    them (a member's own activity)."""
    clauses, params = [], {}
    if q and q.strip():
        clauses.append("(actor_name ILIKE :q OR target ILIKE :q OR coalesce(reason, '') ILIKE :q "
                       "OR coalesce(reference, '') ILIKE :q)")
        params["q"] = like_pattern(q)
    if action:
        clauses.append("action = :action")
        params["action"] = action
    if user_id is not None:
        clauses.append("(actor_user_id = :uid OR subject_user_id = :uid)")
        params["uid"] = user_id
    where = f"WHERE {' AND '.join(clauses)} " if clauses else ""
    total = (await db.execute(text(f"SELECT COUNT(*) FROM activity_log {where}"), params)).scalar_one()
    rows = (
        await db.execute(
            text("SELECT activity_id, created_at, actor_name, actor_role, action, target, reason, "
                 f"reference FROM activity_log {where}"
                 "ORDER BY created_at DESC, activity_id DESC LIMIT :limit OFFSET :offset"),
            {**params, "limit": size, "offset": (page - 1) * size},
        )
    ).all()
    return [
        ActivityOut(id=r.activity_id, created_at=r.created_at, actor_name=r.actor_name,
                    actor_role=r.actor_role, action=r.action, target=r.target, reason=r.reason,
                    reference=r.reference)
        for r in rows
    ], total
