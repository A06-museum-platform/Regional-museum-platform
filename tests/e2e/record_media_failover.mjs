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
  intro: ['THE MECHANISM', 'Supabase serves the primary image.\nR2 holds a copy with the same file key.'],
  normal: ['01 · NORMAL READ', 'The API returns a Supabase URL.\nThe browser loads the primary image.'],
  blocked: ['02 · IMAGE REQUEST FAILS', 'Supabase images are blocked in this browser.\nThe app automatically loads the R2 copy.'],
  hanging: ['03 · PRIMARY REQUEST HANGS', 'This image request is held open.\nAfter 10 seconds, the app switches to R2.'],
  recovered: ['04 · PRIMARY RESTORED', 'Remove the browser block and reload.\nThe image loads from Supabase again.'],
  outro: ['WHAT THE DEMO PROVES', 'Only image requests were interrupted.\nThe database and API stayed online.'],
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
  // Wake a sleeping free-tier API before starting the video, so a hosting cold
  // start does not leave the presentation on its opening slide for a minute.
  const warmup = await browser.newContext();
  try {
    const api = process.env.API_BASE_URL || 'https://regional-museum-platform-api.onrender.com/api';
    const response = await warmup.request.get(`${api}/collection-items/aboriginal-painted-shield-6`, { timeout: 120000 });
    assert.ok(response.ok(), `Public demo record unavailable: HTTP ${response.status()}`);
    const item = await response.json();
    assert.equal(item.image_url, primary, 'Demo record must retain its real Supabase image URL');
  } finally {
    await warmup.close();
  }
  // Capture a tighter 720p composition and export to 1080p. Important text is
  // 22–24 CSS px here (33–36 px in the final video), not tiny full-page text.
  context = await browser.newContext({ viewport: { width: 1280, height: 720 },
    recordVideo: { dir: work, size: { width: 1280, height: 720 } }, reducedMotion: 'reduce' });
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
        body { padding-right:400px !important;padding-bottom:150px !important; }
        #root header,#root footer,#root nav,#root table,#root [class*="related"],
        #root [class*="actions"],#root [class*="pills"] { display:none !important; }
        #root main { padding:24px 32px !important;max-width:none !important; }
        .demo-live-layout { display:flex !important;flex-direction:column !important;gap:12px !important; }
        .demo-live-layout > div:first-child { height:320px !important;width:100% !important; }
        .demo-live-layout h1 { font-size:25px !important;line-height:1.2 !important;margin:0 0 8px !important; }
        .demo-live-layout p { font-size:18px !important;line-height:1.4 !important;max-width:none !important;margin:0 !important; }
        #demo-rail { position:fixed;right:0;top:0;bottom:0;width:400px;box-sizing:border-box;
          background:#15251f;color:#f7faf7;padding:22px;z-index:2147483646;font:20px/1.35 system-ui; }
        #demo-rail .tag {color:#b9d97e;font-size:13px;letter-spacing:1px;font-weight:700;}
        #demo-rail h2 {font:600 29px/1.15 system-ui;margin:10px 0 18px;}
        .demo-box {border:1px solid #4b6255;border-radius:12px;padding:14px;margin:12px 0;background:#1e342a;}
        .demo-label {font-weight:650;font-size:23px;}.demo-url {display:none;}
        .demo-state {font-size:24px;color:#d7dcca;min-height:30px;margin-top:10px;}
        #demo-object {font:18px/1.4 monospace;overflow-wrap:anywhere;color:#d4e7ae;margin-top:10px;}
        #demo-rendered {font-size:24px;font-weight:700;color:#b9df85;}
        #demo-caption {position:fixed;left:0;right:400px;bottom:0;box-sizing:border-box;background:#102019;
          color:white;padding:18px 28px;min-height:132px;z-index:2147483647;font:24px/1.35 system-ui;}
        #demo-caption span {white-space:pre-line;}
        #demo-caption b {display:block;font-size:17px;letter-spacing:1px;color:#b9d97e;margin-bottom:8px;}
        #demo-scope {position:absolute;bottom:20px;left:22px;right:22px;font-size:17px;line-height:1.4;color:#c9d2cc;border-top:1px solid #4b6255;padding-top:14px;}
        #demo-cover {position:fixed;left:0;top:0;right:400px;bottom:132px;background:#f4f6ed;
          z-index:2147483645;padding:48px 40px;box-sizing:border-box;color:#213426;font:23px/1.45 system-ui;}
        #demo-cover h1 {font:700 43px/1.12 system-ui;letter-spacing:-1px;margin:18px 0 24px;color:#213426;}
        #demo-cover p {font-size:22px;line-height:1.45;margin:12px 0;}
        #demo-cover .eyebrow {font-size:16px;letter-spacing:1px;font-weight:700;color:#526b32;}
        #demo-cover .flow {display:flex;align-items:center;gap:16px;margin:25px 0;font-size:22px;}
        #demo-cover .node {padding:16px;border:1px solid #9eaf84;border-radius:12px;background:#fff;}
        #demo-cover small {display:block;color:#46523e;font-size:19px;margin-top:24px;}
      `;
      document.head.append(style);
      const rail = document.createElement('aside');
      rail.id = 'demo-rail';
      rail.innerHTML = `<div class="tag">PRESENTATION VIEW · LIVE REQUESTS</div><h2>One image.<br>Two sources.</h2>
        <div class="demo-box"><div class="demo-label">1 · Supabase primary</div><div class="demo-url">jrgyhvfpgppoarxwqhmk.supabase.co</div><div id="demo-primary" class="demo-state">Waiting for request…</div></div>
        <div style="text-align:center;color:#b9d97e;font-size:20px">Error or 10s timeout ↓</div>
        <div class="demo-box"><div class="demo-label">2 · Cloudflare R2 backup</div><div class="demo-url">pub-5f79a37728b6418db375cb056ccdd868.r2.dev</div><div id="demo-r2" class="demo-state">Standby · no request yet</div></div>
        <div class="demo-box"><div class="demo-label">Same file key</div><div id="demo-object"></div><hr style="border:0;border-top:1px solid #4b6255;margin:14px 0"><div style="font-size:17px;margin-bottom:8px">IMAGE LOADED FROM</div><div id="demo-rendered">Waiting for image…</div></div>
        <div id="demo-scope">Browser-only simulation.<br>Database + API stay online.</div>`;
      document.body.append(rail);
      document.getElementById('demo-object').textContent = objectKey;
      const lower = document.createElement('div');lower.id = 'demo-caption';
      lower.innerHTML = '<b></b><span></span>';
      lower.querySelector('b').textContent = heading;lower.querySelector('span').textContent = caption;
      document.body.append(lower);
      if (key === 'intro' || key === 'outro') {
        const cover = document.createElement('div');cover.id = 'demo-cover';
        cover.innerHTML = key === 'intro'
          ? `<div class="eyebrow">REGIONAL MUSEUM PLATFORM · LIVE DEMO</div><h1>Supabase image failover<br>with Cloudflare R2</h1><p>A backup source for museum images.</p><div class="flow"><div class="node">Supabase<br><small style="margin:0">Primary</small></div><span>→</span><div class="node">Browser</div><span>←</span><div class="node">Cloudflare R2<br><small style="margin:0">Backup copy</small></div></div><small>Real deployed app. Presentation overlays explain the requests.</small>`
          : `<div class="eyebrow">VERIFIED ON THE LIVE WEBSITE</div><h1>Automatic fallback.<br>No manual URL change.</h1><p>✓ Image error → R2 copy<br>✓ Request hangs → 10s timeout → R2<br>✓ Unblock + reload → Supabase</p><small>R2 needs an existing mirrored copy.<br>Daily sync is not instant replication.<br>Database and upload recovery are separate.</small>`;
        document.body.append(cover);
      }
      window.__demoUpdate = ({ source, text, ok }) => {
        const el = document.getElementById(source === 'primary' ? 'demo-primary' : 'demo-r2');
        el.textContent = text;el.style.color = ok ? '#b9df85' : '#f4c983';
      };
      setInterval(() => {
        const img = [...document.images].find(img => img.alt === title);
        // Focus only this recording's view; the deployed site's CSS is untouched.
        img?.parentElement?.parentElement?.classList.add('demo-live-layout');
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
    void update(source, source === 'primary' && mode === 'hanging' ? 'Waiting · 10s timeout' : 'Image requested…');
  });
  page.on('requestfailed', request => {
    if (request.url() !== primary) return;
    events.push({ at: seconds(), scene, source: 'primary', event: 'browser-request-failed', reason: request.failure()?.errorText });
    void update('primary', mode === 'hanging' ? '10s timeout → R2' : 'Blocked (demo)');
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
      await update('primary', '10s timeout → R2');
    }
    if (source === 'r2' && mode === 'blocked') {
      assert.ok(events.some(event => event.scene === scene && event.source === 'primary' && event.event === 'browser-request-failed'));
      await update('primary', 'Blocked (demo)');
    }
    await update(source, 'HTTP 200 · loaded', true);
    await page.waitForFunction(label => document.getElementById('demo-rendered')?.textContent.includes(label),
      source === 'r2' ? 'Cloudflare R2 · loaded' : 'Supabase · loaded');
    const readable = await page.evaluate(() => {
      const caption = document.getElementById('demo-caption');
      const scope = document.getElementById('demo-scope');
      const boxes = [...document.querySelectorAll('.demo-box')];
      const cover = document.getElementById('demo-cover');
      return {
        captionFits: caption.scrollHeight <= caption.clientHeight,
        railFits: boxes.every(box => box.getBoundingClientRect().bottom <= scope.getBoundingClientRect().top - 4),
        coverFits: !cover || cover.scrollHeight <= cover.clientHeight,
      };
    });
    assert.ok(Object.values(readable).every(Boolean), `Presentation text overflow: ${JSON.stringify(readable)}`);
  };
  await goto('intro');await imageLoaded('primary');await page.waitForTimeout(10000);
  await goto('normal');await imageLoaded('primary');
  await page.screenshot({ path: join(work, 'normal-readable.png') });await page.waitForTimeout(12000);
  mode = 'blocked';await goto('blocked');await imageLoaded('r2');
  await page.screenshot({ path: join(work, 'r2-fallback.png') });await page.waitForTimeout(14000);
  mode = 'hanging';await goto('hanging');await imageLoaded('r2');await page.waitForTimeout(9000);
  mode = 'normal';await goto('recovered');await imageLoaded('primary');await page.waitForTimeout(12000);
  await goto('outro');await imageLoaded('primary');await page.waitForTimeout(12000);
  assert.deepEqual(pageErrors, []);
  await page.screenshot({ path: join(work, 'outro.png') });
  const duration = seconds();
  await context.close();context = null;videoPath = await video.path();
  const evidence = {
    recordedAt: new Date().toISOString(), website: base, scope: 'Browser-only image failure simulation; no provider outage or data writes',
    objectKey, durationSeconds: duration, observedTimeoutMs: hangElapsed, chapters, events, pageErrors,
    presentation: { capture: '1280x720', output: '1920x1080', captionPixels: 36, statusPixels: 36, focusedLiveView: true },
  };
  await writeFile(join(output, 'supabase-r2-failover-evidence.json'), JSON.stringify(evidence, null, 2) + '\n');
  execFileSync(process.env.FFMPEG_BIN || 'ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-i', videoPath,
    '-vf', 'scale=1920:1080:flags=lanczos', '-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
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
