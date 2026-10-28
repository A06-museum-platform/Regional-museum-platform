import { Link } from 'react-router-dom';
import { formatPrice } from '../../api/constants';
import { formatCalendarDate } from '../../utils/date';
import styles from './Booking.module.css';

/** Dark "Your booking" panel beside step 2. */
export default function BookingSummary({ draft, editTo = '/book' }) {
  const lines = draft.lines.filter((line) => line.quantity > 0);
  const total = lines.reduce((sum, line) => sum + line.quantity * line.unit_price_cents, 0);
  const people = lines.reduce((sum, line) => sum + line.quantity, 0);

  return (
    <aside className={styles.summary} aria-label="Your booking">
      <div className={styles.summaryLabel}>Your booking</div>
      <h3 className={styles.summaryTitle}>General admission</h3>
      <div className={styles.summarySub}>Entry to all four galleries</div>

      <div className={styles.summaryBlock}>
        <div className={styles.summaryRow}>{formatCalendarDate(draft.visit_date)}</div>
        <div className={`${styles.summaryRow} ${styles.summaryMuted}`}>
          {draft.arrival_window.start} – {draft.arrival_window.end} arrival
        </div>
        <div style={{ marginTop: 'var(--s-4)' }}>
          {lines.map((line) => (
            <div key={line.ticket_type_id} className={styles.summaryRow}>
              <span>
                {line.quantity} × {line.name}
              </span>
              <span>{line.unit_price_cents === 0 ? 'Free' : formatPrice(line.quantity * line.unit_price_cents)}</span>
            </div>
          ))}
        </div>
        <div className={`${styles.summaryRow} ${styles.summaryMuted}`} style={{ fontSize: 'var(--fs-sm)' }}>
          {people} {people === 1 ? 'person' : 'people'}
        </div>
      </div>

      <div className={styles.summaryTotal}>
        <span>Total</span>
        <span>{formatPrice(total)}</span>
      </div>
      <div className={styles.summaryNote}>Indicative pricing for demonstration purposes.</div>
      {editTo && (
        <div style={{ marginTop: 'var(--s-4)' }}>
          <Link to={editTo} className={styles.summaryEdit}>Change date or tickets</Link>
        </div>
      )}
    </aside>
  );
}
