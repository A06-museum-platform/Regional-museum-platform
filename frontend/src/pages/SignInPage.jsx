import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { DEMO_USERS } from '../api/mocks/users';
import { USE_AUTH_MOCKS } from '../api/auth';
import Button from '../components/Button';
import Pill from '../components/Pill';
import styles from './SignInPage.module.css';

const LANDING_BY_ROLE = {
  member: '/account',
  staff: '/staff',
  admin: '/staff',
};

export default function SignInPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(nextEmail = email, nextPassword = password) {
    setBusy(true);
    setError(null);
    try {
      const user = await signIn(nextEmail, nextPassword);
      // Send them where they were originally headed, or to the landing page
      // for their role. A remembered staff/admin URL is only honoured for an
      // account that can open it — otherwise signing out of the workspace and
      // back in as a member lands that member on the refusal screen.
      const from = location.state?.from;
      const fromAllowed =
        from &&
        !(from.startsWith('/admin') && user.role !== 'admin') &&
        !(from.startsWith('/staff') && user.role === 'member');
      navigate((fromAllowed && from) || LANDING_BY_ROLE[user.role] || '/', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.card}>
        <h1>Sign in</h1>
        <p style={{ color: 'var(--c-muted)', fontSize: 'var(--fs-sm)' }}>
          Members, museum staff and administrators all sign in here. What you
          can do afterwards depends on your account.
        </p>

        {error && <div className={styles.errorBox}>{error}</div>}

        <div className="field">
          <label htmlFor="signin-email">Email</label>
          <input
            id="signin-email"
            className="control"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="signin-password">Password</label>
          <input
            id="signin-password"
            className="control"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            onKeyDown={(event) => event.key === 'Enter' && submit()}
          />
        </div>

        <Button fullWidth disabled={busy || !email || !password} onClick={() => submit()}>
          {busy ? 'Signing in…' : 'Sign in'}
        </Button>

        <p style={{ fontSize: 'var(--fs-sm)', marginTop: 'var(--s-4)', marginBottom: 0 }}>
          Not a member yet? <Link to="/membership">Join the museum</Link>
        </p>
      </div>

      {/*
        Demo account panel. Delete this block before any deployment that is not
        a controlled demonstration — it prints working credentials on screen.
        It exists so the three roles can be shown side by side in the Week 10
        demo without the client memorising logins.
      */}
      {USE_AUTH_MOCKS && <div className={styles.demo}>
        <div className={styles.demoHead}>
          <Pill tone="ochre">Prototype</Pill>
          <strong>Demonstration accounts</strong>
        </div>
        {DEMO_USERS.map((user) => (
          <div key={user.id} className={styles.demoRow}>
            <div>
              <div className={styles.demoName}>
                {user.full_name}{' '}
                <span style={{ fontWeight: 400, textTransform: 'capitalize' }}>
                  · {user.role}
                </span>
              </div>
              <div className={styles.demoEmail}>{user.email}</div>
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setEmail(user.email);
                setPassword(user.password);
                submit(user.email, user.password);
              }}
            >
              Use
            </Button>
          </div>
        ))}
      </div>}
    </div>
  );
}
