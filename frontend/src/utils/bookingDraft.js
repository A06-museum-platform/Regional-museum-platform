/**
 * The in-progress booking between step 1 and step 2.
 *
 * Kept in sessionStorage, not component state, because step 2 sits behind
 * sign-in: a visitor who is not signed in is sent to /signin and back, and the
 * date and tickets they chose must still be there when they return. It also
 * survives a refresh. Cleared once the booking is created.
 *
 * Shape: { visit_date, arrival_window: {start, end},
 *          lines: [{ ticket_type_id, name, quantity, unit_price_cents }] }
 */

const KEY = 'sarhn.booking_draft';

export function loadDraft() {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveDraft(draft) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(draft));
  } catch {
    // Blocked storage: the flow still works without a refresh.
  }
}

export function clearDraft() {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // Nothing to clear.
  }
}

export const draftTicketCount = (draft) =>
  (draft?.lines || []).reduce((sum, line) => sum + line.quantity, 0);

export const draftTotal = (draft) =>
  (draft?.lines || []).reduce((sum, line) => sum + line.quantity * line.unit_price_cents, 0);
