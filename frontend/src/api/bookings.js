import { request, USE_MOCKS, delay, ApiError } from './client';
import {
  TICKET_TYPES,
  WINDOW_CAPACITY,
  WINDOW_HOURS,
  MAX_TICKETS_PER_BOOKING,
  SEED_BOOKINGS,
} from './mocks/tickets';
import { WEEKLY, OVERRIDES } from './mocks/openingHours';
import { loadArray, saveArray } from './mocks/persist';
import { activeMembershipFor } from './memberships';
import { recordLocally } from './activity';
import { fromIsoDate, isoDateFromToday } from '../utils/date';

/**
 * General-admission ticket booking with a simulated payment step.
 *
 * The frozen contract only has POST /events/{id}/bookings (Flow 5), which is
 * per event. The client's "book tickets" requirement and Molly's
 * `ticket_type` / `ticket_reservation` tables are about entry to the museum on
 * a date, so this module follows the tables. Proposed amendment — see
 * docs/decisions.md, "Booking and membership":
 *
 *   GET  /ticket-types                        public
 *   GET  /bookings/availability?date=         public — arrival windows + places left
 *   POST /bookings                            member — creates reservation, simulated payment
 *   GET  /bookings/me                         member — the caller's bookings
 *   GET  /bookings/{reference}                member — own booking only (staff: any)
 *   POST /bookings/{reference}/cancel         member — own booking only
 *
 * Error codes reuse Flow 5's: INSUFFICIENT_TICKETS (400) and
 * BOOKING_LIMIT_EXCEEDED (409).
 */

const STORE_KEY = 'bookings';
const BOOKINGS = loadArray(STORE_KEY, SEED_BOOKINGS.map((row) => ({ ...row })));
const persist = () => saveArray(STORE_KEY, BOOKINGS);

/** How far ahead a visit can be booked. */
export const BOOKING_HORIZON_DAYS = 60;

/* ---------------------------------------------------------------- helpers */

const toMinutes = (hhmm) => {
  const [h, m] = hhmm.split(':').map(Number);
  return h * 60 + m;
};

