/**
 * The single place the front end talks to the network.
 *
 * Nothing outside src/api/ should call fetch() directly. Keeping it here means
 * auth headers, error shapes and the mock switch are handled once instead of
 * in every page.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';
export const MOCK_DELAY = Number(import.meta.env.VITE_MOCK_DELAY ?? 400);

const TOKEN_KEY = 'sarhn.access_token';

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

/**
 * Mirrors the error shape in the API contract:
 *   { error: { code, message, reference } }
 *
 * `status` matters as much as `code`:
 *   401 — not signed in, or the token expired  -> send them to sign in
 *   403 — signed in but the role is wrong      -> show the Access refused page
 *
 * Do not collapse those two into one handler. Telling them apart is what the
 * "no privileged endpoint reachable without the required role" evaluation
 * criterion is demonstrated with.
 */
export class ApiError extends Error {
  constructor({ status, code, message, reference, fields }) {
    super(message || 'Something went wrong.');
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.reference = reference ?? null;
    this.fields = fields ?? null;
  }

  get isUnauthenticated() {
    return this.status === 401;
  }

  get isForbidden() {
    return this.status === 403;
  }
}

/** Drops undefined, null and empty-string params so URLs stay clean. */
function buildQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    search.append(key, String(value));
  });
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

export async function request(path, { method = 'GET', params, body } = {}) {
  const headers = { Accept: 'application/json' };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  let response;
  try {
    response = await fetch(`${BASE_URL}${path}${buildQuery(params)}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    // Network failure, backend container down, CORS. No HTTP status exists.
    throw new ApiError({
      status: 0,
      code: 'NETWORK_ERROR',
      message: 'We could not reach the server. Check your connection and try again.',
    });
  }

  if (response.status === 204) return null;

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new ApiError({
      status: response.status,
      code: payload?.error?.code ?? 'UNKNOWN',
      message: payload?.error?.message,
      reference: payload?.error?.reference,
      fields: payload?.error?.fields,
    });
  }

  return payload;
}

/** Used by the mock modules so loading states are visible in development. */
export const delay = (ms = MOCK_DELAY) =>
  new Promise((resolve) => setTimeout(resolve, ms));
