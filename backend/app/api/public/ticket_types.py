"""Ticket types for general-admission booking (docs/decisions.md,
"Booking and membership").

GET /api/ticket-types?page=&size= -> { items, total, page, size, max_per_booking }

Public. A caller signed in with an active membership also gets the free
Member ticket, limited to the people their membership covers.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_user
from app.db.session import get_session
from app.schemas.booking import TicketTypeListOut
from app.schemas.user import UserOut
from app.services.booking_service import MAX_TICKETS_PER_BOOKING, list_ticket_types

router = APIRouter(prefix="/api", tags=["bookings"])


@router.get("/ticket-types", response_model=TicketTypeListOut)
async def get_ticket_types(
    page: int = Query(1, ge=1),
    size: int = Query(12, ge=1, le=100),
    user: Optional[UserOut] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_session),
):
    items, total = await list_ticket_types(db, user.id if user else None, page, size)
    return TicketTypeListOut(
        items=items,
        total=total,
        page=page,
        size=size,
        max_per_booking=MAX_TICKETS_PER_BOOKING,
    )