const toHhmm = (minutes) =>
  `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;

/** Opening hours for one calendar date: an override wins over the weekly row. */
function hoursFor(isoDate) {
  const override = OVERRIDES.find((row) => row.specific_date === isoDate);
  if (override) return override;
  const weekday = fromIsoDate(isoDate).getDay();
  return WEEKLY.find((row) => row.day_of_week === weekday) || null;
}

/** Two-hour arrival windows that fit inside the day's opening hours. */
function windowsFor(hours) {
  if (!hours || hours.is_closed || !hours.opens_at || !hours.closes_at) return [];
  const windows = [];
  const close = toMinutes(hours.closes_at);
  for (let start = toMinutes(hours.opens_at); start + WINDOW_HOURS * 60 <= close; start += WINDOW_HOURS * 60) {
    windows.push({ start: toHhmm(start), end: toHhmm(start + WINDOW_HOURS * 60) });
  }
  return windows;
}

/**
 * Mock-only stand-in for walk-up and other visitors' bookings, so the
 * "places left" figure varies between windows instead of always reading 60.
 * Deterministic per date and window so it does not jump on every request.
 */
function backgroundDemand(isoDate, start) {
  let hash = 0;
  for (const char of `${isoDate}|${start}`) hash = (hash * 31 + char.charCodeAt(0)) % 9973;
  return hash % 45;
}

function placesTaken(isoDate, start) {
  const booked = BOOKINGS.filter(
    (booking) =>
      booking.visit_date === isoDate &&
      booking.arrival_window.start === start &&
      booking.status !== 'cancelled'
  ).reduce((sum, booking) => sum + booking.lines.reduce((n, line) => n + line.quantity, 0), 0);
  return booked + backgroundDemand(isoDate, start);
}

const ticketCount = (lines) => lines.reduce((sum, line) => sum + line.quantity, 0);

function newReference() {
  let reference;
  do {
    reference = `SARHN-${Math.floor(10000 + Math.random() * 90000)}`;
  } while (BOOKINGS.some((booking) => booking.reference === reference));
  return reference;
}

function notFound() {
  return new ApiError({ status: 404, code: 'NOT_FOUND', message: 'We could not find that booking.' });
}

/** Staff may look at any booking; a member only at their own. */
function canSee(booking, user) {
  return booking.user_id === user.id || user.role === 'staff' || user.role === 'admin';
}

/* -------------------------------------------------------------------- API */

/**
 * Ticket types the caller may buy. The Member ticket is only returned (with
 * its limit) to an account holding an active membership.
 */
export async function listTicketTypes(user) {
  if (USE_MOCKS) {
    await delay();
    const membership = user ? activeMembershipFor(user.id) : null;
    const items = TICKET_TYPES.filter((type) => !type.members_only || membership).map((type) =>
      type.members_only
        ? { ...type, max_quantity: membership.adults_covered + membership.children_covered }
        : { ...type, max_quantity: MAX_TICKETS_PER_BOOKING }
    );
    return { items, total: items.length, max_per_booking: MAX_TICKETS_PER_BOOKING };
  }
  return request('/ticket-types');
}

/** Arrival windows and places left for one date. Closed days return no windows. */
export async function getAvailability(isoDate) {
  if (USE_MOCKS) {
    await delay();
    const hours = hoursFor(isoDate);
    const tooEarly = isoDate < isoDateFromToday(0);
    const tooLate = isoDate > isoDateFromToday(BOOKING_HORIZON_DAYS);
    if (tooEarly || tooLate) {
      return { date: isoDate, is_closed: true, note: tooEarly ? 'That date has passed.' : 'Bookings open 60 days ahead.', windows: [] };
    }
    // Same-day bookings only see windows that have not started yet.
    const now = new Date();
    const nowMinutes = now.getHours() * 60 + now.getMinutes();
    const isToday = isoDate === isoDateFromToday(0);
    const windows = windowsFor(hours)
      .filter((window) => !isToday || toMinutes(window.start) > nowMinutes)
      .map((window) => ({
      ...window,
      places_left: Math.max(0, WINDOW_CAPACITY - placesTaken(isoDate, window.start)),
    }));
    return {
      date: isoDate,
      is_closed: windows.length === 0,
      opens_at: hours?.opens_at ?? null,
      closes_at: hours?.closes_at ?? null,
      note:
        windows.length === 0 && isToday && hours && !hours.is_closed
          ? "Today's last arrival time has passed."
          : hours?.note || '',
      windows,
    };
  }
  return request('/bookings/availability', { params: { date: isoDate } });
}

/**
 * payload: { visit_date, arrival_window: {start, end}, lines: [{ticket_type_id, quantity}],
 *            visitor: {first_name, last_name, email, mobile}, accessibility: [],
 *            payment_acknowledged: true }
 */
export async function createBooking(payload, user) {
  if (USE_MOCKS) {
    await delay(900); // a little longer: this stands in for the payment round trip

    if (!payload.payment_acknowledged) {
      throw new ApiError({
        status: 400,
        code: 'VALIDATION_ERROR',
        message: 'Confirm that you understand no payment will be taken.',
      });
    }

    const lines = payload.lines.filter((line) => line.quantity > 0);
    const count = ticketCount(lines);
    if (count === 0) {
      throw new ApiError({ status: 400, code: 'VALIDATION_ERROR', message: 'Choose at least one ticket.' });
    }
    if (count > MAX_TICKETS_PER_BOOKING) {
      throw new ApiError({
        status: 409,
        code: 'BOOKING_LIMIT_EXCEEDED',
        message: `One booking can hold up to ${MAX_TICKETS_PER_BOOKING} tickets. Make a second booking for the rest of your group.`,
      });
    }

    const { items: allowed } = await listTicketTypes(user);
    const priced = lines.map((line) => {
      const type = allowed.find((candidate) => candidate.id === line.ticket_type_id);
      if (!type) {
        throw new ApiError({
          status: 403,
          code: 'FORBIDDEN',
          message: 'Member tickets need an active membership on this account.',
        });
      }
      if (line.quantity > type.max_quantity) {
        throw new ApiError({
          status: 400,
          code: 'VALIDATION_ERROR',
          message: `Your membership covers ${type.max_quantity} ${type.name} tickets per visit.`,
        });
      }
      return {
        ticket_type_id: type.id,
        name: type.name,
        quantity: line.quantity,
        unit_price_cents: type.price_cents,
      };
    });

    const availability = await getAvailability(payload.visit_date);
    const window = availability.windows.find((candidate) => candidate.start === payload.arrival_window.start);
    if (!window) {
      throw new ApiError({ status: 400, code: 'VALIDATION_ERROR', message: 'That arrival time is not available on this date.' });
    }
    if (window.places_left < count) {
      throw new ApiError({
        status: 400,
        code: 'INSUFFICIENT_TICKETS',
        message: `Only ${window.places_left} places are left in that arrival window. Choose another time or fewer tickets.`,
      });
    }

    const booking = {
      id: `bk-${String(BOOKINGS.length + 1).padStart(4, '0')}`,
      reference: newReference(),
      user_id: user.id,
      visit_date: payload.visit_date,
      arrival_window: { start: window.start, end: window.end },
      lines: priced,
      total_cents: priced.reduce((sum, line) => sum + line.quantity * line.unit_price_cents, 0),
      visitor: { ...payload.visitor },
      accessibility: [...(payload.accessibility || [])],
      status: 'reserved',
      payment: { method: 'simulated', status: 'simulated_paid' },
      created_at: new Date().toISOString(),
    };
    BOOKINGS.push(booking);
    persist();
    recordLocally({ actor: user, action: 'booking.created', target: `${booking.reference} — ${count} tickets` });
    return { ...booking };
  }
  return request('/bookings', { method: 'POST', body: payload });
}

export async function getBooking(reference, user) {
  if (USE_MOCKS) {
    await delay();
    const booking = BOOKINGS.find((candidate) => candidate.reference === reference);
    // Someone else's booking is reported as missing, not forbidden — a 403
    // would confirm that the reference exists.
    if (!booking || !canSee(booking, user)) throw notFound();
    return { ...booking };
  }
  return request(`/bookings/${reference}`);
}

export async function listMyBookings(user) {
  if (USE_MOCKS) {
    await delay();
    const items = BOOKINGS.filter((booking) => booking.user_id === user.id)
      .sort((a, b) => (a.visit_date < b.visit_date ? 1 : -1))
      .map((booking) => ({ ...booking }));
    return { items, total: items.length, page: 1, size: items.length };
  }
  return request('/bookings/me');
}

export async function cancelBooking(reference, user) {
  if (USE_MOCKS) {
    await delay();
    const booking = BOOKINGS.find((candidate) => candidate.reference === reference);
    if (!booking || !canSee(booking, user)) throw notFound();
    if (booking.status !== 'reserved') {
      throw new ApiError({ status: 409, code: 'CONFLICT', message: 'Only an upcoming booking can be cancelled.' });
    }
    booking.status = 'cancelled';
    persist();
    recordLocally({ actor: user, action: 'booking.cancelled', target: booking.reference });
    return { ...booking };
  }
  return request(`/bookings/${reference}/cancel`, { method: 'POST' });
}
