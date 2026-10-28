import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import useAsync from '../../hooks/useAsync';
import { useAuth } from '../../context/AuthContext';
import { getBooking, cancelBooking } from '../../api/bookings';
import { formatPrice, ACCESSIBILITY_OPTIONS } from '../../api/constants';
import { formatCalendarDate } from '../../utils/date';
import BookingSteps from '../../components/booking/BookingSteps';
import ConfirmDialog from '../../components/ConfirmDialog';
import EmptyState from '../../components/EmptyState';
import Skeleton from '../../components/Skeleton';
import Button from '../../components/Button';
import Pill from '../../components/Pill';
import styles from '../../components/booking/Booking.module.css';

/**
 * A QR-shaped pattern derived from the booking reference.
 *
 * It is deliberately NOT a scannable QR code: turnstile scanning is out of
 * scope (tagged "Visual only" in the scope sheet), and a code that scans to
 * nothing would be worse than an honest placeholder. Same reference, same
 * pattern, so it looks stable across visits to the page.
 */
function DemoPassCode({ reference }) {
  const size = 21;
  let seed = 0;
  for (const char of reference) seed = (seed * 131 + char.charCodeAt(0)) >>> 0;
  const next = () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 2 ** 32;
  };

  const inFinder = (x, y) =>
    [[0, 0], [size - 7, 0], [0, size - 7]].some(([fx, fy]) => x >= fx && x < fx + 7 && y >= fy && y < fy + 7);
  const finderOn = (x, y) => {
    const [fx, fy] = x < 7 && y < 7 ? [0, 0] : x >= size - 7 ? [size - 7, 0] : [0, size - 7];
    const dx = x - fx;
    const dy = y - fy;
    const ring = Math.min(dx, dy, 6 - dx, 6 - dy);
    return ring !== 1;
  };

  const cells = [];
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const on = inFinder(x, y) ? finderOn(x, y) : next() > 0.52;
      if (on) cells.push(<rect key={`${x}-${y}`} x={x} y={y} width="1" height="1" />);
    }
  }

  return (
    <svg className={styles.qr} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`Demonstration pass ${reference}`}>
      <g fill="#1E2A17">{cells}</g>
    </svg>
  );
}

const PLURAL = { child: 'children' };
const noun = (name, n) => {
  const word = name.toLowerCase();
  return n === 1 ? word : PLURAL[word] || `${word}s`;
};
const peopleLabel = (lines) => lines.map((line) => `${line.quantity} ${noun(line.name, line.quantity)}`).join(' + ');

