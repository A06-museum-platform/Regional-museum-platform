"""General-admission ticket booking (docs/decisions.md, "Booking and
membership", a proposed amendment to Flow 5). The rules follow the demo's
mock API in frontend/src/api/bookings.js, check for check and message for
message.

Ticket types come from ticket_type. Its price is numeric(10,2); the API
sends integer cents (price_cents), so the front end never handles decimals.

ticket_type has no members-only column yet, so the Member ticket is found
by name (ticket_name is UNIQUE). It is offered only to a caller with an
active membership, up to the number of people that membership covers.
The limit is the plan's adults plus the membership's children_covered.

Availability splits a day's opening hours into two-hour arrival windows,
laid end to end from opening time while a whole window fits before
closing, with 60 places each (a constant until schema question 2 is
settled). Places taken are the non-cancelled ticket_reservation quantities
whose visit_time falls inside a window. Dates are judged in museum-local
time, read from Postgres so the server's own time zone doesn't matter:
past dates and dates more than 60 days ahead are closed, and today offers
only windows that haven't started yet. A dated exception in
opening_hours_override (a holiday) wins over the weekly pattern.

Creating a booking checks, in the demo's order: the simulated payment was
acknowledged; there are 1-10 tickets; each ticket type exists and Member
tickets fit an active membership; the arrival window is on offer; it has
room. The room check and the insert run under a lock on that date and
window, so two bookings can't both take the last places. A booking row
(migration 008) holds the reference, window, visitor and accessibility
needs, with one ticket_reservation row per ticket type under it, which is
what availability counts.

Reading a booking back gives the same shape. Nothing marks a visit as done,
so a reserved booking whose date has passed (museum-local) reads as
completed, like the demo's past bookings.
"""

import re
import secrets
from datetime import date, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from types import SimpleNamespace
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.schemas.booking import (
    ArrivalWindowOut,
    AvailabilityOut,
    BookedWindowOut,
    BookingIn,
    BookingLineOut,
    BookingOut,
    PaymentOut,
    TicketTypeOut,
    VisitorOut,
)
from app.services.event_service import MUSEUM_TIMEZONE
from app.services.membership_service import current_membership
from app.services.opening_hours_service import hours_on

# Compared case-insensitively with ticket_type.ticket_name.
MEMBER_TICKET_NAME = "member"

# Tickets of every type together in one booking; more is BOOKING_LIMIT_EXCEEDED.
MAX_TICKETS_PER_BOOKING = 10

WINDOW_MINUTES = 120
WINDOW_CAPACITY = 60
BOOKING_HORIZON_DAYS = 60

REFERENCE_PREFIX = "SARHN-"

# Payment is simulated: every booking reads as paid and nothing is stored.
SIMULATED_PAYMENT = PaymentOut(method="simulated", status="simulated_paid")

_NOT_ON_OFFER = "That arrival time is not available on this date."

_HHMM = re.compile(r"([01][0-9]|2[0-3]):([0-5][0-9])")

_BOOKING_COLUMNS = (
    "booking_id, booking_reference, user_id, visit_date, window_start, window_end, "
    "visitor_first_name, visitor_last_name, visitor_email, visitor_mobile, "
    "accessibility, status, created_at"
)


def to_cents(price) -> int:
    """A numeric(10,2) price as integer cents, exactly. asyncpg returns a
    Decimal; going through str() also keeps a float such as 0.29 from
    turning into 28."""
    return int((Decimal(str(price)) * 100).to_integral_value(rounding=ROUND_HALF_UP))


async def _ticket_type_rows(db: AsyncSession):
    return (
        await db.execute(
            text("SELECT tt.ticket_type_id, tt.ticket_name, tt.description, tt.price "
                 "FROM ticket_type tt ORDER BY tt.ticket_type_id")
        )
    ).all()


def _is_member_ticket(row) -> bool:
    return row.ticket_name.lower() == MEMBER_TICKET_NAME


async def _member_ticket_limit(db: AsyncSession, user_id: int) -> Optional[int]:
    """How many Member tickets the user may hold in one booking -- everyone
    the membership covers -- or None without an active membership."""
    membership = await current_membership(db, user_id)
    if membership is None or membership.status != "active":
        return None
    adults = membership.adults_covered or 1
    return adults + (membership.children_covered or 0)


async def list_ticket_types(
    db: AsyncSession, user_id: Optional[int], page: int, size: int
) -> tuple[list[TicketTypeOut], int]:
    """The ticket types this caller may buy, in table order."""
    member_limit = None
    if user_id is not None:
        member_limit = await _member_ticket_limit(db, user_id)

    items = []
    for row in await _ticket_type_rows(db):
        members_only = _is_member_ticket(row)
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


