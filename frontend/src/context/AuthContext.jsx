import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { login as apiLogin, logout as apiLogout, register as apiRegister, me } from '../api/auth';

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

  useEffect(() => {
    me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setReady(true));
  }, []);

  const signIn = useCallback(async (email, password) => {
    const { user: signedIn } = await apiLogin(email, password);
    setUser(signedIn);
    return signedIn;
  }, []);

  const signUp = useCallback(async (details) => {
    const { user: created } = await apiRegister(details);
    setUser(created);
    return created;
  }, []);

  /** Re-read the account, e.g. after a membership approval changes the role. */
  const refresh = useCallback(async () => {
    const current = await me();
    setUser(current);
    return current;
  }, []);

  const signOut = useCallback(() => {
    apiLogout();
    setUser(null);
  }, []);

  const value = {
    user,
    ready,
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