/** Book tickets — step 3 of 3. Also where "My account" links to view a booking. */
export default function BookingConfirmationPage() {
  const { reference } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: booking, loading, error, reload } = useAsync(() => getBooking(reference, user), [reference, user.id]);

  const [confirmingCancel, setConfirmingCancel] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState(null);

  async function handleCancel() {
    setCancelling(true);
    setCancelError(null);
    try {
      await cancelBooking(reference, user);
      setConfirmingCancel(false);
      reload();
    } catch (err) {
      setCancelError(err.message);
      setConfirmingCancel(false);
    } finally {
      setCancelling(false);
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s-3)' }}>
        <Skeleton height={32} width="40%" />
        <Skeleton height={70} />
        <Skeleton height={200} />
      </div>
    );
  }

  if (error) {
    return (
      <EmptyState
        title={error.status === 404 ? 'We could not find that booking' : 'We could not load that booking'}
        body={
          error.status === 404
            ? 'Check the reference, or find it under your account.'
            : error.message
        }
      >
        <Button onClick={() => navigate('/account')}>Go to my account</Button>
        <Button variant="ghost" onClick={() => navigate('/book')}>Book tickets</Button>
      </EmptyState>
    );
  }

  const isCancelled = booking.status === 'cancelled';
  const isUpcoming = booking.status === 'reserved';
  const needs = booking.accessibility.map((key) => ACCESSIBILITY_OPTIONS[key] || key);

  return (
    <div>
      <h1 className={styles.noPrint}>Book tickets</h1>

      <div className={styles.noPrint}><BookingSteps current={3} /></div>
      <div className={styles.panel}>
        <div className={styles.main}>
          {isCancelled ? (
            <div className={styles.cancelledBanner} role="status">
              <h2>Booking cancelled</h2>
              <p>Reference {booking.reference}. The places have been released for other visitors.</p>
            </div>
          ) : (
            <div className={styles.confirmed} role="status">
              <h2>{isUpcoming ? 'Booking confirmed' : 'Visit completed'}</h2>
              <p>
                Reference <strong>{booking.reference}</strong>. A copy has been sent to {booking.visitor.email}.
              </p>
            </div>
          )}

          {cancelError && <div className={styles.errorBox} role="alert">{cancelError}</div>}

          <div className={styles.grid2}>
            <div>
              <div className={styles.pass}>
                <DemoPassCode reference={booking.reference} />
                <div>
                  <h3 className={styles.passTitle}>General admission</h3>
                  <div className={styles.passMeta}>
                    Entry to all four galleries
                    <br />
                    {formatCalendarDate(booking.visit_date)}, {booking.arrival_window.start}–{booking.arrival_window.end} arrival
                    <br />
                    Admits {peopleLabel(booking.lines)}
                    <br />
                    {booking.visitor.first_name} {booking.visitor.last_name} ·{' '}
                    <span className={styles.passRef}>{booking.reference}</span>
                  </div>
                  <div style={{ marginTop: 'var(--s-3)', display: 'flex', gap: 'var(--s-2)', flexWrap: 'wrap' }}>
                    <Pill tone="ochre">Demonstration pass</Pill>
                    {isCancelled && <Pill tone="danger">Cancelled</Pill>}
                  </div>
                </div>
              </div>

              <table className={styles.lineTable}>
                <tbody>
                  {booking.lines.map((line) => (
                    <tr key={line.ticket_type_id}>
                      <td>{line.quantity} × {line.name}</td>
                      <td>{line.unit_price_cents === 0 ? 'Free' : formatPrice(line.quantity * line.unit_price_cents)}</td>
                    </tr>
                  ))}
                  <tr>
                    <td>Total (simulated payment)</td>
                    <td>{formatPrice(booking.total_cents)}</td>
                  </tr>
                </tbody>
              </table>

              {needs.length > 0 && (
                <p className="hint" style={{ marginTop: 'var(--s-3)' }}>
                  Accessibility support requested: {needs.join(', ')}.
                </p>
              )}

              <div className={`${styles.actions} ${styles.noPrint}`}>
                {!isCancelled && (
                  <Button variant="ghost" size="sm" onClick={() => window.print()}>
                    Print or save pass (PDF)
                  </Button>
                )}
                {isUpcoming && (
                  <Button variant="ghost" size="sm" onClick={() => setConfirmingCancel(true)}>
                    Cancel booking
                  </Button>
                )}
                {(user.role === 'visitor' || user.role === 'member') && (
                  <Link to="/account"><Button variant="ghost" size="sm">My bookings</Button></Link>
                )}
              </div>
            </div>

            <div>
              <h3 style={{ fontSize: 16 }}>Getting there</h3>
              <div className={styles.gettingThere}>
                Adelaide Cultural Boulevard, North Terrace
                <br />
                Tram: Art Gallery / University stop, 40&nbsp;m to the main entrance
                <br />
                Parking: Wilson Adelaide Central, flat rate
                <br />
                Step-free entry and pram ramps throughout
              </div>
              <div className={styles.noPrint} style={{ marginTop: 'var(--s-5)' }}>
                <Link to="/visit">Plan your visit</Link> · <Link to="/events">What&apos;s on that day</Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      {confirmingCancel && (
        <ConfirmDialog
          title={`Cancel booking ${booking.reference}?`}
          body={`Your places on ${formatCalendarDate(booking.visit_date)} will be released for other visitors. No payment was taken, so there is nothing to refund. This cannot be undone — you would need to book again.`}
          confirmLabel="Cancel booking"
          cancelLabel="Keep booking"
          busy={cancelling}
          onConfirm={handleCancel}
          onCancel={() => setConfirmingCancel(false)}
        />
      )}
    </div>
  );
}
