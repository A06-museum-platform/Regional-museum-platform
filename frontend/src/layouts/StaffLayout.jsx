import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import styles from './StaffLayout.module.css';

/**
 * One layout, two variants, driven by role.
 *
 * Staff see five items. Administrators see three more, each badged so the
 * difference is obvious in a screenshot. Build the equivalent Figma component
 * with a role variant rather than two separate frames.
 *
 * Hiding an item does not protect the route behind it — RoleGuard renders the
 * refusal page, and FastAPI refuses the request. This list is convenience.
 */
const STAFF_NAV = [
  { to: '/staff', label: 'Today at a glance', end: true },
  { to: '/staff/content', label: 'Exhibitions & collections' },
  { to: '/staff/media', label: 'Media library' },
  { to: '/staff/events', label: 'Events & workshops' },
  { to: '/staff/hours', label: 'Opening hours' },
  { to: '/staff/bookings', label: 'Bookings & check-in' },
];

const ADMIN_NAV = [
  { to: '/admin/members', label: 'Members' },
  { to: '/admin/accounts', label: 'Staff accounts & roles' },
  { to: '/admin/activity', label: 'Activity log' },
];

export default function StaffLayout() {
  const { user, isAdmin, signOut } = useAuth();
  const navigate = useNavigate();

  const linkClass = ({ isActive }) =>
    isActive ? `${styles.navItem} ${styles.navItemActive}` : styles.navItem;

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <div className={styles.brandName}>SARHN</div>
          <div className={styles.brandRole}>
            {isAdmin ? 'Administration' : 'Staff workspace'}
          </div>
        </div>

        <nav className={styles.nav}>
          {STAFF_NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={linkClass}>
              {item.label}
            </NavLink>
          ))}

          {isAdmin &&
            ADMIN_NAV.map((item) => (
              <NavLink key={item.to} to={item.to} className={linkClass}>
                {item.label}
                <span className={styles.adminBadge}>Admin</span>
              </NavLink>
            ))}
        </nav>

        <div className={styles.account}>
          <div className={styles.accountName}>{user?.full_name}</div>
          <div className={styles.accountRole}>{user?.role}</div>
          <button
            type="button"
            className={styles.signOut}
            onClick={() => { signOut(); navigate('/'); }}
          >
            Sign out
          </button>
        </div>
      </aside>

      <div className={styles.content}>
        <div className={styles.topbar}>
          <span>South Australian Regional Heritage Network</span>
          <NavLink to="/">View the public site</NavLink>
        </div>
        <main className={styles.main}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
