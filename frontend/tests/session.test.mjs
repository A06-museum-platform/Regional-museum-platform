import test from 'node:test';
import assert from 'node:assert/strict';
import { getToken, setToken, expireSession, tokenExpiresAt, SESSION_EXPIRED_EVENT } from '../src/api/session.js';

function setup() {
  const values = new Map();
  globalThis.localStorage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: key => values.delete(key),
  };
  globalThis.window = new EventTarget();
}

test('rejected current token clears the stored session and notifies the UI', () => {
  setup();setToken('expired');let notified = 0;
  window.addEventListener(SESSION_EXPIRED_EVENT, () => notified++);
  assert.equal(expireSession('expired'), true);
  assert.equal(getToken(), null);
  assert.equal(notified, 1);
});

test('late rejection from a previous login does not erase a new token', () => {
  setup();setToken('new-login');let notified = 0;
  window.addEventListener(SESSION_EXPIRED_EVENT, () => notified++);
  assert.equal(expireSession('old-login'), false);
  assert.equal(getToken(), 'new-login');
  assert.equal(notified, 0);
});

test('missing token can invalidate stale visible login state', () => {
  setup();let notified = false;
  window.addEventListener(SESSION_EXPIRED_EVENT, () => { notified = true; });
  assert.equal(expireSession(null), true);
  assert.equal(notified, true);
});

test('JWT expiry is read only for UI timing; malformed and mock tokens are ignored', () => {
  const encoded = Buffer.from(JSON.stringify({ exp: 2000000000 })).toString('base64url');
  assert.equal(tokenExpiresAt(`header.${encoded}.signature`), 2000000000000);
  for (const token of [null, '', 'mock.7', 'broken', 'a.b.c', `a.${Buffer.from('{"exp":"tomorrow"}').toString('base64url')}.c`]) {
    assert.equal(tokenExpiresAt(token), null);
  }
});
