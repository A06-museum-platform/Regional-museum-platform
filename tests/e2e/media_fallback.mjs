// Run against Vite --mode production; requests to both storage providers are
// intercepted in an isolated browser. No cloud content or credentials change.
import assert from 'node:assert/strict';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const base = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';
const primary = 'https://jrgyhvfpgppoarxwqhmk.supabase.co/storage/v1/object/public/museum-media/browser-drill.png';
const standby = 'https://pub-5f79a37728b6418db375cb056ccdd868.r2.dev/browser-drill.png';
const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1sAAAAASUVORK5CYII=', 'base64');
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH || undefined });
const results = [];
try {
  for (const scenario of ['primary', 'error', 'timeout', 'both-error', 'both-timeout', 'lazy', 'source-change', 'hide']) {
    const context = await browser.newContext();
    const page = await context.newPage();
    const hits = [];
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.clock.install();
    await context.route('https://**/*', async route => {
      const url = route.request().url();
      hits.push(url);
      if (scenario === 'source-change' && url === primary + '?new=1') {
        return route.fulfill({ contentType: 'image/png', body: png });
      }
      if (url.startsWith(primary)) {
        if (['timeout', 'both-timeout', 'lazy'].includes(scenario)) return; // Hold the request open.
        if (['error', 'both-error', 'hide', 'source-change'].includes(scenario)) return route.abort();
      }
      if (url === standby) {
        if (scenario === 'both-timeout') return;
        if (['both-error', 'hide', 'source-change'].includes(scenario)) return route.abort();
      }
      return route.fulfill({ contentType: 'image/png', body: png });
    });
    const query = new URLSearchParams({ src: primary, next: primary + '?new=1' });
    if (scenario === 'lazy') query.set('lazy', '1');
    if (scenario === 'hide') query.set('hide', '1');
    await page.goto(`${base}/tests/browser/media-image.html?${query}`, { waitUntil: 'domcontentloaded' });
    await page.getByRole('button', { name: 'Change source' }).waitFor();
    const image = page.locator('img');
    const waitLoaded = async url => {
      await page.waitForFunction(expected => {
        const img = document.querySelector('img');
        return img?.src === expected && img.complete && img.naturalWidth > 0;
      }, url);
    };
    if (scenario === 'lazy') {
      await image.waitFor();
      await page.clock.runFor(11000);
      assert.equal(hits.includes(standby), false, 'offscreen lazy image must not time out');
      await image.scrollIntoViewIfNeeded();
      await page.waitForFunction(() => {
        const bounds = document.querySelector('img').getBoundingClientRect();
        return bounds.top >= 0 && bounds.top < window.innerHeight;
      });
      await page.waitForTimeout(100); // Let IntersectionObserver start the timer.
      await page.clock.runFor(11000);
      await waitLoaded(standby);
    } else if (scenario === 'timeout' || scenario === 'both-timeout') {
      await image.waitFor();
      await page.waitForTimeout(100);
      await page.clock.runFor(11000);
      if (scenario === 'both-timeout') {
        await page.waitForFunction(() => document.querySelector('img')?.dataset.mediaFallback === 'true');
        await page.clock.runFor(11000);
        await page.getByRole('img', { name: 'Browser drill image' }).filter({ hasText: 'Image unavailable' }).waitFor();
      } else await waitLoaded(standby);
    } else if (['both-error', 'source-change'].includes(scenario)) {
      await page.getByText('Image unavailable').waitFor();
      if (scenario === 'source-change') {
        // A new source starts at Supabase even after both previous attempts fail.
        await page.getByRole('button', { name: 'Change source' }).click();
        await waitLoaded(primary + '?new=1');
        assert.equal(await image.getAttribute('data-media-fallback'), 'false');
        assert.ok(hits.some(url => url === primary + '?new=1'));
      }
    } else if (scenario === 'hide') {
      await page.waitForFunction(() => !document.querySelector('img') && !document.querySelector('[role=img]'));
      await page.waitForTimeout(100);
      assert.ok(hits.includes(standby));
    } else {
      await waitLoaded(scenario === 'primary' ? primary : standby);
      await page.clock.runFor(22000);
      await waitLoaded(scenario === 'primary' ? primary : standby);
    }
    if (scenario === 'primary') assert.equal(hits.includes(standby), false);
    assert.deepEqual(errors, []);
    // Neither failed provider is retried in a loop.
    if (scenario !== 'source-change') assert.ok(hits.filter(url => url === standby).length <= 1);
    results.push(scenario);
    console.log(`PASS ${scenario}`);
    await context.close();
  }
} finally {
  await browser.close();
}
console.log(`${results.length} real-browser image fallback scenarios passed`);
