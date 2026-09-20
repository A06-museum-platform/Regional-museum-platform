/**
 * Opening hours.
 *
 * The client said hours change seasonally and "does not matter as it changes",
 * so the model has to support both a regular weekly pattern and one-off
 * overrides for public holidays and closures. Two shapes, one table:
 *
 *   day_of_week    0-6, Sunday first — the regular weekly pattern
 *   specific_date  YYYY-MM-DD        — an override that wins for that day
 *
 * Exactly one of the two is set on any row. The backend enforces that with a
 * CHECK constraint; see the `opening_hours` table in the API contract.
 */

export const WEEKLY = [
  { id: 'oh-w0', day_of_week: 0, opens_at: '10:00', closes_at: '16:00', is_closed: false, note: '' },
  { id: 'oh-w1', day_of_week: 1, opens_at: null,    closes_at: null,    is_closed: true,  note: 'Collection care day' },
  { id: 'oh-w2', day_of_week: 2, opens_at: '09:30', closes_at: '17:00', is_closed: false, note: '' },
  { id: 'oh-w3', day_of_week: 3, opens_at: '09:30', closes_at: '17:00', is_closed: false, note: '' },
  { id: 'oh-w4', day_of_week: 4, opens_at: '09:30', closes_at: '17:00', is_closed: false, note: '' },
  { id: 'oh-w5', day_of_week: 5, opens_at: '09:30', closes_at: '20:00', is_closed: false, note: 'Late opening' },
  { id: 'oh-w6', day_of_week: 6, opens_at: '10:00', closes_at: '17:00', is_closed: false, note: '' },
];

export const OVERRIDES = [
  {
    id: 'oh-o1',
    specific_date: '2026-10-05',
    opens_at: '11:00',
    closes_at: '15:00',
    is_closed: false,
    note: 'Labour Day — reduced hours',
  },
  {
    id: 'oh-o2',
    specific_date: '2026-12-25',
    opens_at: null,
    closes_at: null,
    is_closed: true,
    note: 'Christmas Day',
  },
];
