import { cardBrand, digits, formatCardNumber, formatExpiry } from '../../utils/card';
import styles from './CardPaymentForm.module.css';

/**
 * Card payment fields — a realistic checkout for the prototype.
 *
 * Nothing here is a real payment. The card details live only in the parent
 * component's state: they are never sent to the API, logged or stored. Only
 * the brand and last four digits are passed on (to show "Visa •••• 4242" on
 * the receipt). Any well-formed values are accepted; a finished system would
 * replace this component with the payment provider's hosted fields.
 */

export default function CardPaymentForm({ card, onChange, errors = {}, amountLabel, idPrefix = 'pay' }) {
  const set = (key, format) => (event) => {
    const raw = event.target.value;
    onChange({ ...card, [key]: format ? format(raw, card[key]) : raw }, `card_${key}`);
  };
  const cls = (key) => `control ${errors[key] ? 'control--error' : ''}`;
  const brand = cardBrand(card.number);

  return (
    <fieldset className={styles.payment}>
      <legend className={styles.legend}>Payment details</legend>
      {amountLabel && (
        <div className={styles.amount}>
          <span>Amount due</span>
          <strong>{amountLabel}</strong>
        </div>
      )}

      <div className={styles.brands} aria-hidden="true">
        {['Visa', 'Mastercard', 'American Express'].map((b) => (
          <span key={b} className={`${styles.brand} ${brand === b ? styles.brandOn : ''}`}>{b === 'American Express' ? 'Amex' : b}</span>
        ))}
      </div>

      <div className="field">
        <label htmlFor={`${idPrefix}-name`}>Name on card</label>
        <input id={`${idPrefix}-name`} className={cls('card_name')} autoComplete="off"
          value={card.name} onChange={set('name')} />
        {errors.card_name && <div className="error-text">{errors.card_name}</div>}
      </div>

      <div className="field">
        <label htmlFor={`${idPrefix}-number`}>Card number</label>
        <input id={`${idPrefix}-number`} className={cls('card_number')} inputMode="numeric" autoComplete="off"
          placeholder="1234 5678 9012 3456" value={card.number} onChange={set('number', formatCardNumber)} />
        {errors.card_number && <div className="error-text">{errors.card_number}</div>}
      </div>

      <div className={styles.row}>
        <div className="field">
          <label htmlFor={`${idPrefix}-expiry`}>Expiry (MM/YY)</label>
          <input id={`${idPrefix}-expiry`} className={cls('card_expiry')} inputMode="numeric" autoComplete="off"
            placeholder="MM/YY" value={card.expiry} onChange={set('expiry', formatExpiry)} />
          {errors.card_expiry && <div className="error-text">{errors.card_expiry}</div>}
        </div>
        <div className="field">
          <label htmlFor={`${idPrefix}-cvc`}>Security code</label>
          <input id={`${idPrefix}-cvc`} className={cls('card_cvc')} inputMode="numeric" autoComplete="off"
            placeholder="CVC" value={card.cvc} onChange={set('cvc', (v) => digits(v).slice(0, 4))} />
          {errors.card_cvc && <div className="error-text">{errors.card_cvc}</div>}
        </div>
      </div>

      <p className={styles.note}>
        Demonstration checkout: no money is taken, and card details are not sent or stored.
      </p>
    </fieldset>
  );
}
