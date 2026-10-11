import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { createBooking } from '../../api/bookings';
import { formatPrice, ACCESSIBILITY_OPTIONS } from '../../api/constants';
import { loadDraft, clearDraft, draftTotal, draftTicketCount } from '../../utils/bookingDraft';
import BookingSteps from '../../components/booking/BookingSteps';
import BookingSummary from '../../components/booking/BookingSummary';
import SimulatedPaymentForm from '../../components/booking/SimulatedPaymentForm';
import FormErrorSummary from '../../components/FormErrorSummary';
import EmptyState from '../../components/EmptyState';
import Button from '../../components/Button';
import styles from '../../components/booking/Booking.module.css';

function splitName(fullName = '') {
  const parts = fullName.trim().split(/\s+/);
  return { first: parts[0] || '', last: parts.slice(1).join(' ') };
}

/** Error messages say what to do next, per the design review. */
function validate(form, acknowledged) {
  const errors = {};
  if (!form.first_name.trim()) errors.first_name = 'Add a first name for the pass.';
  if (!form.last_name.trim()) errors.last_name = 'Add a last name for the pass.';
  if (!form.email.trim()) {
    errors.email = 'Add an email address so we can send your pass.';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
    errors.email = form.email.includes('@')
      ? 'Add the part after the @ so we can send your pass.'
      : 'Include an @ in the email address.';
  }
  if (form.mobile.trim() && !/^[+\d][\d\s]{7,}$/.test(form.mobile.trim())) {
    errors.mobile = 'Use digits only for the mobile number, e.g. 0400 000 000.';
  }
  if (!acknowledged) errors.ack = 'Tick the box to confirm you understand no payment will be taken.';
  return errors;
}

/**
 * Book tickets — step 2 of 3: who is visiting, and the simulated payment.
 * Behind sign-in (route guard), so `user` is always present here.
 */
export default function CheckoutPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [draft] = useState(loadDraft); // read once on arrival

  const { first, last } = splitName(user.full_name);
  const [form, setForm] = useState({ first_name: first, last_name: last, email: user.email, mobile: '' });
  const [accessibility, setAccessibility] = useState([]);
  const [acknowledged, setAcknowledged] = useState(false);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  if (!draft || draftTicketCount(draft) === 0) {
    return (
      <EmptyState
        title="Start by choosing your visit"
        body="Your date and tickets were not found — they are kept only until the booking is made or the tab is closed."
      >
        <Button onClick={() => navigate('/book')}>Choose a date and tickets</Button>
      </EmptyState>
    );
  }

  const setField = (key) => (event) => {
    setForm((prev) => ({ ...prev, [key]: event.target.value }));
    setErrors((prev) => ({ ...prev, [key]: undefined }));
  };

  const toggleNeed = (key) =>
    setAccessibility((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));

  async function handleConfirm() {
    const next = validate(form, acknowledged);
    setErrors(next);
    setSubmitError(null);
    if (Object.keys(next).length) return;

    setBusy(true);
    try {
      const booking = await createBooking(
        {
          visit_date: draft.visit_date,
          arrival_window: draft.arrival_window,
          lines: draft.lines.map(({ ticket_type_id: id, quantity }) => ({ ticket_type_id: id, quantity })),
          visitor: {
            first_name: form.first_name.trim(),
            last_name: form.last_name.trim(),
            email: form.email.trim(),
            mobile: form.mobile.trim(),
          },
          accessibility,
          payment_acknowledged: true,
        },
        user
      );
      clearDraft();
      navigate(`/book/confirmation/${booking.reference}`, { replace: true });
    } catch (err) {
      setSubmitError(err.message);
      setBusy(false);
    }
  }

  const fieldClass = (key) => `control ${errors[key] ? 'control--error' : ''}`;
  const total = draftTotal(draft);
  const shownErrors = Object.fromEntries(Object.entries(errors).filter(([, v]) => v));

  return (
    <div>
      <h1>Book tickets</h1>
      <p style={{ color: 'var(--c-muted)' }}>
        Booking as {user.full_name}. <Link to="/book">Back to date and tickets</Link>
      </p>

      <BookingSteps current={2} />
      <div className={`${styles.panel} ${styles.split}`}>
        <div className={styles.main}>
          <h2 className={styles.sectionTitle}>Who is visiting</h2>
          <p className={styles.sectionHint}>We send the entry pass to this email address.</p>

          <div className={styles.row2}>
            <div className="field">
              <label htmlFor="bk-first">First name</label>
              <input id="bk-first" className={fieldClass('first_name')} autoComplete="given-name"
                value={form.first_name} onChange={setField('first_name')} />
              {errors.first_name && <div className="error-text">{errors.first_name}</div>}
            </div>
            <div className="field">
              <label htmlFor="bk-last">Last name</label>
              <input id="bk-last" className={fieldClass('last_name')} autoComplete="family-name"
                value={form.last_name} onChange={setField('last_name')} />
              {errors.last_name && <div className="error-text">{errors.last_name}</div>}
            </div>
          </div>

          <div className={styles.row2}>
            <div className="field">
              <label htmlFor="bk-email">Email</label>
              <input id="bk-email" type="email" className={fieldClass('email')} autoComplete="email"
                value={form.email} onChange={setField('email')} />
              {errors.email && <div className="error-text">{errors.email}</div>}
            </div>
            <div className="field">
              <label htmlFor="bk-mobile">Mobile (optional)</label>
              <input id="bk-mobile" type="tel" className={fieldClass('mobile')} autoComplete="tel"
                placeholder="0400 000 000" value={form.mobile} onChange={setField('mobile')} />
              {errors.mobile && <div className="error-text">{errors.mobile}</div>}
            </div>
          </div>

          <fieldset className="field" style={{ border: 0, padding: 0, margin: 0 }}>
            <legend style={{ fontSize: 'var(--fs-sm)', fontWeight: 600, padding: 0 }}>
              Accessibility support needed on the day
            </legend>
            <div className={styles.checks}>
              {Object.entries(ACCESSIBILITY_OPTIONS).map(([key, label]) => (
                <label key={key} className={styles.check}>
                  <input type="checkbox" checked={accessibility.includes(key)} onChange={() => toggleNeed(key)} />
                  {label}
                </label>
              ))}
            </div>
            <div className="hint">Staff see this on the day's booking list so it is ready when you arrive.</div>
          </fieldset>

          <SimulatedPaymentForm
            totalLabel={total > 0 ? formatPrice(total) : null}
            acknowledged={acknowledged}
            onAcknowledge={(value) => {
              setAcknowledged(value);
              setErrors((prev) => ({ ...prev, ack: undefined }));
            }}
            onConfirm={handleConfirm}
            busy={busy}
            error={submitError}
          />
          <div style={{ marginTop: 'var(--s-4)' }}>
            <FormErrorSummary errors={shownErrors} />
          </div>
        </div>

        <BookingSummary draft={draft} />
      </div>
    </div>
  );
}