async def _museum_clock(db: AsyncSession):
    """Today's date and the time now (today, now_time), in the museum's time
    zone, whatever zone the server runs in."""
    return (
        await db.execute(
            text(f"SELECT (now() AT TIME ZONE '{MUSEUM_TIMEZONE}')::date AS today, "
                 f"(now() AT TIME ZONE '{MUSEUM_TIMEZONE}')::time AS now_time")
        )
    ).first()


async def get_availability(db: AsyncSession, visit_date: date) -> AvailabilityOut:
    clock = await _museum_clock(db)
    if visit_date < clock.today:
        return _closed(visit_date, "That date has passed.")
    if visit_date > clock.today + timedelta(days=BOOKING_HORIZON_DAYS):
        return _closed(visit_date, f"Bookings open {BOOKING_HORIZON_DAYS} days ahead.")

    hours = await hours_on(db, visit_date)
    if hours is None or hours.is_closed:
        return _closed(visit_date, getattr(hours, "note", "") or "")

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


def _to_booking(row, lines, today: Optional[date] = None) -> BookingOut:
    """A booking row (_BOOKING_COLUMNS) and its ticket lines (ticket_type_id,
    ticket_name, ticket_quantity, unit_price) in the demo's booking shape.
    Given today's date, a reservation for an earlier day reads completed."""
    status = row.status.lower()
    if status == "reserved" and today is not None and row.visit_date < today:
        status = "completed"
    out_lines = [
        BookingLineOut(
            ticket_type_id=line.ticket_type_id,
            name=line.ticket_name,
            quantity=line.ticket_quantity,
            unit_price_cents=to_cents(line.unit_price),
        )
        for line in lines
    ]
    return BookingOut(
        id=row.booking_id,
        reference=row.booking_reference,
        user_id=row.user_id,
        visit_date=row.visit_date,
        arrival_window=BookedWindowOut(
            start=_hhmm(_minutes(row.window_start)), end=_hhmm(_minutes(row.window_end))
        ),
        lines=out_lines,
        total_cents=sum(line.quantity * line.unit_price_cents for line in out_lines),
        visitor=VisitorOut(
            first_name=row.visitor_first_name,
            last_name=row.visitor_last_name,
            email=row.visitor_email,
            mobile=row.visitor_mobile or "",
        ),
        accessibility=list(row.accessibility),
        status=status,
        checked_in=row.status == "Completed",
        payment=SIMULATED_PAYMENT,
        created_at=row.created_at,
    )


async def get_booking(db: AsyncSession, reference: str, user_id: int, sees_all: bool) -> BookingOut:
    """One booking by its reference, for its owner, or anyone when sees_all
    (staff and admins). Someone else's booking is reported as missing, not
    forbidden: a 403 would confirm that the reference exists."""
    row = (
        await db.execute(
            text(f"SELECT {_BOOKING_COLUMNS} FROM booking WHERE booking_reference = :reference"),
            {"reference": reference.strip().upper()},
        )
    ).first()
    if row is None or (row.user_id != user_id and not sees_all):
        raise ApiError(404, "We could not find that booking.", "NOT_FOUND")
    lines = (await _lines_for(db, [row.booking_id])).get(row.booking_id, [])
    clock = await _museum_clock(db)
    return _to_booking(row, lines, today=clock.today)


async def _lines_for(db: AsyncSession, booking_ids: list[int]) -> dict[int, list]:
    """Ticket lines for several bookings in one query, keyed by booking_id."""
    if not booking_ids:
        return {}
    rows = (
        await db.execute(
            text("SELECT tr.booking_id, tr.ticket_type_id, tt.ticket_name, tr.ticket_quantity, "
                 "COALESCE(tr.unit_price, tt.price) AS unit_price "
                 "FROM ticket_reservation tr "
                 "JOIN ticket_type tt ON tt.ticket_type_id = tr.ticket_type_id "
                 "WHERE tr.booking_id = ANY(:ids) ORDER BY tr.reservation_id"),
            {"ids": booking_ids},
        )
    ).all()
    grouped: dict[int, list] = {}
    for line in rows:
        grouped.setdefault(line.booking_id, []).append(line)
    return grouped


