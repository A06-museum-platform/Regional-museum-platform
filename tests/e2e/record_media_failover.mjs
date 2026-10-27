// Records real production image reads. Failures exist only in this isolated
// browser's routing; no credentials, database writes or provider changes.
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { execFileSync } from 'node:child_process';

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const base = process.env.E2E_BASE_URL || 'https://regional-museum-platform.pages.dev';
const work = resolve(process.env.MEDIA_DEMO_WORK_DIR || 'backups/media-failover-recording');
const output = resolve(process.env.MEDIA_DEMO_OUT || 'docs/demos');
await mkdir(work, { recursive: true });
await mkdir(output, { recursive: true });
const primaryOrigin = 'https://jrgyhvfpgppoarxwqhmk.supabase.co';
const r2Origin = 'https://pub-5f79a37728b6418db375cb056ccdd868.r2.dev';
const objectKey = 'aboriginal-painted-shield.jpg';
const primary = `${primaryOrigin}/storage/v1/object/public/museum-media/${objectKey}`;
const standby = `${r2Origin}/${objectKey}`;
const title = 'Aboriginal Painted Shield';
const scenes = {
  intro: ['THE MECHANISM', 'Supabase is the primary image store. R2 holds a mirrored copy with the same object key.'],
  normal: ['01 · NORMAL READ', 'The real API supplies a Supabase URL. The browser loads the primary image successfully.'],
  blocked: ['02 · IMAGE REQUEST FAILS', 'Only this browser blocks Supabase image requests. The application automatically retries the same object in R2.'],
  hanging: ['03 · PRIMARY REQUEST HANGS', 'No immediate error: the 10-second image deadline triggers the same R2 fallback automatically.'],
  recovered: ['04 · PRIMARY RESTORED', 'Remove the browser block and reload. A fresh image load uses Supabase again.'],
  outro: ['WHAT THE DEMO PROVES', 'Automatic image-read fallback works. The database and API remain online throughout this simulation.'],
};
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH || undefined });
const events = [];
const chapters = [];
const pageErrors = [];
let context;
let video;
let mode = 'normal';
let scene = 'intro';
let started;
let requestStarted = 0;
let hangElapsed = 0;
let videoPath;
const seconds = () => (Date.now() - started) / 1000;
try {
  context = await browser.newContext({ viewport: { width: 1920, height: 1080 },
    recordVideo: { dir: work, size: { width: 1920, height: 1080 } }, reducedMotion: 'reduce' });
  // Read-only guard. A fresh context has no cookies, storage or signed-in user.
  await context.route('**/api/**', route => ['GET', 'HEAD'].includes(route.request().method())
    ? route.continue() : route.abort());
  await context.route(`${primaryOrigin}/storage/**`, route => {
    if (mode === 'blocked') return route.abort('failed');
    if (mode === 'hanging') return; // Keep the browser request unresolved.
    return route.continue();
  });
  await context.addInitScript(({ scenes, title, objectKey }) => {
    document.addEventListener('DOMContentLoaded', () => {
      const key = new URLSearchParams(location.search).get('demo_scene') || 'intro';
      const [heading, caption] = scenes[key];
      const style = document.createElement('style');
      style.textContent = `
        body { padding-right: 450px !important; padding-bottom: 170px !important; }
        #demo-rail { position:fixed;right:0;top:0;bottom:0;width:450px;box-sizing:border-box;
          background:#15251f;color:#f7faf7;padding:36px 28px;z-index:2147483646;font:18px/1.5 system-ui; }
        #demo-rail .tag {color:#b9d97e;font-size:13px;letter-spacing:2px;font-weight:700;}
        #demo-rail h2 {font:600 30px/1.2 system-ui;margin:12px 0 26px;}
        .demo-box {border:1px solid #4b6255;border-radius:14px;padding:20px;margin:18px 0;background:#1e342a;}
        .demo-label {font-weight:650;font-size:20px;}.demo-url {font:13px/1.5 monospace;color:#c3cec7;overflow-wrap:anywhere;margin:10px 0;}
        .demo-state {font-size:18px;color:#d7dcca;min-height:28px;}
        #demo-object {font:15px/1.6 monospace;overflow-wrap:anywhere;color:#d4e7ae;}
        #demo-rendered {font-size:20px;font-weight:700;color:#b9df85;}
        #demo-caption {position:fixed;left:0;right:450px;bottom:0;box-sizing:border-box;background:#102019;
          color:white;padding:25px 46px;min-height:142px;z-index:2147483647;font:26px/1.42 system-ui;}
        #demo-caption b {display:block;font-size:14px;letter-spacing:2px;color:#b9d97e;margin-bottom:10px;}
        #demo-scope {position:absolute;bottom:28px;left:28px;right:28px;font-size:15px;color:#c9d2cc;border-top:1px solid #4b6255;padding-top:20px;}
        #demo-cover {position:fixed;left:0;top:0;right:450px;bottom:142px;background:#f4f6ed;
          z-index:2147483645;padding:130px 90px;box-sizing:border-box;color:#213426;font:24px/1.6 system-ui;}
        #demo-cover h1 {font:700 61px/1.15 system-ui;letter-spacing:-2px;margin:20px 0 32px;color:#213426;}
        #demo-cover .eyebrow {font-size:16px;letter-spacing:3px;font-weight:700;color:#526b32;}
        #demo-cover .flow {display:flex;align-items:center;gap:25px;margin:45px 0;font-size:23px;}
        #demo-cover .node {padding:24px 30px;border:1px solid #9eaf84;border-radius:16px;background:#fff;}
        #demo-cover small {display:block;color:#58654c;font-size:18px;margin-top:40px;}
      `;
      document.head.append(style);
      const rail = document.createElement('aside');
      rail.id = 'demo-rail';
      rail.innerHTML = `<div class="tag">PRESENTATION OVERLAY · LIVE NETWORK</div><h2>One image.<br>Two storage sources.</h2>
        <div class="demo-box"><div class="demo-label">1 · Supabase primary</div><div class="demo-url">jrgyhvfpgppoarxwqhmk.supabase.co</div><div id="demo-primary" class="demo-state">Waiting for request…</div></div>
        <div style="text-align:center;color:#b9d97e">on error / 10-second deadline ↓</div>
        <div class="demo-box"><div class="demo-label">2 · Cloudflare R2 backup</div><div class="demo-url">pub-5f79a37728b6418db375cb056ccdd868.r2.dev</div><div id="demo-r2" class="demo-state">Standby · no request yet</div></div>
        <div class="demo-box"><div class="demo-label">Same object key</div><div id="demo-object"></div><hr style="border:0;border-top:1px solid #4b6255;margin:18px 0"><div style="font-size:14px">ACTUAL RENDERED IMAGE SOURCE</div><div id="demo-rendered">Waiting for image…</div></div>
        <div id="demo-scope">Browser-only failure simulation.<br>Database + API stay online.<br>No cloud configuration is changed.</div>`;
      document.body.append(rail);
      document.getElementById('demo-object').textContent = objectKey;
      const lower = document.createElement('div');lower.id = 'demo-caption';
      lower.innerHTML = '<b></b><span></span>';
      lower.querySelector('b').textContent = heading;lower.querySelector('span').textContent = caption;
      document.body.append(lower);
      if (key === 'intro' || key === 'outro') {
        const cover = document.createElement('div');cover.id = 'demo-cover';
        cover.innerHTML = key === 'intro'
          ? `<div class="eyebrow">REGIONAL MUSEUM PLATFORM · LIVE DEMO</div><h1>Supabase image failover<br>with Cloudflare R2</h1><p>Keep a museum image visible when its primary storage request fails.</p><div class="flow"><div class="node">Supabase Storage<br><small style="margin:0">Primary image URL</small></div><span>→</span><div class="node">Browser image</div><span>←</span><div class="node">Cloudflare R2<br><small style="margin:0">Mirrored object key</small></div></div><small>Recorded on the deployed website. Captions and this network panel are presentation overlays.</small>`
          : `<div class="eyebrow">VERIFIED ON THE DEPLOYED APPLICATION</div><h1>Automatic image fallback.<br>No manual URL rewrite.</h1><p>✓ Primary request error → matching R2 object<br>✓ Primary request hangs → 10-second deadline → R2<br>✓ Unblock and reload → Supabase primary</p><small>Requires an existing R2 copy. Daily synchronization is not instant replication.<br>This is image-read resilience, not PostgreSQL or upload failover.</small>`;
        document.body.append(cover);
      }
      window.__demoUpdate = ({ source, text, ok }) => {
        const el = document.getElementById(source === 'primary' ? 'demo-primary' : 'demo-r2');
        el.textContent = text;el.style.color = ok ? '#b9df85' : '#f4c983';
      };
      setInterval(() => {
        const img = [...document.images].find(img => img.alt === title);
        const el = document.getElementById('demo-rendered');
        el.textContent = img?.complete && img.naturalWidth > 0
          ? (img.dataset.mediaFallback === 'true' ? 'Cloudflare R2 · loaded' : 'Supabase · loaded') : 'Image loading…';
      }, 150);
      window.__demoReady = true;
    });
  }, { scenes, title, objectKey });
  const page = await context.newPage();video = page.video();started = Date.now();
  const update = async (source, text, ok = false) => {
    await page.evaluate(state => window.__demoUpdate?.(state), { source, text, ok }).catch(() => {});
  };
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('request', request => {
    if (request.url() !== primary && request.url() !== standby) return;
    const source = request.url() === primary ? 'primary' : 'r2';
    if (source === 'primary') requestStarted = Date.now();
    events.push({ at: seconds(), scene, source, event: 'request', url: request.url() });
    void update(source, source === 'primary' && mode === 'hanging' ? 'Pending · waiting for 10s deadline…' : 'GET image · requested');
  });
  page.on('requestfailed', request => {
    if (request.url() !== primary) return;
    events.push({ at: seconds(), scene, source: 'primary', event: 'browser-request-failed', reason: request.failure()?.errorText });
    void update('primary', mode === 'hanging' ? '10s deadline · switched to R2' : 'Blocked in this demo browser');
  });
  page.on('response', response => {
    if (response.url() !== primary && response.url() !== standby) return;
    const source = response.url() === primary ? 'primary' : 'r2';
    events.push({ at: seconds(), scene, source, event: 'response', status: response.status() });
    void update(source, `HTTP ${response.status()} · image received`, response.ok());
  });
  const goto = async key => {
    scene = key;chapters.push({ scene: key, start: seconds(), caption: scenes[key][1] });
    await page.goto(`${base}/collections/aboriginal-painted-shield-6?demo_scene=${key}`, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => window.__demoReady === true);
  };
  const imageLoaded = async source => {
    const expected = source === 'primary' ? primary : standby;
    await page.waitForFunction(({ title, expected }) => {
      const img = [...document.images].find(img => img.alt === title);
      return img?.src === expected && img.complete && img.naturalWidth > 0;
    }, { title, expected }, { timeout: 45000 });
    assert.equal(await page.getByAltText(title, { exact: true }).getAttribute('data-media-fallback'), source === 'r2' ? 'true' : 'false');
    const response = events.findLast(event => event.scene === scene && event.source === source && event.event === 'response');
    assert.ok(response && response.status === 200, 'Expected a real HTTP 200 image response');
    events.push({ at: seconds(), scene, source, event: 'rendered-and-decoded' });
    if (source === 'r2' && mode === 'hanging') {
      hangElapsed = Date.now() - requestStarted;
      assert.ok(hangElapsed >= 9500 && hangElapsed < 20000, `Unexpected deadline: ${hangElapsed}ms`);
      await update('primary', '10s deadline · switched to R2');
    }
    if (source === 'r2' && mode === 'blocked') {
      assert.ok(events.some(event => event.scene === scene && event.source === 'primary' && event.event === 'browser-request-failed'));
      await update('primary', 'Blocked in this demo browser');
    }
    await update(source, 'HTTP 200 · image loaded', true);
    await page.waitForFunction(label => document.getElementById('demo-rendered')?.textContent.includes(label),
      source === 'r2' ? 'Cloudflare R2 · loaded' : 'Supabase · loaded');
  };
  await goto('intro');await imageLoaded('primary');await page.waitForTimeout(8000);
  await goto('normal');await imageLoaded('primary');await page.waitForTimeout(10000);
  mode = 'blocked';await goto('blocked');await imageLoaded('r2');
  await page.screenshot({ path: join(work, 'r2-fallback.png') });await page.waitForTimeout(12000);
  mode = 'hanging';await goto('hanging');await imageLoaded('r2');await page.waitForTimeout(8000);
  mode = 'normal';await goto('recovered');await imageLoaded('primary');await page.waitForTimeout(10000);
  await goto('outro');await imageLoaded('primary');await page.waitForTimeout(9000);
  assert.deepEqual(pageErrors, []);
  await page.screenshot({ path: join(work, 'outro.png') });
  const duration = seconds();
  await context.close();context = null;videoPath = await video.path();
  const evidence = {
    recordedAt: new Date().toISOString(), website: base, scope: 'Browser-only image failure simulation; no provider outage or data writes',
    objectKey, durationSeconds: duration, observedTimeoutMs: hangElapsed, chapters, events, pageErrors,
  };
  await writeFile(join(output, 'supabase-r2-failover-evidence.json'), JSON.stringify(evidence, null, 2) + '\n');
  execFileSync(process.env.FFMPEG_BIN || 'ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-i', videoPath,
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
    '-an', join(output, 'supabase-r2-failover.mp4')]);
  const posterAt = events.find(event => event.scene === 'blocked' && event.event === 'rendered-and-decoded').at + 2;
  execFileSync(process.env.FFMPEG_BIN || 'ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-ss', String(posterAt),
    '-i', join(output, 'supabase-r2-failover.mp4'), '-frames:v', '1', '-q:v', '3', join(output, 'supabase-r2-failover-poster.jpg')]);
  const probe = JSON.parse(execFileSync(process.env.FFPROBE_BIN || 'ffprobe', ['-v', 'error', '-show_entries',
    'format=duration,size:stream=codec_name,width,height,r_frame_rate', '-of', 'json', join(output, 'supabase-r2-failover.mp4')], { encoding: 'utf8' }));
  evidence.video = probe;
  await writeFile(join(output, 'supabase-r2-failover-evidence.json'), JSON.stringify(evidence, null, 2) + '\n');
  const timecode = seconds => {
    const ms = Math.round(seconds * 1000);
    return [Math.floor(ms / 3600000), Math.floor(ms / 60000) % 60, Math.floor(ms / 1000) % 60]
      .map(n => String(n).padStart(2, '0')).join(':') + ',' + String(ms % 1000).padStart(3, '0');
  };
  const subtitles = chapters.map((chapter, i) => `${i + 1}\n${timecode(chapter.start)} --> ${timecode(chapters[i + 1]?.start ?? Number(probe.format.duration))}\n${chapter.caption}\n`).join('\n');
  await writeFile(join(output, 'supabase-r2-failover.srt'), subtitles);
  console.log(JSON.stringify({ video: join(output, 'supabase-r2-failover.mp4'), durationSeconds: duration,
    observedTimeoutMs: hangElapsed, scenarios: ['Supabase 200', 'browser error → real R2 200', '10-second hang → real R2 200', 'unblock + reload → Supabase 200'], pageErrors }));
} finally {
  if (context) await context.close();
  await browser.close();
}
