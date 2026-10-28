# Regional Museum Visitor Experience Platform

Capstone project for the South Australian Regional Heritage Network.
A fully functional web application prototype replacing reliance on posters,
brochures and word of mouth with a centralised online presence.

## Deployed application

- **Website:** https://regional-museum-platform.pages.dev/
- **Staff media library:** https://regional-museum-platform.pages.dev/staff/media
- **Backend API documentation:** https://regional-museum-platform-api.onrender.com/docs
- **API liveness:** https://regional-museum-platform-api.onrender.com/health
- **Database readiness:** https://regional-museum-platform-api.onrender.com/api/health

The live website uses the real FastAPI API and Supabase PostgreSQL, not the
frontend mock accounts. Render Free can take around a minute to wake after
inactivity; allow the first API request to complete before retrying. Payments
are **simulated**: this release does not charge cards.

Cloudflare Pages serves React, Render runs FastAPI, Supabase stores PostgreSQL
records and primary media, and Cloudflare R2 holds mirrored media. R2 is a
file backup, not a PostgreSQL replica. Images try the matching R2 object after
a Supabase error or ten-second timeout. New uploads need mirroring before
they have R2 coverage. Image fallback does not repair an API/database outage.

Deployments follow **`dev`**, also the repository default branch: Render
deploys after checks pass; GitHub Actions builds and publishes Pages. Changing
`main` alone does not publish this environment. Apply reviewed migrations
separately after a backup; the deployment gate only checks them.
See [deployment](infra/deployment.md) and [maintenance](docs/handover/technical-maintenance-notes.md).

## Stack

React (Vite) · FastAPI · PostgreSQL · Docker Compose

## Quick start

Requires Docker with Compose v2 and Git. Host-only development/testing uses
Python 3.11+ and Node.js 22. Run from the repository root with a fresh local
database; do not load demo seed data into the hosted database.

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

Once the containers are running, open another terminal at the repository root
and apply the schema migrations, then load the demo data into the fresh local
database. Scripts and `docker compose` use the local database by default;
hosted staging needs an explicit `DB_TARGET=staging` prefix (see
`docs/runbooks/media-ops.md`).

```bash
./scripts/apply_migrations.sh
docker compose exec -T db psql -U museum -d museum -v ON_ERROR_STOP=1 --single-transaction < database/seed/seed.sql
```

Migrations can be rerun safely; load the seed data only once on a fresh database
(it inserts fixed demo records and is not idempotent).

`/health` is a DB-free liveness probe for Render and Compose. `/api/health`
checks database readiness with a two-second timeout and returns 503 if the
database is unavailable.

## Running the tests

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/unit tests/permissions -q
```

`tests/integration/` runs the API against a real PostgreSQL database that it
rebuilds from `database/migrations` and `database/seed/seed.sql` before every
test. It only ever touches a database whose name ends in `_test` and is
skipped when none is reachable:

```bash
# From the repository root, while the local db container is running:
docker compose exec db createdb -U museum museum_test
cd backend
TEST_DATABASE_URL=postgresql://museum:museum@localhost:5432/museum_test pytest tests -q
```

The full suite **rebuilds its selected test database**. Never point it at the
hosted database. For the frontend, from `frontend/`, run
`npm ci && npm run lint && npm test && npm run build`.

CI runs both against a `museum_test` service container, plus the front
end's lint, unit tests and build. The role-permission matrix is tested row
by row for every role in `backend/tests/integration/test_role_matrix.py`
(see `docs/role-permission-matrix.md`).

Browser end-to-end checks (Playwright) live in `tests/e2e/` — see its
README.

## Demo accounts

`database/seed/seed.sql` creates one account per role. The passwords are
for local demos only.

They are not a list of live credentials. Use your team's existing live account;
passwords and service keys must not be added to this README.

| Role | Email | Password | After login |
|---|---|---|---|
| Visitor | alice@example.com | `Visitor123!` | `/account` |
| Member | ben@example.com | `Member123!` | `/account` (Ben holds Visitor + Member; the higher role wins) |
| Staff | staff@museum.org | `Staff123!` | `/staff` |
| Administrator | admin@museum.org | `Admin123!` | `/staff` |

To see the 403 page, sign in as Alice or Ben and open `/staff`, or as
Emma (staff) and open an `/admin/...` page such as `/admin/members`.

## Switching to real accounts

The following is an administrator-operated **local setup** procedure. Removing
accounts deletes related data; it is not a routine deployment step. Do not run
it on the deployed database without a reviewed backup and explicit approval.

Keep the seeded content (exhibitions, objects, events, hours) but replace
the demo people with real ones:

```bash
# 1. Remove the 12 demo accounts and their bookings, registrations,
#    memberships and activity (asks for confirmation)
docker compose exec backend python /app/scripts/remove_demo_accounts.py

