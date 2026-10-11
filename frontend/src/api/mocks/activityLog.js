/**
 * Activity log entries.
 *
 * Mutable on purpose: the mock write functions append here so an
 * administrator can revoke a membership and then see the reason they typed
 * appear in the log. In the real system the backend writes every row —
 * a log the browser can author is not an audit trail.
 */

export const ACTIVITY = [
  {
    id: 'al-0001',
    created_at: '2026-09-19T03:12:00Z',
    actor_name: 'Xuan Meng',
    actor_role: 'staff',
    action: 'event.published',
    target: 'Morse code and galvanic batteries: hands-on lab',
    reason: null,
    reference: null,
  },
  {
    id: 'al-0002',
    created_at: '2026-09-18T22:41:00Z',
    actor_name: 'Xuan Meng',
    actor_role: 'staff',
    action: 'opening_hours.updated',
    target: 'Weekly pattern — Friday late opening',
    reason: null,
    reference: null,
  },
  {
    id: 'al-0003',
    created_at: '2026-09-17T06:03:00Z',
    actor_name: 'Kangjun Liao',
    actor_role: 'admin',
    action: 'member.approved',
    target: 'Daniel Okafor (SA-9344)',
    reason: null,
    reference: null,
  },
  {
    id: 'al-0004',
    created_at: '2026-06-18T05:20:00Z',
    actor_name: 'Kangjun Liao',
    actor_role: 'admin',
    action: 'member.revoked',
    target: 'Rachel Vance (SA-8817)',
    reason: 'Family pass used by a non-member on three visits',
    reference: null,
  },
];

export const ACTION_LABELS = {
  'member.approved': 'Membership approved',
  'member.declined': 'Application declined',
  'member.revoked': 'Access revoked',
  'member.restored': 'Access restored',
  'event.published': 'Event published',
  'event.unpublished': 'Event unpublished',
  'opening_hours.updated': 'Opening hours updated',
  'access.refused': 'Access refused',
  'role.changed': 'Role changed',
  'member.applied': 'Membership applied for',
  'booking.created': 'Tickets booked',
  'booking.cancelled': 'Booking cancelled',
};
