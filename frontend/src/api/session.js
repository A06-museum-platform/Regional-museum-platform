// Session lifecycle only. The server remains authoritative for token validity
// and roles; decoding exp here is just a timely sign-in prompt for the UI.
export const TOKEN_KEY = 'sarhn.access_token';
export const SESSION_EXPIRED_EVENT = 'sarhn:session-expired';
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = token => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export function expireSession(tokenUsed) {
  // A late 401 from a previous session must never erase a fresh login.
  if (getToken() !== tokenUsed) return false;
  clearToken();
  window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  return true;
}

export function tokenExpiresAt(token) {
  try {
    const payload = token?.split('.')[1];
    if (!payload) return null;
    const { exp } = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    return typeof exp === 'number' && Number.isFinite(exp) && exp > 0 ? exp * 1000 : null;
  } catch {
    return null;
  }
}
