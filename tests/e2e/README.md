# Browser end-to-end checks

Playwright (Python) scripts that drive the real UI against a running stack —
the evidence for the "all five functional areas demonstrated end to end"
and "Content Manageability" evaluation criteria. Each prints what it checked
and saves screenshots to `tests/e2e/screenshots/` (git-ignored).

| Script | What it proves |
|---|---|
| `crawl.py` | Every route, as signed-out / visitor / member / staff / admin, loads with no API errors or page crashes |
| `booking_flow.py` | Choose a visit while signed out → sign in → details → simulated payment → confirmation → shows on the account page → cancel |
| `staff_event_flow.py` | Staff create and publish a session in the UI → a visitor finds it, signs in, registers → staff see the places taken and cancel it → the admin activity log shows every step |
| `register_and_mobile.py` | Account creation with validation and duplicate-email handling; public pages at 390 px have no horizontal scroll |
| `member_portal.py` | Recommendations, registering from a recommendation, changing interests, cancelling a registration; visitor vs member views; staff tag editor |
| `admin_flows.py` | Front-desk check-in, booking search, event registrations; an administrator promotes an account to staff and it can open the workspace |

## Running

```bash
# 1. fresh demo data (the scripts expect the seed's accounts and bookings)
docker compose down -v && docker compose up -d --build
./scripts/apply_migrations.sh
docker compose exec -T db psql -U museum -d museum -v ON_ERROR_STOP=1 --single-transaction < database/seed/seed.sql

# 2. once: the browser driver
pip install playwright && playwright install chromium

# 3. the checks
./tests/e2e/run_all.sh                       # or: python tests/e2e/crawl.py
E2E_BASE_URL=https://staging.example.org ./tests/e2e/run_all.sh
```

The flows change data (bookings, registrations, roles), so reload the seed
before running the suite a second time.

## Isolated image fallback drill

`media_fallback.mjs` drives the real `MediaImage` component using a development-only
fixture, with storage requests intercepted in a fresh Chromium context. It does
not log in, change cloud data, or require storage credentials. Unlike the flows
above, no database reset is needed. The Node Playwright package and its Chromium
browser must already be available.

```bash
# Terminal 1, from frontend/: public storage URL configuration only
npm run dev -- --mode production --host 127.0.0.1 --port 5179 --strictPort

# Terminal 2, from the repository root
E2E_BASE_URL=http://127.0.0.1:5179 node tests/e2e/media_fallback.mjs
```

If Playwright is installed outside the repo, set `PLAYWRIGHT_MODULE_PATH` to its
absolute `index.mjs`. `PLAYWRIGHT_EXECUTABLE_PATH` can select an existing Chromium.
The eight scenarios cover healthy primary reads, primary errors and hangs, both
providers failing or hanging, offscreen lazy loading, a changed source after
failure, and card-placeholder behavior. Tests advance the browser clock instead
of waiting ten real seconds per attempt. The fixture is not a production build
entry point.

## Public catalog photo checks

After the original snapshot catalog and current catalog are both published,
`catalog_media.mjs` reads the real public API and tests the collection detail
page. It checks correct photos, a missing classification, browser-only Supabase
blocking and R2 fallback, an escaped filename, both providers failing, and the
current catalog's existing no-photo placeholder. It never changes cloud data.
It uses the same Node Playwright setup and optional executable/module overrides
as the isolated drill above.

```bash
E2E_BASE_URL=http://127.0.0.1:5179 node tests/e2e/catalog_media.mjs
# Or verify a deployed, approved release:
E2E_BASE_URL=https://regional-museum-platform.pages.dev node tests/e2e/catalog_media.mjs
```

`API_BASE_URL` can override the public Render API used for catalog discovery.
For local Vite checks, use `VITE_API_BASE_URL=/api` and
`API_PROXY_TARGET=https://regional-museum-platform-api.onrender.com` so browser
GET requests use the dev proxy. Run only against a catalog with the restored
source records; this script does not insert fixtures or reset a database.
