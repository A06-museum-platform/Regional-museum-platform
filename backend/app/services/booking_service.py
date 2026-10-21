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

Availability splits a day's opening hours into two-hour arrival windows,
laid end to end from opening time while a whole window fits before
closing, with 60 places each (a constant until schema question 2 is
settled). Places taken are the non-cancelled ticket_reservation quantities
whose visit_time falls inside a window. Dates are judged in museum-local
time, read from Postgres so the server's own time zone doesn't matter:
past dates and dates more than 60 days ahead are closed, and today offers
only windows that haven't started yet. opening_hours holds the weekly
pattern only; there are no date overrides (holidays) or notes yet.
"""

from datetime import date, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.booking import ArrivalWindowOut, AvailabilityOut, TicketTypeOut
from app.services.event_service import MUSEUM_TIMEZONE
from app.services.membership_service import MEMBERSHIP_PLANS, current_membership
from app.services.opening_hours_service import hours_on

# Compared case-insensitively with ticket_type.ticket_name.
MEMBER_TICKET_NAME = "member"

# Tickets of every type together in one booking; more is BOOKING_LIMIT_EXCEEDED.
MAX_TICKETS_PER_BOOKING = 10

WINDOW_MINUTES = 120
WINDOW_CAPACITY = 60
BOOKING_HORIZON_DAYS = 60


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


def _minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _closed(visit_date: date, note: str = "") -> AvailabilityOut:
    return AvailabilityOut(
        date=visit_date, is_closed=True, opens_at=None, closes_at=None, note=note, windows=[]
    )


async def get_availability(db: AsyncSession, visit_date: date) -> AvailabilityOut:
    clock = (
        await db.execute(
            text(f"SELECT (now() AT TIME ZONE '{MUSEUM_TIMEZONE}')::date AS today, "
                 f"(now() AT TIME ZONE '{MUSEUM_TIMEZONE}')::time AS now_time")
        )
    ).first()
    if visit_date < clock.today:
        return _closed(visit_date, "That date has passed.")
    if visit_date > clock.today + timedelta(days=BOOKING_HORIZON_DAYS):
        return _closed(visit_date, f"Bookings open {BOOKING_HORIZON_DAYS} days ahead.")

    hours = await hours_on(db, visit_date)
    if hours is None or hours.is_closed:
        return _closed(visit_date)

    opens, closes = _minutes(hours.open_time), _minutes(hours.close_time)
    starts = list(range(opens, closes - WINDOW_MINUTES + 1, WINDOW_MINUTES))
    is_today = visit_date == clock.today
    if is_today:
        # A window starting this minute has already begun.
        starts = [start for start in starts if start > _minutes(clock.now_time)]

    windows = []
    if starts:
        taken = (
            await db.execute(
                text("SELECT tr.visit_time, SUM(tr.ticket_quantity) AS taken "
                     "FROM ticket_reservation tr "
                     "WHERE tr.visit_date = :visit_date AND tr.status <> 'Cancelled' "
                     "GROUP BY tr.visit_time"),
                {"visit_date": visit_date},
            )
        ).all()
        for start in starts:
            end = start + WINDOW_MINUTES
            booked = sum(row.taken for row in taken if start <= _minutes(row.visit_time) < end)
            windows.append(
                ArrivalWindowOut(
                    start=_hhmm(start),
                    end=_hhmm(end),
                    places_left=max(0, WINDOW_CAPACITY - booked),
                )
            )

    return AvailabilityOut(
        date=visit_date,
        is_closed=not windows,
        opens_at=_hhmm(opens),
        closes_at=_hhmm(closes),
        note="Today's last arrival time has passed." if is_today and not windows else "",
        windows=windows,
    )
