// Isolated full-app session regression: every API call is intercepted. No
// credentials, real accounts, database writes or cloud uploads are involved.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const base = process.env.E2E_BASE_URL || 'http://127.0.0.1:5179';
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH || undefined });
const key = 'sarhn.access_token';
const user = { id: 7, role: 'staff', full_name: 'Session Test Staff', email: 'staff@example.invalid' };
const jwt = seconds => `test.${Buffer.from(JSON.stringify({ sub: '7', exp: Math.floor(Date.now() / 1000) + seconds })).toString('base64url')}.test`;
const fixture = await readFile('docs/demos/supabase-r2-failover-poster.jpg');
try {
  for (const scenario of ['valid-upload', 'list-401-relogin', 'upload-401', 'expiry', 'other-tab-logout', 'list-503-retry', 'list-403', 'old-401-new-login', 'old-me-401-new-login']) {
    const token = jwt(scenario === 'expiry' ? 3 : 3600);
    const freshToken = jwt(7200);
    const context = await browser.newContext();
    await context.addInitScript(({ key, token }) => localStorage.setItem(key, token), { key, token });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    let lists = 0;
    let posts = 0;
    let retrySucceeded = false;
    let held = false;
    let release;
    const json = (route, status, data) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) });
    await context.route('**/api/**', async route => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      // Vite serves JavaScript from /src/api/ too; those are not API requests.
      if (!path.startsWith('/api/')) return route.continue();
      const bearer = request.headers().authorization;
      if (path === '/api/auth/login') return json(route, 200, { user, access_token: freshToken });
      if (path === '/api/auth/me') {
        if (scenario === 'old-me-401-new-login' && !held && bearer === `Bearer ${token}`) {
          held = true;
          await new Promise(resolve => { release = resolve; });
          return json(route, 401, { detail: 'Invalid or expired token', code: 'AUTH_INVALID' });
        }
        return json(route, 200, user);
      }
      if (path === '/api/staff/collection-items/6/media' && request.method() === 'GET') {
        lists++;
        if (scenario === 'old-401-new-login' && lists === 1) {
          held = true;
          await new Promise(resolve => { release = resolve; });
          return json(route, 401, { detail: 'Not authenticated', code: 'AUTH_REQUIRED' });
        }
        if (scenario === 'list-401-relogin' && lists === 1) return json(route, 401, { detail: 'Not authenticated', code: 'AUTH_REQUIRED' });
        if (scenario === 'list-503-retry' && !retrySucceeded) return json(route, 503, { detail: 'Temporary media service failure' });
        if (scenario === 'list-403') return json(route, 403, { detail: 'Staff role required', code: 'FORBIDDEN' });
        assert.ok(bearer === `Bearer ${token}` || bearer === `Bearer ${freshToken}`);
        return json(route, 200, []);
      }
      if (path === '/api/staff/collection-items/6/media' && request.method() === 'POST') {
        posts++;
        assert.equal(bearer, `Bearer ${token}`);
        if (scenario === 'upload-401') return json(route, 401, { detail: 'Invalid or expired token', code: 'AUTH_INVALID' });
        assert.ok(request.postDataBuffer().length > fixture.length);
        return json(route, 201, { media: { media_id: 99, url: 'https://example.invalid/test.jpg', media_type: 'image', storage: 'supabase' } });
      }
      return json(route, 200, []);
    });
    const ended = async () => {
      await page.waitForURL('**/signin');
      await page.getByRole('status').filter({ hasText: 'Your session ended' }).waitFor();
      assert.equal(await page.evaluate(key => localStorage.getItem(key), key), null);
    };
    const relogin = async () => {
      await page.getByLabel('Email', { exact: true }).fill('staff@example.invalid');
      await page.getByLabel('Password', { exact: true }).fill('test-only');
      await page.getByRole('main').getByRole('button', { name: 'Sign in', exact: true }).click();
      await page.waitForURL('**/staff/media');
      await page.waitForFunction(() => [...document.querySelectorAll('button')].some(b => b.textContent === 'Upload images' && !b.disabled));
    };
    try {
      await page.goto(`${base}/staff/media`, { waitUntil: 'domcontentloaded' });
      const upload = page.getByRole('button', { name: 'Upload images', exact: true });
      if (scenario === 'list-401-relogin') {
        await ended();await relogin();
        assert.equal(await page.evaluate(key => localStorage.getItem(key), key), freshToken);
      } else if (scenario === 'old-me-401-new-login') {
        while (!held) await page.waitForTimeout(20);
        const other = await context.newPage();await other.goto(`${base}/signin`);
        await other.evaluate(({ key, freshToken }) => localStorage.setItem(key, freshToken), { key, freshToken });
        await page.getByRole('heading', { name: 'Media library' }).waitFor();
        release();await page.waitForTimeout(250);
        assert.equal(await page.evaluate(key => localStorage.getItem(key), key), freshToken);
        assert.ok(page.url().endsWith('/staff/media'));
      } else if (scenario === 'old-401-new-login') {
        while (!held) await page.waitForTimeout(20);
        const other = await context.newPage();await other.goto(`${base}/signin`);
        await other.evaluate(key => localStorage.removeItem(key), key);
        await ended();await relogin();release();await page.waitForTimeout(250);
        assert.equal(await page.evaluate(key => localStorage.getItem(key), key), freshToken);
        assert.ok(page.url().endsWith('/staff/media'));
      } else if (scenario === 'expiry') {
        await ended();assert.equal(posts, 0);
      } else if (scenario === 'other-tab-logout') {
        await upload.waitFor();const other = await context.newPage();await other.goto(`${base}/signin`);
        await other.evaluate(key => localStorage.removeItem(key), key);await ended();
      } else if (scenario === 'list-503-retry') {
        await page.getByRole('alert').filter({ hasText: 'Temporary media service failure' }).waitFor();
        assert.equal(await upload.isDisabled(), true);
        retrySucceeded = true;
        await page.getByRole('button', { name: 'Retry loading media' }).click();
        await page.waitForFunction(() => [...document.querySelectorAll('button')].some(b => b.textContent === 'Upload images' && !b.disabled));
        assert.equal(await page.evaluate(key => localStorage.getItem(key), key), token);
      } else if (scenario === 'list-403') {
        await page.getByRole('alert').filter({ hasText: 'Staff role required' }).waitFor();
        assert.equal(await page.evaluate(key => localStorage.getItem(key), key), token);
        assert.equal(await upload.isDisabled(), true);
      } else {
        await page.waitForFunction(() => [...document.querySelectorAll('button')].some(b => b.textContent === 'Upload images' && !b.disabled));
        await page.locator('input[type=file]').setInputFiles({ name: 'test.jpeg', mimeType: 'image/jpeg', buffer: fixture });
        if (scenario === 'upload-401') await ended();
        else {
          await page.waitForFunction(() => [...document.querySelectorAll('button')].some(b => b.textContent === 'Upload images' && !b.disabled));
          assert.equal(posts, 1);
        }
      }
      assert.deepEqual(errors, []);
      console.log(`PASS ${scenario}`);
    } catch (error) {
      console.error(JSON.stringify({ scenario, url: page.url(), lists, posts, pageErrors: errors,
        screen: (await page.locator('body').innerText()).slice(0, 1200) }));
      throw error;
    } finally {
      release?.();await context.close();
    }
  }
} finally {
  await browser.close();
}
