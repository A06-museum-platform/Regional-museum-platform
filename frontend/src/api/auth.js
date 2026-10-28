import { request, USE_MOCKS, delay, ApiError, setToken, clearToken, getToken } from './client';
import { DEMO_USERS } from './mocks/users';

/**
 * Contract:
 *   POST /auth/login    -> { access_token, user }
 *   GET  /auth/me       -> user
 *   POST /auth/register -> { access_token, user }
 *
 * The role the UI trusts comes from /auth/me, not from anything the browser
 * stored. A tampered localStorage value must not grant anything — the server
 * decides on every request. The role here only controls what is rendered.
 */

const MOCK_TOKEN_PREFIX = 'mock.';
export const USE_AUTH_MOCKS = import.meta.env.VITE_AUTH_USE_MOCKS === undefined
  ? USE_MOCKS : import.meta.env.VITE_AUTH_USE_MOCKS === 'true';

const normaliseUser = (user) => ({ ...user, full_name: user.full_name || user.display_name });

export async function login(email, password) {
  if (USE_AUTH_MOCKS) {
    await delay();
    const user = DEMO_USERS.find(
      (candidate) => candidate.email.toLowerCase() === email.trim().toLowerCase()
    );

    if (!user || user.password !== password) {
      throw new ApiError({
        status: 401,
        code: 'INVALID_CREDENTIALS',
        // Deliberately vague: saying "no such email" tells an attacker which
        // addresses are registered.
        message: 'That email and password combination does not match an account.',
      });
    }

    if (!user.is_active) {
      throw new ApiError({
        status: 403,
        code: 'ACCOUNT_REVOKED',
        message: 'Access to this account has been revoked. Contact the museum for help.',
        reference: 'ACC-403',
      });
    }

    const safeUser = { ...user };
    delete safeUser.password;
    setToken(`${MOCK_TOKEN_PREFIX}${user.id}`);
    return { access_token: `${MOCK_TOKEN_PREFIX}${user.id}`, user: safeUser };
  }

  const result = await request('/auth/login', { method: 'POST', body: { email, password } });
  setToken(result.access_token);
  return { ...result, user: normaliseUser(result.user) };
}

export async function me() {
  const token = getToken();
  if (!token) return null;

  if (USE_AUTH_MOCKS) {
    await delay(0);
    if (!token.startsWith(MOCK_TOKEN_PREFIX)) return null;
    const id = token.slice(MOCK_TOKEN_PREFIX.length);
    const user = DEMO_USERS.find((candidate) => candidate.id === id);
    if (!user || !user.is_active) {
      clearToken();
      return null;
    }
    const safeUser = { ...user };
    delete safeUser.password;
    return safeUser;
  }

  try {
    return normaliseUser(await request('/auth/me'));
  } catch (error) {
    if (error.isUnauthenticated) {
      // request() already invalidated only the token used by this request.
      // Clearing again here could erase a newer login after a delayed 401.
      return null;
    }
    throw error;
  }
}

/**
 * Create a visitor account, then sign straight in with it. A new account is
 * a Visitor; it becomes a Member when an administrator approves a
 * membership application.
 */
export async function register({ first_name, last_name, email, password }) {
  if (USE_AUTH_MOCKS) {
    await delay();
    throw new ApiError({
      status: 501,
      code: 'NOT_AVAILABLE',
      message: 'Creating accounts needs the backend. Use one of the demonstration accounts.',
    });
  }
  await request('/auth/register', { method: 'POST', body: { first_name, last_name, email, password } });
  return login(email, password);
}

export function logout() {
  clearToken();
}
