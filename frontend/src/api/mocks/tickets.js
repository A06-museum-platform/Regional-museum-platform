/**
 * General-admission tickets.
 *
 * TICKET_TYPES mirrors the `ticket_type` rows in Molly's seed
 * (database/seed/seed.sql and regional_museum_1010.sql) — same names, same
 * prices — converted to integer cents because the API never sends decimals.
 *
 * `members_only` is a front-end flag: the Member ticket is free but only
 * offered to a signed-in account with an active membership, and only up to
 * the number of people that membership covers.
 */

export const TICKET_TYPES = [
  {
    id: 1,
    name: 'Adult',
    description: 'Standard adult admission ticket.',
    price_cents: 1500,
    members_only: false,
  },
  {
    id: 2,
    name: 'Concession',
    description: 'Discounted admission for eligible concession holders.',
    price_cents: 1000,
    members_only: false,
  },
  {
    id: 3,
    name: 'Child',
    description: 'Admission for children.',
    price_cents: 750,
    members_only: false,
  },
  {
    id: 4,
    name: 'Member',
    description: 'Admission for museum members.',
    price_cents: 0,
    members_only: true,
  },
];

/** Places per arrival window. Arrival windows are two hours long. */
export const WINDOW_CAPACITY = 60;
export const WINDOW_HOURS = 2;

/** Upper limit on tickets in one booking — BOOKING_LIMIT_EXCEEDED above it. */
export const MAX_TICKETS_PER_BOOKING = 10;

/** Shape follows `ticket_reservation`, grouped by booking reference. */
export const SEED_BOOKINGS = [
  {
    id: 'bk-0001',
    reference: 'SARHN-89241',
    user_id: 'u-0001',
    visit_date: '2026-10-24',
    arrival_window: { start: '10:00', end: '12:00' },
    lines: [
      { ticket_type_id: 4, name: 'Member', quantity: 2, unit_price_cents: 0 },
      { ticket_type_id: 3, name: 'Child', quantity: 1, unit_price_cents: 750 },
    ],
    total_cents: 750,
    visitor: {
      first_name: 'Eleanor',
      last_name: 'Vance',
      email: 'eleanor.vance@example.com',
      mobile: '',
    },
    accessibility: ['step_free'],
    status: 'reserved',
    payment: { method: 'simulated', status: 'simulated_paid' },
    created_at: '2026-10-02T03:12:00Z',
  },
  {
    id: 'bk-0002',
    reference: 'SARHN-87730',
    user_id: 'u-0001',
    visit_date: '2026-09-13',
    arrival_window: { start: '12:00', end: '14:00' },
    lines: [{ ticket_type_id: 4, name: 'Member', quantity: 2, unit_price_cents: 0 }],
    total_cents: 0,
    visitor: {
      first_name: 'Eleanor',
      last_name: 'Vance',
      email: 'eleanor.vance@example.com',
      mobile: '',
    },
    accessibility: [],
    status: 'completed',
    payment: { method: 'simulated', status: 'simulated_paid' },
    created_at: '2026-09-08T08:40:00Z',
  },
];
