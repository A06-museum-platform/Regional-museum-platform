// Full-app record selection and cover regressions. All API calls are intercepted.
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH || undefined });
const base = process.env.E2E_BASE_URL || 'http://127.0.0.1:5179';
const fixture = await readFile('docs/demos/supabase-r2-failover-poster.jpg');
let releaseOld, releaseUpload, releaseRecords;
try {
  const context = await browser.newContext();
  await context.addInitScript(() => localStorage.setItem('sarhn.access_token', 'test-session'));
  const page = await context.newPage();
  const errors = [];page.on('pageerror', e => errors.push(e.message));
  const calls = [];let oldHeld = false;let uploaded = false;let cover = false;let recordsFailed = false;let recordsHeld = false;
  const image = (id, url) => ({ media_id: id, url, media_type: 'image', is_primary: cover, storage: 'supabase' });
  const json = (route, status, data) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(data) });
  await context.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (!path.startsWith('/api/')) return route.continue();
    calls.push([route.request().method(), path]);
    if (path === '/api/auth/me') return json(route, 200, { id: 7, full_name: 'Test Staff', role: 'staff' });
    if (path === '/api/staff/collection-items') {
      if (recordsHeld) await new Promise(resolve => { releaseRecords = resolve; });
      return json(route, 200, { items: [{ id: 17, title: 'Collection with same numeric ID', status: 'published' }] });
    }
    if (path === '/api/staff/exhibitions') return recordsFailed
      ? json(route, 503, { detail: 'Records unavailable' })
      : json(route, 200, { items: [{ id: 17, title: 'Telegraph', status: 'published' }, { id: 2, title: 'Mine', status: 'draft' }] });
    if (path === '/api/staff/events') return json(route, 200, { items: [] });
    if (path === '/api/staff/exhibitions/2/media') {
      oldHeld = true;await new Promise(resolve => { releaseOld = resolve; });
      return json(route, 200, [image(22, 'https://example.invalid/old-owner.jpg')]);
    }
    if (path === '/api/staff/exhibitions/17/media') {
      if (route.request().method() === 'POST') {
        assert.equal(route.request().headers().authorization, 'Bearer test-session');
        await new Promise(resolve => { releaseUpload = resolve; });uploaded = true;
        return json(route, 201, { media: image(77, 'https://example.invalid/telegraph.jpg') });
      }
      return json(route, 200, uploaded ? [image(77, 'https://example.invalid/telegraph.jpg')] : []);
    }
    if (path === '/api/staff/media/77/primary') {
      assert.equal(route.request().method(), 'PATCH');cover = true;
      return json(route, 200, image(77, 'https://example.invalid/telegraph.jpg'));
    }
    return json(route, 200, []);
  });
  await page.goto(base + '/staff/media');
  await page.getByLabel('Record', { exact: true }).waitFor();
  assert.equal(await page.getByRole('button', { name: 'Upload images', exact: true }).count(), 0);
  assert.ok(!calls.some(([,path]) => path.endsWith('/media')));
  console.log('PASS no guessed default upload target');

  await page.getByLabel('Record type', { exact: true }).selectOption('exhibition');
  await page.getByRole('option', { name: 'Mine — ID 2 (Draft)', exact: true }).waitFor({ state: 'attached' });
  await page.getByLabel('Record', { exact: true }).selectOption('2');
  await page.getByRole('heading', { name: 'Images for Mine' }).waitFor();
  await page.getByText('Draft — images will not appear publicly until this record is published.', { exact: false }).waitFor();
  while (!oldHeld) await page.waitForTimeout(20);
  await page.getByLabel('Record', { exact: true }).selectOption('17');
  await page.getByRole('heading', { name: 'Images for Telegraph' }).waitFor();
  await page.getByRole('button', { name: 'Upload images', exact: true }).waitFor();
  releaseOld();await page.waitForTimeout(100);
  assert.equal(await page.locator('img[src*="old-owner"]').count(), 0);
  console.log('PASS immediate title/ID selection; stale previous-media response ignored');

  await page.locator('input[type=file]').setInputFiles({ name: 'telegraph.jpeg', mimeType: 'image/jpeg', buffer: fixture });
  while (!releaseUpload) await page.waitForTimeout(20);
  assert.equal(await page.getByLabel('Record type', { exact: true }).isDisabled(), true);
  assert.equal(await page.getByLabel('Record', { exact: true }).isDisabled(), true);
  releaseUpload();await page.getByText('Image ID: 77', { exact: true }).waitFor();
  await page.getByRole('button', { name: 'Use as cover' }).click();
  await page.getByText('Public cover', { exact: true }).waitFor();
  assert.ok(calls.some(([method,path]) => method === 'POST' && path === '/api/staff/exhibitions/17/media'));
  assert.ok(calls.some(([method,path]) => method === 'PATCH' && path === '/api/staff/media/77/primary'));
  assert.ok(!calls.some(([method,path]) => method === 'POST' && path !== '/api/staff/exhibitions/17/media'));
  console.log('PASS upload stays on named record; busy selection locked; cover uses image ID');

  recordsHeld = true;
  await page.getByLabel('Record type', { exact: true }).selectOption('collection-item');
  await page.getByRole('status').filter({ hasText: 'Loading records' }).waitFor();
  assert.equal(await page.getByRole('region', { name: 'Selected record media' }).count(), 0);
  assert.equal(await page.getByRole('button', { name: 'Upload images', exact: true }).count(), 0);
  while (!releaseRecords) await page.waitForTimeout(20);
  recordsHeld = false;releaseRecords();
  await page.getByRole('option', { name: /Collection with same numeric ID/ }).waitFor({ state: 'attached' });
  assert.equal(await page.getByLabel('Record', { exact: true }).inputValue(), '');
  await page.getByLabel('Record', { exact: true }).selectOption('17');
  await page.getByRole('heading', { name: 'Images for Collection with same numeric ID' }).waitFor();
  console.log('PASS type change clears ID even with shared number; no stale uploader while loading');

  await page.goto(base + '/staff/media?type=exhibition&id=999');
  await page.getByRole('alert').filter({ hasText: 'no longer available' }).waitFor();
  assert.equal(await page.getByRole('button', { name: 'Upload images', exact: true }).count(), 0);
  await page.goto(base + '/staff/media?type=exhibition&id=17');
  await page.getByRole('heading', { name: 'Images for Telegraph' }).waitFor();
  console.log('PASS missing/deleted ID blocked; direct record link resolves stable ID');

  recordsFailed = true;await page.goto(base + '/staff/media?type=exhibition&id=17');
  await page.getByRole('alert').filter({ hasText: 'Records unavailable' }).waitFor();
  assert.equal(await page.getByRole('button', { name: 'Upload images', exact: true }).count(), 0);
  recordsFailed = false;await page.getByRole('button', { name: 'Retry loading records' }).click();
  await page.getByRole('heading', { name: 'Images for Telegraph' }).waitFor();
  await page.getByLabel('Record type', { exact: true }).selectOption('event');
  await page.getByText('No records of this type are available.').waitFor();
  assert.equal(await page.getByRole('button', { name: 'Upload images', exact: true }).count(), 0);
  assert.deepEqual(errors, []);
  console.log('PASS record-list errors and empty lists block uploads; retry recovers');
} finally {
  releaseOld?.();releaseUpload?.();releaseRecords?.();await browser.close();
}
