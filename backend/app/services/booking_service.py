"""General-admission ticket booking (docs/decisions.md, "Booking and
membership", a proposed amendment to Flow 5).

Ticket types come from ticket_type. Its price is numeric(10,2); the API
sends integer cents (price_cents), so the front end never handles decimals.

ticket_type has no members-only column yet, so the Member ticket is found
by name (ticket_name is UNIQUE). It is offered only to a caller with an
active membership, up to the number of people that membership covers.
membership has no children_covered column (schema question 3), so the
plan's max_children stands in for the children the member registered.
Replace both stand-ins once the schema has the columns.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.booking import TicketTypeOut
from app.services.membership_service import MEMBERSHIP_PLANS, current_membership

# Compared case-insensitively with ticket_type.ticket_name.
MEMBER_TICKET_NAME = "member"

# Tickets of every type together in one booking; more is BOOKING_LIMIT_EXCEEDED.
MAX_TICKETS_PER_BOOKING = 10


def to_cents(price) -> int:
    """A numeric(10,2) price as integer cents, exactly. asyncpg returns a
    Decimal; going through str() also keeps a float such as 0.29 from
    turning into 28."""
    return int((Decimal(str(price)) * 100).to_integral_value(rounding=ROUND_HALF_UP))


async def _member_ticket_limit(db: AsyncSession, user_id: int) -> Optional[int]:
    """How many Member tickets the user may hold in one booking, or None
    without an active membership."""
    membership = await current_membership(db, user_id)
    if membership is None or membership.status != "active":
        return None
    plan = next((p for p in MEMBERSHIP_PLANS if p.id == membership.plan_id), None)
    if plan is None:
        return 1  # a membership type with no matching plan still covers its holder
    return plan.adults_covered + plan.max_children


async def list_ticket_types(
    db: AsyncSession, user_id: Optional[int], page: int, size: int
) -> tuple[list[TicketTypeOut], int]:
    """The ticket types this caller may buy, in table order."""
    member_limit = None
    if user_id is not None:
        member_limit = await _member_ticket_limit(db, user_id)
    rows = (
        await db.execute(
            text("SELECT tt.ticket_type_id, tt.ticket_name, tt.description, tt.price "
                 "FROM ticket_type tt ORDER BY tt.ticket_type_id")
        )
    ).all()

    items = []
    for row in rows:
        members_only = row.ticket_name.lower() == MEMBER_TICKET_NAME
        if members_only and member_limit is None:
            continue
        items.append(
            TicketTypeOut(
                id=row.ticket_type_id,
                name=row.ticket_name,
                description=row.description,
                price_cents=to_cents(row.price),
                members_only=members_only,
                max_quantity=member_limit if members_only else MAX_TICKETS_PER_BOOKING,
            )
        )
    start = (page - 1) * size
    return items[start : start + size], len(items)
