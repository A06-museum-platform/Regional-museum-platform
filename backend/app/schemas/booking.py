"""Pydantic schemas for general-admission ticket booking (docs/decisions.md,
"Booking and membership"). Money is always integer cents."""

from typing import Optional

from pydantic import BaseModel


class TicketTypeOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price_cents: int
    # True for the Member ticket: free, and only for an active membership.
    members_only: bool
    # Most tickets of this type one booking may hold: the people the
    # membership covers for the Member ticket, otherwise the booking limit.
    max_quantity: int


class TicketTypeListOut(BaseModel):
    """GET /api/ticket-types: the contract's list shape plus the booking
    limit frontend/src/pages/booking/TicketBookingPage.jsx reads."""

    items: list[TicketTypeOut]
    total: int
    page: int
    size: int
    # Tickets of every type together in one booking; more is
    # BOOKING_LIMIT_EXCEEDED.
    max_per_booking: int
