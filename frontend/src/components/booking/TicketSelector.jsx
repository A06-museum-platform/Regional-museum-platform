import { formatPrice } from '../../api/constants';
import styles from './Booking.module.css';

/**
 * One row per ticket type with a − / + stepper.
 *
 * `quantities` is { [ticket_type_id]: number }. The + button stops at the
 * type's own limit (a membership covers a fixed number of people) and at the
 * per-booking limit across all rows, and says which one was hit.
 */
export default function TicketSelector({ types, quantities, onChange, maxPerBooking }) {
  const total = Object.values(quantities).reduce((sum, n) => sum + n, 0);

  const set = (id, next) => onChange({ ...quantities, [id]: Math.max(0, next) });

  return (
    <div className={styles.tickets}>
      {types.map((type) => {
        const quantity = quantities[type.id] || 0;
        const atTypeLimit = quantity >= type.max_quantity;
        const atBookingLimit = total >= maxPerBooking;
        return (
          <div key={type.id} className={styles.ticket}>
            <div>
              <div className={styles.ticketName}>{type.name}</div>
              <div className={styles.ticketMeta}>
                {type.price_cents === 0 ? 'Free' : formatPrice(type.price_cents)} · {type.description}
                {type.members_only && ` Up to ${type.max_quantity} per visit on your membership.`}
              </div>
            </div>
            <div className={styles.stepper}>
              <button
                type="button"
                className={styles.stepperBtn}
                onClick={() => set(type.id, quantity - 1)}
                disabled={quantity === 0}
                aria-label={`Remove one ${type.name} ticket`}
              >
                −
              </button>
              <span className={styles.stepperValue} aria-live="polite" aria-label={`${quantity} ${type.name}`}>
                {quantity}
              </span>
              <button
                type="button"
                className={`${styles.stepperBtn} ${styles.stepperBtnAdd}`}
                onClick={() => set(type.id, quantity + 1)}
                disabled={atTypeLimit || atBookingLimit}
                aria-label={`Add one ${type.name} ticket`}
                title={
                  atTypeLimit && type.members_only
                    ? 'Your membership covers this many people'
                    : atBookingLimit
                      ? `Up to ${maxPerBooking} tickets per booking`
                      : undefined
                }
              >
                +
              </button>
            </div>
          </div>
        );
      })}
      {total >= maxPerBooking && (
        <div className="hint">
          One booking holds up to {maxPerBooking} tickets. Larger groups can make a second booking.
        </div>
      )}
    </div>
  );
}
