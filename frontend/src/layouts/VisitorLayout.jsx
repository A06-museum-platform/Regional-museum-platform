import { useState } from 'react';
import { NavLink, Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Button from '../components/Button';
import styles from './VisitorLayout.module.css';

const NAV = [
  { to: '/visit', label: 'Visit & plan' },
  { to: '/exhibitions', label: 'Exhibitions' },
  { to: '/collections', label: 'Collections' },
  { to: '/events', label: 'Events' },
  { to: '/membership', label: 'Membership' },
];

/**
 * Shell for every public-facing page. Staff and admin screens get their own
 * layout later — they are desktop-only and share nothing with this one.
 */
export default function VisitorLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { user, isSignedIn, isStaff, signOut } = useAuth();
  const navigate = useNavigate();

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link to="/" className={styles.logo}>SARHN</Link>

          <button
            className={styles.menuToggle}
            aria-expanded={menuOpen}
            aria-label="Menu"
            onClick={() => setMenuOpen((open) => !open)}
          >
            &#9776;
          </button>

          <nav className={`${styles.nav} ${menuOpen ? '' : styles.navClosed}`}>
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  isActive ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink
                }
                onClick={() => setMenuOpen(false)}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <input
            className={styles.search}
            type="search"
            placeholder="Search collections"
            aria-label="Search collections"
          />

          <div className={styles.actions}>
            {isSignedIn ? (
              <>
                {isStaff && (
                  <Link to="/staff">
                    <Button variant="ghost" size="sm">Workspace</Button>
                  </Link>
                )}
                {user.role === 'member' && (
                  <Link to="/account">
                    <Button variant="ghost" size="sm">My account</Button>
                  </Link>
                )}
                <Link to="/book"><Button size="sm">Book tickets</Button></Link>
                <Button
                  variant="ghost"
                  size="sm"
                  title={user.full_name}
                  onClick={() => { signOut(); navigate('/'); }}
                >
                  Sign out
                </Button>
              </>
            ) : (
              <>
                <Link to="/signin"><Button variant="ghost" size="sm">Sign in</Button></Link>
                <Link to="/membership"><Button size="sm">Join</Button></Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className={styles.main}>
        <Outlet />
      </main>

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div>
            South Australian Regional Heritage Network
            <br />
            Adelaide Cultural Boulevard, North Terrace
          </div>
          <div>
            <Link to="/visit">Plan your visit</Link>
            <br />
            <Link to="/book">Book tickets</Link>
            <br />
            <Link to="/membership">Membership</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
