import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { login as apiLogin, logout as apiLogout, register as apiRegister, me } from '../api/auth';
import { expireSession, getToken, tokenExpiresAt, TOKEN_KEY, SESSION_EXPIRED_EVENT } from '../api/session';

const AuthContext = createContext(null);

/**
 * Holds the signed-in user for the whole app.
 *
 * `ready` matters: on a page refresh the token is in localStorage but the user
 * has not been fetched yet. Rendering a guard before `ready` is true would
 * bounce a signed-in administrator to the sign-in page every refresh.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);
  const generation = useRef(0);

  useEffect(() => {
    let active = true;
    const load = () => {
      const version = generation.current;
      me().then(current => {
        if (active && version === generation.current) setUser(current);
      }).catch(() => {
        if (active && version === generation.current) setUser(null);
      }).finally(() => {
        if (active && version === generation.current) setReady(true);
      });
    };
    const expired = () => {
      generation.current += 1;
      setUser(null);
      setSessionExpired(true);
      setReady(true);
    };
    const changedInAnotherTab = event => {
      if (event.key !== TOKEN_KEY && event.key !== null) return;
      generation.current += 1;
      if (!getToken()) expired();
      else load();
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, expired);
    window.addEventListener('storage', changedInAnotherTab);
    load();
    return () => {
      active = false;
      window.removeEventListener(SESSION_EXPIRED_EVENT, expired);
      window.removeEventListener('storage', changedInAnotherTab);
    };
  }, []);

  useEffect(() => {
    if (!user) return;
    const token = getToken();
    const expires = tokenExpiresAt(token);
    let timer;
    const check = () => {
      const current = getToken();
      if (!current) expireSession(null);
      else if (current === token && expires !== null && expires <= Date.now()) expireSession(token);
    };
    if (expires !== null) timer = window.setTimeout(check, Math.max(0, Math.min(expires - Date.now(), 2147483647)));
    window.addEventListener('focus', check);
    document.addEventListener('visibilitychange', check);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener('focus', check);
      document.removeEventListener('visibilitychange', check);
    };
  }, [user]);

  const signIn = useCallback(async (email, password) => {
    generation.current += 1;
    const { user: signedIn } = await apiLogin(email, password);
    generation.current += 1;
    setUser(signedIn);
    setSessionExpired(false);
    setReady(true);
    return signedIn;
  }, []);

  const signUp = useCallback(async (details) => {
    generation.current += 1;
    const { user: created } = await apiRegister(details);
    generation.current += 1;
    setUser(created);
    setSessionExpired(false);
    setReady(true);
    return created;
  }, []);

  /** Re-read the account, e.g. after a membership approval changes the role. */
  const refresh = useCallback(async () => {
    const version = generation.current;
    const current = await me();
    if (version === generation.current) setUser(current);
    return current;
  }, []);

  const signOut = useCallback(() => {
    generation.current += 1;
    apiLogout();
    setUser(null);
    setSessionExpired(false);
    setReady(true);
  }, []);

  const value = {
    user,
    ready,
    sessionExpired,
    signIn,
    signUp,
    signOut,
    refresh,
    isSignedIn: Boolean(user),
    isStaff: user?.role === 'staff' || user?.role === 'admin',
    isAdmin: user?.role === 'admin',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// The hook lives beside its provider on purpose; fast refresh still works for
// every component that uses it.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside an AuthProvider');
  return context;
}
