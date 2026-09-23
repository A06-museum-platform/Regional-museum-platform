import { useEffect } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { recordLocally } from '../api/activity';
import { useAuth } from '../context/AuthContext';
import AccessRefusedPage from '../pages/AccessRefusedPage';

/**
 * Route guard.
 *
 * READ THIS BEFORE RELYING ON IT: this component decides what to RENDER. It
 * is not a security boundary. Anyone can edit the JavaScript in their own
 * browser and make it render whatever they like.
 *
 * The actual protection is FastAPI refusing the request. Every admin endpoint
 * must check the role server-side, and the negative test cases must call those
 * endpoints directly with a staff token — not click around the UI. This is the
 * exact failure mode named in the project risk register: access control
 * implemented only in the interface while the API stays open.
 */
export default function RoleGuard({ allow }) {
  const { user, ready } = useAuth();
  const location = useLocation();

  const refused = ready && user && !allow.includes(user.role);

  // Mock-only: mirrors the row FastAPI writes when it refuses the request, so
  // the demonstration chain (refusal screen -> log entry) holds together.
  // recordLocally is a no-op against the real API — the server owns the log.
  useEffect(() => {
    if (!refused) return;
    recordLocally({
      actor: user,
      action: 'access.refused',
      target: location.pathname,
      reference: 'ACC-403',
    });
  }, [refused, location.pathname, user]);

  if (!ready) return null;

  // Not signed in at all -> 401 territory -> send them to sign in, and
  // remember where they were headed.
  if (!user) {
    return <Navigate to="/signin" state={{ from: location.pathname }} replace />;
  }

  // Signed in but the wrong role -> 403 territory -> explain, do not redirect.
  // Silently bouncing someone to the home page makes them think the link is
  // broken; the refusal screen tells them what their account can do instead.
  if (!allow.includes(user.role)) {
    return <AccessRefusedPage requiredRoles={allow} />;
  }

  return <Outlet />;
}
