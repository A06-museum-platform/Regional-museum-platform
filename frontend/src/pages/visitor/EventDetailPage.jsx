import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import { getEvent, registerForEvent } from '../../api/events';
import { galleryLabel, formatPrice } from '../../api/constants';
import { formatDate, formatTimeRange } from '../../utils/date';
import EmptyState from '../../components/EmptyState';
import Skeleton from '../../components/Skeleton';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import styles from './EventDetailPage.module.css';

function audienceLabel({ age_min, age_max }) {
  if (age_min && age_max) return `Ages ${age_min}–${age_max}`;
  if (age_min) return `Ages ${age_min}+`;
  return 'All ages';
}

export default function EventDetailPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const { data: event, loading, error, reload } = useAsync(() => getEvent(slug), [slug]);

  const [form, setForm] = useState({ contact_name: '', contact_email: '', party_size: 1 });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [confirmation, setConfirmation] = useState(null);

  const setField = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  async function handleRegister() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await registerForEvent(slug, {
        ...form,
        party_size: Number(form.party_size),
      });
      setConfirmation(result);
      reload();
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className={styles.layout}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-3)' }}>
          <Skeleton height={16} width="35%" />
          <Skeleton height={32} width="80%" />
          <Skeleton height={80} />
          <Skeleton height={200} />
        </div>
        <Skeleton height={280} />
      </div>
    );
  }

  if (error) {
    const notFound = error.status === 404;
    return (
      <EmptyState
        title={notFound ? 'We could not find that session' : 'We could not load that session'}
        body={notFound ? 'It may have finished, or the link may be out of date.' : error.message}
      >
        <Button onClick={() => navigate('/events')}>Back to events</Button>
      </EmptyState>
    );
  }

  const taken = event.capacity - event.spots_remaining;
  const filledPercent = Math.round((taken / event.capacity) * 100);
  const lowStock = event.spots_remaining <= 5 && !event.is_sold_out;
  const formValid = form.contact_name.trim() && form.contact_email.includes('@');

  return (
    <div>
      <nav className={styles.crumbs} aria-label="Breadcrumb">
        <Link to="/events">Events and workshops</Link> / {event.title}
      </nav>

      <div className={styles.layout}>
        <div>
          <div className={styles.pills}>
            <Pill tone="lime">{audienceLabel(event)}</Pill>
            <Pill>{galleryLabel(event.gallery)}</Pill>
            {event.is_sold_out && <Pill tone="danger">Fully booked</Pill>}
          </div>

          <h1 className={styles.title}>{event.title}</h1>
          <p>{event.description}</p>

          <table className={styles.facts}>
            <tbody>
              <tr><th scope="row">Date</th><td>{formatDate(event.starts_at)}</td></tr>
              <tr><th scope="row">Time</th><td>{formatTimeRange(event.starts_at, event.ends_at)}</td></tr>
              <tr><th scope="row">Where</th><td>{galleryLabel(event.gallery)}</td></tr>
              <tr><th scope="row">Suitable for</th><td>{audienceLabel(event)}</td></tr>
              <tr>
                <th scope="row">Admission</th>
                <td>
                  {event.price_cents === 0 ? 'Free' : formatPrice(event.price_cents)}
                  {event.price_cents > 0 && event.member_price_cents === 0 && ' · free for members'}
                  {event.price_cents > 0 && event.member_price_cents > 0 &&
                    ` · ${formatPrice(event.member_price_cents)} for members`}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <aside className={styles.panel}>
          {confirmation ? (
            <div className={styles.confirmed}>
              <h3>You are registered</h3>
              <p style={{ fontSize: 'var(--fs-sm)', marginBottom: 'var(--s-3)' }}>
                Reference {confirmation.reference}. We have your place for{' '}
                {confirmation.party_size}{' '}
                {confirmation.party_size === 1 ? 'person' : 'people'}.
              </p>
              <p style={{ fontSize: 'var(--fs-xs)', color: 'var(--c-muted)', marginBottom: 0 }}>
                This is a demonstration booking. No confirmation email is sent and no
                payment has been taken.
              </p>
            </div>
          ) : (
            <>
              <div className={styles.price}>
                {event.price_cents === 0 ? 'Free' : formatPrice(event.price_cents)}
              </div>

              <div className={styles.bar}>
                <div
                  className={`${styles.barFill} ${lowStock ? styles.barFillLow : ''}`}
                  style={{ width: `${filledPercent}%` }}
                />
              </div>
              <div className={styles.capacity}>
                {event.is_sold_out
                  ? 'All places taken'
                  : `${event.spots_remaining} of ${event.capacity} places available`}
              </div>

              {event.is_sold_out ? (
                <EmptyState
                  title="This session is full"
                  body="Other sessions in the same programme may still have places."
                >
                  <Link to="/events"><Button size="sm">See other sessions</Button></Link>
                </EmptyState>
              ) : (
                <>
                  <div className={styles.notice}>
                    <div className={styles.noticeHead}>
                      <Pill tone="ochre">Prototype</Pill>
                      <strong>Registration is simulated</strong>
                    </div>
                    No payment is taken and no email is sent. Registering reserves the
                    place in the demonstration system exactly as the finished platform
                    would.
                  </div>

                  {submitError && <div className={styles.errorBox}>{submitError}</div>}

                  <div className="field">
                    <label htmlFor="reg-name">Your name</label>
                    <input id="reg-name" className="control" value={form.contact_name}
                      onChange={setField('contact_name')} />
                  </div>

                  <div className="field">
                    <label htmlFor="reg-email">Email</label>
                    <input id="reg-email" className="control" type="email"
                      value={form.contact_email} onChange={setField('contact_email')} />
                    <div className="hint">We send the session details here.</div>
                  </div>

                  <div className="field">
                    <label htmlFor="reg-party">How many people</label>
                    <select id="reg-party" className="control" value={form.party_size}
                      onChange={setField('party_size')}>
                      {Array.from(
                        { length: Math.min(6, event.spots_remaining) },
                        (_, i) => i + 1
                      ).map((n) => (
                        <option key={n} value={n}>{n}</option>
                      ))}
                    </select>
                  </div>

                  <Button fullWidth disabled={!formValid || submitting} onClick={handleRegister}>
                    {submitting ? 'Registering…' : 'Register (simulated)'}
                  </Button>
                </>
              )}
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
