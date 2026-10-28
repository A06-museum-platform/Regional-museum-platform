// Read-only checks for restored public catalog photos. Requires the two
// catalogs to be present; never logs in, edits records or uploads files.
import assert from 'node:assert/strict';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const base = process.env.E2E_BASE_URL || 'http://127.0.0.1:5179';
const api = process.env.API_BASE_URL || 'https://regional-museum-platform-api.onrender.com/api';
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH || undefined });
const supabase = 'https://jrgyhvfpgppoarxwqhmk.supabase.co';
const r2 = 'https://pub-5f79a37728b6418db375cb056ccdd868.r2.dev';
try {
  const context = await browser.newContext();
  const collections = await (await context.request.get(`${api}/collection-items?page_size=100`)).json();
  const exhibitions = await (await context.request.get(`${api}/exhibitions?page_size=100`)).json();
  const find = title => {
    const item = collections.items.find(item => item.title === title);
    assert.ok(item, `Missing public record: ${title}`);
    return item;
  };
  const shield = find('Aboriginal Painted Shield');
  const necklace = find('Kula Trading Necklace');
  const current = find('Malachite matrix, Burra');
  assert.match(shield.image_url, /\/aboriginal-painted-shield\.jpg$/);
  assert.match(necklace.image_url, /\/Kula%20Trading%20Necklace\.png$/);
  assert.equal(shield.category, null); // Source snapshot does not classify it.
  assert.ok(exhibitions.items.some(item => item.title === 'Stories of South Australia' && item.hero_image_url));
  assert.ok(exhibitions.items.some(item => item.title === 'Colonial Mining & the Overland Telegraph'));
  console.log(`Public catalogs: ${collections.total} collections, ${exhibitions.total} exhibitions`);
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const waitLoaded = async (alt, origin) => {
    await page.waitForFunction(({ alt, origin }) => {
      const img = [...document.images].find(img => img.alt === alt);
      return img?.src.startsWith(origin) && img.complete && img.naturalWidth > 0;
    }, { alt, origin });
  };
  await page.goto(`${base}/collections/${shield.slug}`);
  await waitLoaded(shield.title, supabase);
  await page.getByRole('heading', { name: 'Other collection records' }).waitFor();
  assert.equal(await page.locator('a[href*="category=null"], a[href*="gallery=null"]').count(), 0);
  console.log('PASS restored detail photo and missing classification');
  await context.route(`${supabase}/storage/**`, route => route.abort());
  await page.reload();
  await waitLoaded(shield.title, r2);
  console.log('PASS actual detail Supabase-to-R2 fallback');
  await page.goto(`${base}/collections/${necklace.slug}`);
  await waitLoaded(necklace.title, r2);
  console.log('PASS escaped filename fallback');
  await context.route(`${r2}/**`, route => route.abort());
  await page.reload();
  await page.getByText('Image unavailable', { exact: true }).waitFor();
  console.log('PASS both providers unavailable');
  await context.unroute(`${supabase}/storage/**`);
  await context.unroute(`${r2}/**`);
  await page.goto(`${base}/collections/${current.slug}`);
  await page.getByRole('heading', { name: current.title, exact: true }).waitFor();
  if (current.image_url) {
    await waitLoaded(current.title, new URL(current.image_url).origin);
    console.log('PASS current catalog photo preserved');
  } else {
    await page.getByRole('img', { name: `Placeholder image for ${current.title}`, exact: true }).waitFor();
    console.log('PASS current catalog no-photo placeholder preserved');
  }
  assert.deepEqual(errors, []);
  await context.close();
} finally {
  await browser.close();
}