async def list_bookings(
    db: AsyncSession,
    *,
    user_id: Optional[int],
    page: int,
    size: int,
    visit_date: Optional[date] = None,
    q: Optional[str] = None,
) -> tuple[list[BookingOut], int]:
    """Bookings newest visit first. user_id limits them to one account (the
    member's own list); None lists every account's (staff). visit_date and q
    (reference, visitor name or email) narrow the staff list."""
    clauses, params = [], {}
    if user_id is not None:
        clauses.append("user_id = :user_id")
        params["user_id"] = user_id
    if visit_date is not None:
        clauses.append("visit_date = :visit_date")
        params["visit_date"] = visit_date
    if q and q.strip():
        needle = re.sub(r"([\\%_])", r"\\\1", q.strip())
        clauses.append("(booking_reference ILIKE :q OR visitor_email ILIKE :q "
                       "OR (visitor_first_name || ' ' || visitor_last_name) ILIKE :q)")
        params["q"] = f"%{needle}%"
    where = f"WHERE {' AND '.join(clauses)} " if clauses else ""

    total = (await db.execute(text(f"SELECT COUNT(*) FROM booking {where}"), params)).scalar_one()
    rows = (
        await db.execute(
            text(f"SELECT {_BOOKING_COLUMNS} FROM booking {where}"
                 "ORDER BY visit_date DESC, window_start DESC, booking_id DESC "
                 "LIMIT :limit OFFSET :offset"),
            {**params, "limit": size, "offset": (page - 1) * size},
        )
    ).all()
    lines = await _lines_for(db, [row.booking_id for row in rows])
    clock = await _museum_clock(db)
    return [_to_booking(row, lines.get(row.booking_id, []), today=clock.today) for row in rows], total


async def cancel_booking(db: AsyncSession, reference: str, user_id: int, sees_all: bool) -> BookingOut:
    """Cancel an upcoming booking. Only a reserved booking whose visit date
    hasn't passed can be cancelled; its places go back on offer because
    availability skips cancelled reservations."""
    booking = await get_booking(db, reference, user_id, sees_all)
    if booking.status != "reserved":
        raise ApiError(409, "Only an upcoming booking can be cancelled.", "CONFLICT")
    await db.execute(
        text("UPDATE booking SET status = 'Cancelled' WHERE booking_id = :id"), {"id": booking.id}
    )
    await db.execute(
        text("UPDATE ticket_reservation SET status = 'Cancelled' WHERE booking_id = :id"),
        {"id": booking.id},
    )
    await db.commit()
    return booking.model_copy(update={"status": "cancelled"})


