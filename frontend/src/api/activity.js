import { request, USE_MOCKS, delay } from './client';
import { ACTIVITY } from './mocks/activityLog';

/**
 * Contract: GET /admin/activity-log?action=&from=&to=&page=
 *
 * There is no POST. The log is written by the backend as a side effect of the
 * action being logged — never by a client call, because a log the browser can
 * author is not an audit trail. `recordLocally` below exists only so the mock
 * can show the chain end to end; it is a no-op against the real API.
 */

export async function listActivity({ q = '', action = '' } = {}) {
  if (USE_MOCKS) {
    await delay();
    const needle = q.trim().toLowerCase();
    const matched = ACTIVITY.filter((entry) => {
      if (action && entry.action !== action) return false;
      if (needle) {
        const haystack = `${entry.actor_name} ${entry.target} ${entry.reason ?? ''}`.toLowerCase();
        if (!haystack.includes(needle)) return false;
      }
      return true;
    }).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    return { items: matched, total: matched.length };
  }

  return request('/admin/activity-log', { params: { q, action } });
}

/** Mock-only. In production the server writes this row, not the browser. */
export function recordLocally({ actor, action, target, reason = null, reference = null }) {
  if (!USE_MOCKS) return;
  ACTIVITY.unshift({
    id: `al-${Date.now()}`,
    created_at: new Date().toISOString(),
    actor_name: actor?.full_name ?? 'Unknown',
    actor_role: actor?.role ?? 'anonymous',
    action,
    target,
    reason,
    reference,
  });
}
