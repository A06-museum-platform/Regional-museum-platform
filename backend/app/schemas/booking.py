"""Pydantic schemas for general-admission ticket booking (docs/decisions.md,
"Booking and membership"). Money is always integer cents; times of day are
museum-local "HH:MM" strings."""

import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


class ArrivalWindowOut(BaseModel):
    start: str
    end: str
    places_left: int


class AvailabilityOut(BaseModel):
    """GET /api/bookings/availability for one date. A day with no window
    left to book reads is_closed, with the reason in note when there is one."""

    date: datetime.date
    is_closed: bool
    opens_at: Optional[str]
    closes_at: Optional[str]
    note: str
    windows: list[ArrivalWindowOut]


# The keys of ACCESSIBILITY_OPTIONS in frontend/src/api/constants.js.
AccessibilityNeed = Literal["step_free", "sensory_backpack", "hearing_loop"]


class ArrivalWindowIn(BaseModel):
    start: str
    # Not used: the window's end comes from the opening hours.
    end: Optional[str] = None


class BookingLineIn(BaseModel):
    ticket_type_id: int
    quantity: int = Field(ge=0)


class VisitorIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    # Optional; when given, the checkout form's rule (digits and spaces).
    mobile: str = Field(default="", max_length=30, pattern=r"^([+0-9][0-9 ]{7,})?$")


class BookingIn(BaseModel):
    """POST /api/bookings, as frontend/src/pages/booking/CheckoutPage.jsx sends it."""

    visit_date: datetime.date
    arrival_window: ArrivalWindowIn
    lines: list[BookingLineIn] = Field(max_length=20)
    visitor: VisitorIn
    accessibility: list[AccessibilityNeed] = Field(default_factory=list, max_length=3)
    payment_acknowledged: bool = False


class BookingLineOut(BaseModel):
    ticket_type_id: int
    name: str
    quantity: int
    unit_price_cents: int


class BookedWindowOut(BaseModel):
    start: str
    end: str


class VisitorOut(BaseModel):
    first_name: str
    last_name: str
    email: str
    mobile: str


class PaymentOut(BaseModel):
    method: str
    status: str


class BookingOut(BaseModel):
    """One booking, in the shape of the demo's mock bookings
    (frontend/src/api/mocks/tickets.js)."""

    id: int
    reference: str
    user_id: int
    visit_date: datetime.date
    arrival_window: BookedWindowOut
    lines: list[BookingLineOut]
    total_cents: int
    visitor: VisitorOut
    accessibility: list[str]
    # reserved | cancelled | completed
    status: str
    # True once staff have checked the visitors in at the front desk.
    checked_in: bool = False
    payment: PaymentOut
    created_at: datetime.datetime


class BookingListOut(BaseModel):
    items: list[BookingOut]
    total: int
    page: int
    size: int