async def _insert_booking(db: AsyncSession, user_id: int, body: BookingIn, start: int):
    """Insert the booking row under a fresh random reference and return it.
    A reference already in use is skipped and another one drawn."""
    visitor = body.visitor
    params = {
        "user_id": user_id,
        "visit_date": body.visit_date,
        "window_start": time(start // 60, start % 60),
        "window_end": time((start + WINDOW_MINUTES) // 60, (start + WINDOW_MINUTES) % 60),
        "first_name": visitor.first_name,
        "last_name": visitor.last_name,
        "email": visitor.email,
        "mobile": visitor.mobile or None,
        "accessibility": list(dict.fromkeys(body.accessibility)),
    }
    for _ in range(10):
        reference = f"{REFERENCE_PREFIX}{10000 + secrets.randbelow(90000)}"
        row = (
            await db.execute(
                text("INSERT INTO booking (booking_reference, user_id, visit_date, "
                     "window_start, window_end, visitor_first_name, visitor_last_name, "
                     "visitor_email, visitor_mobile, accessibility) "
                     "VALUES (:reference, :user_id, :visit_date, :window_start, :window_end, "
                     ":first_name, :last_name, :email, :mobile, :accessibility) "
                     f"ON CONFLICT (booking_reference) DO NOTHING RETURNING {_BOOKING_COLUMNS}"),
                {"reference": reference, **params},
            )
        ).first()
        if row is not None:
            return row
    raise ApiError(500, "Could not create a booking reference. Please try again.", "INTERNAL_ERROR")


async def create_booking(db: AsyncSession, user_id: int, body: BookingIn) -> BookingOut:
    if not body.payment_acknowledged:
        raise ApiError(400, "Confirm that you understand no payment will be taken.",
                       "VALIDATION_ERROR")

    # One line per ticket type, so splitting a type over two lines can't get
    # round its limit.
    quantities: dict[int, int] = {}
    for line in body.lines:
        if line.quantity > 0:
            quantities[line.ticket_type_id] = quantities.get(line.ticket_type_id, 0) + line.quantity
    count = sum(quantities.values())
    if count == 0:
        raise ApiError(400, "Choose at least one ticket.", "VALIDATION_ERROR")
    if count > MAX_TICKETS_PER_BOOKING:
        raise ApiError(
            409,
            f"One booking can hold up to {MAX_TICKETS_PER_BOOKING} tickets. "
            "Make a second booking for the rest of your group.",
            "BOOKING_LIMIT_EXCEEDED",
        )

    types = {row.ticket_type_id: row for row in await _ticket_type_rows(db)}
    lines = []
    for type_id, quantity in quantities.items():
        row = types.get(type_id)
        if row is None:
            raise ApiError(400, "That ticket type does not exist.", "VALIDATION_ERROR")
        if _is_member_ticket(row):
            limit = await _member_ticket_limit(db, user_id)
            if limit is None:
                raise ApiError(403, "Member tickets need an active membership on this account.",
                               "FORBIDDEN")
            if quantity > limit:
                noun = "ticket" if limit == 1 else "tickets"
                raise ApiError(400, f"Your membership covers {limit} {row.ticket_name} {noun} "
                               "per visit.", "VALIDATION_ERROR")
        lines.append(SimpleNamespace(ticket_type_id=type_id, ticket_name=row.ticket_name,
                                     ticket_quantity=quantity, unit_price=row.price))

    match = _HHMM.fullmatch(body.arrival_window.start)
    if match is None:
        raise ApiError(400, _NOT_ON_OFFER, "VALIDATION_ERROR")
    start = int(match[1]) * 60 + int(match[2])

    # Bookings for the same date and window wait here until this transaction
    # ends, so the room check below sees every booking made before it.
    await db.execute(text("SELECT pg_advisory_xact_lock(:day, :minute)"),
                     {"day": body.visit_date.toordinal(), "minute": start})
    try:
        availability = await get_availability(db, body.visit_date)
        window = next((w for w in availability.windows if w.start == _hhmm(start)), None)
        if window is None:
            raise ApiError(400, _NOT_ON_OFFER, "VALIDATION_ERROR")
        if window.places_left < count:
            raise ApiError(
                400,
                f"Only {window.places_left} places are left in that arrival window. "
                "Choose another time or fewer tickets.",
                "INSUFFICIENT_TICKETS",
            )

        booking = await _insert_booking(db, user_id, body, start)
        for line in lines:
            await db.execute(
                text("INSERT INTO ticket_reservation (booking_id, user_id, ticket_type_id, "
                     "visit_date, visit_time, ticket_quantity, unit_price, status) "
                     "VALUES (:booking_id, :user_id, :ticket_type_id, :visit_date, "
                     ":visit_time, :quantity, :unit_price, 'Reserved')"),
                {
                    "booking_id": booking.booking_id,
                    "user_id": user_id,
                    "ticket_type_id": line.ticket_type_id,
                    "visit_date": body.visit_date,
                    "visit_time": booking.window_start,
                    "quantity": line.ticket_quantity,
                    "unit_price": line.unit_price,
                },
            )
        await db.commit()
    except ApiError:
        await db.rollback()
        raise
    return _to_booking(booking, lines)

async def check_in(db: AsyncSession, reference: str) -> BookingOut:
    """Staff mark a reserved booking as arrived (status Completed). Only a
    booking for today or earlier can be checked in, and only once."""
    booking = await get_booking(db, reference, user_id=0, sees_all=True)
    clock = await _museum_clock(db)
    if booking.status == "cancelled":
        raise ApiError(409, "That booking was cancelled.", "CONFLICT")
    raw = (await db.execute(text("SELECT status FROM booking WHERE booking_id = :id"),
                            {"id": booking.id})).scalar_one()
    if raw == "Completed":
        raise ApiError(409, "Already checked in.", "ALREADY_CHECKED_IN")
    if booking.visit_date > clock.today:
        raise ApiError(409, f"This booking is for {booking.visit_date:%A %d %B}, not today.",
                       "NOT_TODAY")
    await db.execute(text("UPDATE booking SET status = 'Completed' WHERE booking_id = :id"),
                     {"id": booking.id})
    await db.execute(text("UPDATE ticket_reservation SET status = 'Completed' WHERE booking_id = :id"),
                     {"id": booking.id})
    await db.commit()
    return await get_booking(db, reference, user_id=0, sees_all=True)


async def day_summary(db: AsyncSession, visit_date: date) -> dict:
    """Bookings, tickets and check-ins for one date, overall and per window."""
    rows = (
        await db.execute(
            text("SELECT b.window_start, b.status, COUNT(DISTINCT b.booking_id) AS bookings, "
                 "COALESCE(SUM(tr.ticket_quantity), 0) AS tickets "
                 "FROM booking b LEFT JOIN ticket_reservation tr ON tr.booking_id = b.booking_id "
                 "WHERE b.visit_date = :d AND b.status <> 'Cancelled' "
                 "GROUP BY b.window_start, b.status ORDER BY b.window_start"),
            {"d": visit_date},
        )
    ).all()
    windows: dict[str, dict] = {}
    for r in rows:
        key = _hhmm(_minutes(r.window_start))
        w = windows.setdefault(key, {"start": key, "bookings": 0, "tickets": 0, "checked_in": 0})
        w["bookings"] += r.bookings
        w["tickets"] += int(r.tickets)
        if r.status == "Completed":
            w["checked_in"] += r.bookings
    return {
        "date": visit_date,
        "bookings": sum(w["bookings"] for w in windows.values()),
        "tickets": sum(w["tickets"] for w in windows.values()),
        "checked_in": sum(w["checked_in"] for w in windows.values()),
        "windows": list(windows.values()),
    }
