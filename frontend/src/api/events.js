import { request, USE_MOCKS, delay, ApiError } from './client';
import { EVENTS } from './mocks/events';

/**
 * Events — client requirement 3(iii): publish event details and search them.
 *
 * Contract:
 *   GET  /events?q=&from=&to=&gallery=&audience=&page=&page_size=
 *          -> { items, total, page, page_size }
 *   GET  /events/{slug}
 *   POST /events/{slug}/registrations
 *
 * Every event carries a computed `spots_remaining`. The mock derives it from
 * registered_count; the real backend derives it from the registrations table.
 * A page must never count registrations itself.
 */

const DEFAULT_PAGE_SIZE = 10;

/** Mock-only in-memory registrations, reset on page reload. */
const localRegistrations = new Map();

function withComputed(event) {
  const extra = localRegistrations.get(event.id) ?? 0;
  const taken = event.registered_count + extra;
  // registered_count is a mock implementation detail and is not sent by the
  // real API, so strip it here rather than letting pages depend on it.
  const { registered_count: _ignored, ...rest } = event;
  return {
    ...rest,
    spots_remaining: Math.max(0, event.capacity - taken),
    is_sold_out: taken >= event.capacity,
  };
}

function suitsAudience(event, audience) {
  if (audience === 'families') {
    // Something a 10 to 14 year old can attend.
    return (event.age_min ?? 0) <= 14 && (event.age_max ?? 99) >= 10;
  }
  if (audience === 'adults') return (event.age_min ?? 0) >= 16;
  return true;
}

export async function listEvents(params = {}) {
  const page = Number(params.page) || 1;
  const pageSize = Number(params.page_size) || DEFAULT_PAGE_SIZE;

  if (USE_MOCKS) {
    await delay();
    const needle = params.q?.trim().toLowerCase();

    const matched = EVENTS.filter((event) => {
      if (event.status !== 'published') return false;
      if (needle) {
        const haystack = `${event.title} ${event.description}`.toLowerCase();
        if (!haystack.includes(needle)) return false;
      }
      if (params.gallery && event.gallery !== params.gallery) return false;
      if (params.audience && !suitsAudience(event, params.audience)) return false;
      if (params.from && new Date(event.starts_at) < new Date(params.from)) return false;
      if (params.to && new Date(event.starts_at) > new Date(params.to)) return false;
      return true;
    }).sort((a, b) => new Date(a.starts_at) - new Date(b.starts_at));

    const start = (page - 1) * pageSize;
    return {
      items: matched.slice(start, start + pageSize).map(withComputed),
      total: matched.length,
      page,
      page_size: pageSize,
    };
  }

  return request('/events', { params: { ...params, page, page_size: pageSize } });
}

export async function getEvent(slug) {
  if (USE_MOCKS) {
    await delay();
    const event = EVENTS.find((candidate) => candidate.slug === slug);
    if (!event) {
      throw new ApiError({
        status: 404,
        code: 'NOT_FOUND',
        message: 'That event does not exist.',
      });
    }
    return withComputed(event);
  }

  return request(`/events/${slug}`);
}

/**
 * Registering is free of charge in the prototype even for priced events —
 * a functional payment system is out of scope, so the confirmation says so
 * plainly rather than pretending money changed hands.
 */
export async function registerForEvent(slug, { contact_name, contact_email, party_size }) {
  if (USE_MOCKS) {
    await delay();
    const event = EVENTS.find((candidate) => candidate.slug === slug);
    if (!event) {
      throw new ApiError({ status: 404, code: 'NOT_FOUND', message: 'That event does not exist.' });
    }

    const computed = withComputed(event);
    if (party_size > computed.spots_remaining) {
      throw new ApiError({
        status: 409,
        code: 'EVENT_FULL',
        message:
          computed.spots_remaining === 0
            ? 'This session is now full.'
            : `Only ${computed.spots_remaining} places are left.`,
      });
    }

    localRegistrations.set(event.id, (localRegistrations.get(event.id) ?? 0) + party_size);

    return {
      reference: `SARHN-EV-${Math.floor(10000 + Math.random() * 89999)}`,
      status: 'confirmed',
      event_id: event.id,
      contact_name,
      contact_email,
      party_size,
    };
  }

  return request(`/events/${slug}/registrations`, {
    method: 'POST',
    body: { contact_name, contact_email, party_size },
  });
}