# 2. Create the first administrator (prompts for a password)
docker compose exec backend python /app/scripts/create_admin_user.py --email you@example.com --first Your --last Name
```

Anyone can then create an account at `/register`. To give a team member
the staff workspace, they register first, then an administrator opens
*Staff accounts & roles* (`/admin/accounts`), searches for them and
chooses **Make staff**.

## Repository layout

| Folder | Responsibility |
|---|---|
| `frontend/` | React application — public, member, staff and admin interfaces |
| `backend/` | FastAPI application — models, schemas, services, role-scoped API |
| `database/` | Migrations, seed data, ERD and schema notes |
| `infra/` | Dockerfiles and deployment notes |
| `tests/load/` | Locust load tests against the 100 / 500 concurrency targets |
| `tests/e2e/` | Playwright browser checks of every user flow |
| `docs/` | Requirements, personas, permission matrix, test evidence, reports |
| `scripts/` | Repeatable setup and seed commands |

## The four roles

| Role | Can do |
|---|---|
| Visitor | Browse home page, search collections, view events, book tickets |
| Member | All visitor actions, plus membership status, activity, recommendations |
| Staff | Create and edit events, update opening hours and content, view bookings |
| Administrator | All staff actions, plus revoke member access and assign roles |

Authorisation is enforced **server-side** on every route. The UI hides
unavailable actions for convenience only — it is not a security boundary.

## Presentation demo

[Watch the Supabase → Cloudflare R2 image failover demo](docs/demos/README.md).
The captioned recording shows real image requests, automatic fallback after an
error or ten-second hang, and primary recovery after a reload. Failures are
simulated only in the recording browser; the API and database remain online.

## Contributing

See `CONTRIBUTING.md`. In short: branch from `dev`, small commits,
open a pull request into `dev`; approval and green CI are required before merge.
The current live environment deploys from `dev`; `main` is not its deployment branch.

## Handover and operations

- [Staff and administrator guide](docs/handover/staff-administrator-guide.md)
- [Technical maintenance notes](docs/handover/technical-maintenance-notes.md)
- [Tests and reproducible checks](docs/testing.md)
- [Media, backup and recovery runbook](docs/runbooks/media-ops.md)
- [Reference-image sources and licenses](docs/media/reference-catalog-images.md)
- [Frontend development](frontend/README.md)

The cloud recovery workflow is configured daily at 02:17 Australia/Adelaide;
GitHub schedules can be delayed. It backs up PostgreSQL, mirrors media to R2,
and checks file bytes, with seven-day private artifact retention and a 10 MiB
artifact cap. It does not depend on a developer's Mac. Check workflow results
and restore instructions rather than assuming a backup exists.

Known handover limitations: curators must confirm image-to-record matches
before any reassignment; technical checks do not establish curatorial accuracy.
Some older academic/report documents are empty placeholders, and PR #30 remains
a separate team review.
Historical load-test results describe their recorded test environment, not a
capacity guarantee for Render Free.

## Out of scope

- Real payment processing (booking ends at a **simulated** payment step)
- Native mobile applications
- Integration with external museum systems
