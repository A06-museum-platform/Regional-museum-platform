import test from 'node:test';
import assert from 'node:assert/strict';
import { validateCard, cardSummary, cardBrand, formatCardNumber, formatExpiry, EMPTY_CARD } from '../src/utils/card.js';

const good = { name: 'Sarah Nguyen', number: '4111 1111 1111 1111', expiry: '08/29', cvc: '123' };

test('any well-formed card is accepted (no Luhn or real check)', () => {
  assert.deepEqual(validateCard(good), {});
  assert.deepEqual(validateCard({ ...good, number: '1234 5678 9012 3456' }), {});
});

test('empty and malformed fields get a message each', () => {
  assert.deepEqual(Object.keys(validateCard(EMPTY_CARD)).sort(), ['card_cvc', 'card_expiry', 'card_name', 'card_number']);
  const bad = validateCard({ name: 'x', number: '4111 11', expiry: '13/29', cvc: '12' });
  assert.deepEqual(Object.keys(bad).sort(), ['card_cvc', 'card_expiry', 'card_number']);
});

test('only brand and last four digits leave the form', () => {
  assert.deepEqual(cardSummary(good), { brand: 'Visa', last4: '1111' });
  assert.equal(cardBrand('5500 0000'), 'Mastercard');
  assert.equal(cardBrand('3782'), 'American Express');
});

test('number and expiry are formatted as typed', () => {
  assert.equal(formatCardNumber('41111111abc11111111'), '4111 1111 1111 1111');
  assert.equal(formatExpiry('0829', ''), '08/29');
  assert.equal(formatExpiry('08', '08/'), '08');
});
