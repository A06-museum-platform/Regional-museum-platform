# Verification and testing

Tests run on disposable data unless explicitly described as read-only hosted
checks. Do not seed or run mutation-based browser suites against the live site.
Local seed credentials are not live credentials. See [browser instructions](../tests/e2e/README.md).

## Backend and database

Use Python 3.11+ and install `backend/requirements.txt` in a virtual environment.

```bash
cd backend
pytest tests/unit tests/permissions -q
TEST_DATABASE_URL=postgresql://museum:museum@localhost:5432/museum_test pytest tests -q
```

The full suite rebuilds its selected `*_test` database. It exercises real SQL,
role checks, registration/login, memberships, bookings/cancellation, attendance,
content editing, opening rules, recommendations, media validation and existing
image cover selection. Never set this URL to hosted data.

```bash
MIGRATION_TEST_CONTAINER=<disposable-postgres-container> python3 -m unittest discover -s tests/ops -v
```

The selected disposable PostgreSQL container must have a `museum` superuser.
The nine operations tests cover schema replay, source-snapshot compatibility,
atomic rollback, concurrent runners and synchronization guards. Five database
cases are skipped if no test container is supplied; skips are not passes.

## Frontend

```bash
cd frontend
npm ci
npm run lint
npm test
npm run build
npm audit --audit-level=high
```

Public production configuration is in `frontend/.env.production`. Test the
actual API mode rather than drawing conclusions from mock accounts. Isolated
Node browser tests cover eight media-fallback cases, nine session cases and
six record-selection groups; the API/storage is intercepted for these checks.
The data-mutating Python suite additionally drives the real local API and
PostgreSQL through all four roles, bookings, event registration, mobile layouts,
admin tasks and simulated membership checkout/approval.

## Dependency changes in the delivery review

Frontend compatible patch updates resolve the npm audit findings. The backend
uses patched FastAPI/Starlette/Pydantic/multipart packages and PyJWT rather than
the previous python-jose/ecdsa dependency chain. HS256 algorithm, signing secret,
claims, expiry and bcrypt hash format remain unchanged. Regression tests verify
previous compact HS256 tokens and reject expired, tampered or wrong-algorithm
sessions. Framework-route tests inspect OpenAPI or actual routing rather than
private router internals. CI runs backend and frontend dependency audits.

## Review evidence: 2026-10-29

Before release approval, the delivery branch passed 239 backend tests on
PostgreSQL 17, nine migration/synchronization tests, frontend lint, 13 frontend
unit tests, a production build and zero-finding resolved dependency audits.
The isolated real-stack browser suite passed all seven scripts, including
membership checkout/approval; the route crawl covered 26 role/page combinations
and the mobile pass covered eight public pages with zero horizontal overflow.
Detailed execution logs and screenshots stay in ignored local `backups/`;
PR CI provides independently inspectable checks of the committed change.

Read-only hosted checks found healthy API/database probes, migrations 001–012,
validated constraints and no duplicate primary-image flags. A manually dispatched
cloud recovery backup succeeded (run 40712926388, private artifact 7,082,120 bytes).
Media reachability and curatorial ownership must be reviewed separately from
relational integrity. A passing test suite does not establish Free-hosting
capacity, real payment processing, complete academic reports or curator approval.
