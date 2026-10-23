import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Button from '../components/Button';
import styles from './SignInPage.module.css';

/**
 * Create a visitor account (client requirement 3(iv): "sign-up for new
 * members"). An account can book tickets and register for events straight
 * away; it becomes a member once an administrator approves a membership
 * application.
 *
 * Messages say what to do next, never just "invalid" (design board,
 * "Empty, error and loading states").
 */
export default function RegisterPage() {
  const { signUp } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', password: '', confirm: '',
  });
  const [attempted, setAttempted] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (key) => (event) => setForm((prev) => ({ ...prev, [key]: event.target.value }));

  const errors = {};
  if (!form.first_name.trim()) errors.first_name = 'Add your first name.';
  if (!form.last_name.trim()) errors.last_name = 'Add your last name.';
  if (!form.email.includes('@')) errors.email = 'Add your email address, including the @.';
  else if (!/@[^@\s]+\.[^@\s]+$/.test(form.email.trim()))
    errors.email = 'Add the part after the @ so we can send your passes.';
  if (form.password.length < 8) errors.password = 'Use at least 8 characters.';
  if (form.confirm !== form.password) errors.confirm = 'The two passwords need to match.';

  const show = (key) => attempted && errors[key];

  async function submit(event) {
    event.preventDefault();
    setAttempted(true);
    if (Object.keys(errors).length > 0) return;
    setBusy(true);
    setError(null);
    try {
      await signUp({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        email: form.email.trim(),
        password: form.password,
      });
      navigate(location.state?.from || '/account', { replace: true });
    } catch (err) {
      setError(
        err.status === 409
          ? 'An account already uses that email. Sign in instead, or use a different email.'
          : err.message
      );
    } finally {
      setBusy(false);
    }
  }

  const field = (key, label, props = {}) => (
    <div className="field">
      <label htmlFor={`reg-${key}`}>{label}</label>
      <input
        id={`reg-${key}`}
        className="control"
        value={form[key]}
        onChange={set(key)}
        aria-invalid={Boolean(show(key))}
        aria-describedby={show(key) ? `reg-${key}-error` : undefined}
        style={show(key) ? { borderColor: 'var(--c-danger)', borderWidth: 2 } : undefined}
        {...props}
      />
      {show(key) && (
        <div id={`reg-${key}-error`} style={{ color: 'var(--c-danger)', fontSize: 'var(--fs-sm)', marginTop: 5 }}>
          {errors[key]}
        </div>
      )}
    </div>
  );

  return (
    <div className={styles.wrap}>
      <form className={styles.card} onSubmit={submit} noValidate>
        <h1>Create an account</h1>
        <p style={{ color: 'var(--c-muted)', fontSize: 'var(--fs-sm)' }}>
          Book tickets, register for workshops and keep your passes in one place.
          Membership is a separate step once you have an account.
        </p>

        {error && <div className={styles.errorBox} role="alert">{error}</div>}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--s-3)' }}>
          {field('first_name', 'First name', { autoComplete: 'given-name' })}
          {field('last_name', 'Last name', { autoComplete: 'family-name' })}
        </div>
        {field('email', 'Email', { type: 'email', autoComplete: 'email' })}
        {field('password', 'Password', { type: 'password', autoComplete: 'new-password' })}
        {field('confirm', 'Confirm password', { type: 'password', autoComplete: 'new-password' })}

        <Button type="submit" fullWidth disabled={busy}>
          {busy ? 'Creating your account…' : 'Create account'}
        </Button>

        <p style={{ fontSize: 'var(--fs-sm)', marginTop: 'var(--s-4)', marginBottom: 0 }}>
          Already have an account?{' '}
          <Link to="/signin" state={location.state}>Sign in</Link>
        </p>
      </form>
    </div>
  );
}
