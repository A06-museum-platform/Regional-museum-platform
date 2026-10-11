import Button from '../Button';
import Pill from '../Pill';
import styles from './Booking.module.css';

/**
 * Stands where a card form would be. No card fields, no gateway name, no
 * PCI claim — a functional payment system is out of scope, so the step is
 * labelled as simulated in words the visitor cannot miss.
 */
export default function SimulatedPaymentForm({ totalLabel, acknowledged, onAcknowledge, onConfirm, busy, error }) {
  return (
    <div className={styles.simulated}>
      <div className={styles.simulatedHead}>
        <Pill tone="ochre">Prototype</Pill>
        <h3>Payment is simulated</h3>
      </div>
      <p>
        This prototype does not process real payments and does not collect card details.
        Selecting confirm will create the booking and issue a demonstration pass, exactly as
        the finished system would after a successful payment{totalLabel ? ` of ${totalLabel}` : ''}.
      </p>
      <label className={styles.ack}>
        <input
          type="checkbox"
          checked={acknowledged}
          onChange={(event) => onAcknowledge(event.target.checked)}
        />
        <span>I understand this is a demonstration booking and no payment will be taken.</span>
      </label>
      {error && <div className={styles.errorBox} role="alert">{error}</div>}
      <Button onClick={onConfirm} disabled={busy}>
        {busy ? 'Confirming…' : 'Confirm booking (simulated)'}
      </Button>
    </div>
  );
}
