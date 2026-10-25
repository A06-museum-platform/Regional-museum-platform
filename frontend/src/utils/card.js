/**
 * Demonstration card checkout helpers (see components/payment/CardPaymentForm).
 * Card details never leave the browser; only cardSummary() output is kept.
 */

export const EMPTY_CARD = { name: '', number: '', expiry: '', cvc: '' };

export const digits = (value) => value.replace(/\D/g, '');

export function cardBrand(number) {
  const d = digits(number);
  if (/^4/.test(d)) return 'Visa';
  if (/^(5[1-5]|2[2-7])/.test(d)) return 'Mastercard';
  if (/^3[47]/.test(d)) return 'American Express';
  return null;
}

/** Field errors, worded as what to do next. Empty object = card accepted. */
export function validateCard(card) {
  const errors = {};
  if (!card.name.trim()) errors.card_name = 'Add the name shown on the card.';
  const n = digits(card.number).length;
  if (!n) errors.card_number = 'Add the card number.';
  else if (n < 13 || n > 19) errors.card_number = 'Card numbers are 13 to 19 digits — check for a missing digit.';
  const m = card.expiry.match(/^(\d{2})\s*\/\s*(\d{2})$/);
  if (!card.expiry.trim()) errors.card_expiry = 'Add the expiry date, e.g. 08/29.';
  else if (!m || Number(m[1]) < 1 || Number(m[1]) > 12) errors.card_expiry = 'Use MM/YY, e.g. 08/29.';
  const c = digits(card.cvc).length;
  if (!c) errors.card_cvc = 'Add the 3- or 4-digit security code from the back of the card.';
  else if (c < 3 || c > 4) errors.card_cvc = 'The security code is 3 or 4 digits.';
  return errors;
}

/** What may leave this form: brand and last four digits, nothing else. */
export function cardSummary(card) {
  return { brand: cardBrand(card.number) || 'Card', last4: digits(card.number).slice(-4) };
}

export function formatCardNumber(value) {
  return digits(value).slice(0, 19).replace(/(\d{4})(?=\d)/g, '$1 ');
}

export function formatExpiry(value, previous) {
  const d = digits(value).slice(0, 4);
  // Deleting the slash shouldn't immediately re-add it.
  if (d.length === 2 && previous.length > value.length) return d;
  return d.length >= 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
}
