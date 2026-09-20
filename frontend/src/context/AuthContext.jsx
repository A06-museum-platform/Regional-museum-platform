import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { login as apiLogin, logout as apiLogout, me } from '../api/auth';

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

  const signOut = useCallback(() => {
    apiLogout();
    setUser(null);
  }, []);

  const value = {
    user,
    ready,
    signIn,
    signOut,
    isSignedIn: Boolean(user),
    isStaff: user?.role === 'staff' || user?.role === 'admin',
    isAdmin: user?.role === 'admin',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside an AuthProvider');
  return context;
}
