import { request, USE_MOCKS, delay, ApiError } from './client';
import { WEEKLY, OVERRIDES } from './mocks/openingHours';

/**
 * Contract:
 *   GET /opening-hours        public, returns { weekly, overrides }
 *   PUT /staff/opening-hours  staff and admin, replaces the whole set
 *
 * PUT rather than per-row PATCH: staff edit the week as one thing, and
 * replacing it wholesale avoids a half-saved timetable if one request fails.
 */

export const DAY_NAMES = [
  'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
];

export async function getOpeningHours() {
  if (USE_MOCKS) {
    await delay();
    return {
      weekly: WEEKLY.map((row) => ({ ...row })),
      overrides: OVERRIDES.map((row) => ({ ...row })),
    };
  }
  return request('/opening-hours');
}

export async function saveOpeningHours({ weekly, overrides }) {
  // Validated here for a fast error message, and again on the server because
  // the browser is not a trustworthy validator.
  const broken = [...weekly, ...overrides].find(
    (row) => !row.is_closed && (!row.opens_at || !row.closes_at || row.opens_at >= row.closes_at)
  );
  if (broken) {
    throw new ApiError({
      status: 422,
      code: 'INVALID_HOURS',
      message: 'Every open day needs an opening time earlier than its closing time.',
    });
  }

  if (USE_MOCKS) {
    await delay();
    WEEKLY.splice(0, WEEKLY.length, ...weekly);
    OVERRIDES.splice(0, OVERRIDES.length, ...overrides);
    return { weekly, overrides };
  }

  return request('/staff/opening-hours', { method: 'PUT', body: { weekly, overrides } });
}
