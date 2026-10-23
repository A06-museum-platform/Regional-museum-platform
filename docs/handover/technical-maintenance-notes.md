# Technical maintenance notes

For the developer who looks after the platform after hand-over. Start with
`README.md` (setup, demo accounts) and `docs/diagrams/system-architecture.md`.

## 1. Repository map

| Path | Contents |
|---|---|
| `backend/app/main.py` | App factory: routers, error handlers, CORS, `/health` |
| `backend/app/api/{public,member,staff,admin}/` | Routers by audience; staff/admin routers carry `Depends(require_staff/require_admin)` at router level |
| `backend/app/api/deps.py` | Authentication and role dependencies (roles read from the DB per request) |
| `backend/app/services/` | Business rules — all SQL lives here (`text()` queries, async SQLAlchemy) |
| `backend/app/schemas/` | Pydantic request/response models |
| `backend/app/core/` | Settings (`config.py`), JWT + bcrypt (`security.py`), error envelope (`errors.py`) |
| `backend/tests/` | `unit/`, `permissions/` (fake DB), `integration/` (real DB, incl. role matrix) |
| `frontend/src/api/` | The only code that calls the network; each module has a mock branch for `VITE_USE_MOCKS=true` |
| `frontend/src/pages/{visitor,member,booking,public,staff,admin}/` | Screens; routes in `src/routes/AppRoutes.jsx` |
| `frontend/src/styles/tokens.css` | Design tokens (measured contrast; one 768 px breakpoint) |
| `database/migrations/`, `database/seed/seed.sql` | Schema history and demo data (`database/schema-notes.md`) |
| `scripts/` | Migrations, backup/restore, media mirroring, `create_admin_user.py` |
| `tests/e2e/`, `tests/load/` | Browser checks; load tests |
| `docs/` | Requirements, decisions, API reference, role matrix, testing, this guide |

## 2. Environment variables

| Variable | Used by | Notes |
|---|---|---|
| `DATABASE_URL` | API | `postgresql://…`; `?sslmode=require` supported for hosted Postgres |
| `SECRET_KEY` | API | signs access tokens — **set a long random value in every non-local environment**; changing it signs everyone out |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | API | default 60; there is no refresh token |
| `FRONTEND_ORIGIN` | API | allowed CORS origin |
| `MEDIA_BACKEND` + `SUPABASE_*`, `R2_*`, `LOCAL_UPLOAD_DIR`, `MAX_*_MB` | API | `docs/design/media-storage.md` |
| `WEB_CONCURRENCY`, `PORT` | production image | worker count (default 2) and port |
| `VITE_API_BASE_URL`, `VITE_USE_MOCKS`, `VITE_AUTH_USE_MOCKS` | front-end build | `/api` behind the dev proxy; mocks off in real deployments |
| `API_PROXY_TARGET` | `vite dev` | where the dev server proxies `/api` (default `http://backend:8000`) |
| `TEST_DATABASE_URL` | tests | must point at a `*_test` database |

## 3. Routine tasks

**Add a database change.** Create `database/migrations/012_<what>.sql`
(additive where possible), run `./scripts/apply_migrations.sh` locally, add
or adjust integration tests, update `database/schema-notes.md`. After merge,
apply to staging: `DB_TARGET=staging ./scripts/apply_migrations.sh`.

**Add an endpoint.** Schema in `schemas/`, logic in `services/`, route in the
router for its audience (the router's role dependency then applies), an
integration test, and — if it changes what a role can do — a row in
`docs/role-permission-matrix.md` and `test_role_matrix.py`. Log meaningful
actions with `activity_service.record(...)`.

**Add a screen.** Page under `src/pages/…`, API call in `src/api/…` (with a
mock branch), route in `AppRoutes.jsx` under the right `RoleGuard`, then add
it to `tests/e2e/crawl.py`.

**Back up / restore.** `scripts/backup_database.sh` and
`scripts/restore_database.sh` (both honour `DB_TARGET=staging`); media:
`scripts/mirror_media.sh`, `scripts/restore_media.sh`; a nightly GitHub
Actions backup is defined in `.github/workflows/recovery-backup.yml`. Full
procedures: `docs/runbooks/media-ops.md`.

**Create an administrator.**
`docker compose exec backend python /app/scripts/create_admin_user.py --email … --first … --last …`
(prompts for the password; promotes an existing account if the email
exists).

**Reset the demo.** `docker compose down -v`, `up`, apply migrations, load
`seed.sql` (dates are relative to the load day).

## 4. Quality gates

CI (`.github/workflows/ci.yml`) on every pull request: backend unit +
integration tests on PostgreSQL 16, front-end lint, unit tests, build; on
push to `dev` it also deploys the front end to Cloudflare Pages. Keep it
green; branch from `dev`, pull request into `dev` (`CONTRIBUTING.md`).

## 5. Things to know

- **Authorisation is server-side only.** Hiding a button is not security;
  every write route is under `/api/staff` or `/api/admin`.
- **Roles** come from `user_role`; the highest wins. Approving a membership
  adds the Member role; revoking disables the account.
- **Capacity** for booking windows (60) and window length (2 h) are
  constants in `booking_service.py`; per-event capacity is a column.
- **Membership plans** (Individual / Family / Patron, prices, coverage) are
  defined in code in `membership_service.MEMBERSHIP_PLANS`; a `membership`
  row stores the plan name and `children_covered`.
- **Times:** events are stored museum-local; the API sends UTC ISO strings;
  booking windows and opening hours are `"HH:MM"` local.
- **Payment is simulated.** Adding a real gateway would mean a payment
  record table, a provider integration (hosted checkout, never raw card
  data) and webhook-driven booking confirmation.

## 6. Known limitations and next steps

| Limitation | Suggested next step |
|---|---|
| No password reset or email sending (confirmation emails are described, not sent) | Add an email provider (transactional API) and a reset-token flow |
| No refresh tokens — sessions end after `ACCESS_TOKEN_EXPIRE_MINUTES` | Add refresh tokens if staff find re-signing-in disruptive |
| Membership plans are code, not data | Move to a `membership_plan` table with a staff editor if prices change often |
| Booking window capacity is a constant | Make it per-day configurable alongside opening hours |
| Usability findings (`usability-testing.md`) | Fix severity 3–4 issues found in sessions |
| Free-tier hosting (Render sleeps when idle, Supabase pauses after a week) | Paid tiers or a single VPS for production; wake the services before demos |

## 7. Contacts and ownership

Repository: `A06-museum-platform/Regional-museum-platform` (GitHub), to be
transferred to the client at hand-over (M7). Hosted services (Render,
Supabase, Cloudflare, R2) must be transferred or re-created under the
museum's accounts; rotate every key afterwards.
