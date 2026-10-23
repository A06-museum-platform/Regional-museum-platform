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
