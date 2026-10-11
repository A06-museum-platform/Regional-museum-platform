/**
 * Keeps a mock collection alive across a page refresh.
 *
 * Mock data normally lives in module memory, so a refresh wipes anything
 * created during a demo — including the booking the confirmation page is
 * about to display. sessionStorage survives a refresh but not a closed tab,
 * which is the right lifetime for a demonstration.
 *
 * Mock-only. Against the real API the server is the only store.
 */

const PREFIX = 'sarhn.mock.';

export function loadArray(key, seed) {
  try {
    const raw = sessionStorage.getItem(PREFIX + key);
    if (raw) return JSON.parse(raw);
  } catch {
    // Private mode or blocked storage: fall back to the seed silently.
  }
  return seed;
}

export function saveArray(key, rows) {
  try {
    sessionStorage.setItem(PREFIX + key, JSON.stringify(rows));
  } catch {
    // Storage full or blocked. The data still lives in memory for this page.
  }
}
