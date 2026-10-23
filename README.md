# Regional Museum Visitor Experience Platform

Capstone project for the South Australian Regional Heritage Network.
A fully functional web application prototype replacing reliance on posters,
brochures and word of mouth with a centralised online presence.

## Stack

React (Vite) · FastAPI · PostgreSQL · Docker Compose

## Quick start

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
pytest tests                      # unit + permission tests, no database needed
```

`tests/integration/` runs the API against a real PostgreSQL database that it
rebuilds from `database/migrations` and `database/seed/seed.sql` before every
test. It only ever touches a database whose name ends in `_test` and is
skipped when none is reachable:

```bash
docker compose exec db createdb -U museum museum_test
TEST_DATABASE_URL=postgresql://museum:museum@localhost:5432/museum_test pytest tests
```

CI runs both against a `museum_test` service container, plus the front
end's lint, unit tests and build. The role-permission matrix is tested row
by row for every role in `backend/tests/integration/test_role_matrix.py`
(see `docs/role-permission-matrix.md`).

Browser end-to-end checks (Playwright) live in `tests/e2e/` — see its
README.

## Demo accounts

`database/seed/seed.sql` creates one account per role. The passwords are
for local demos only.

| Role | Email | Password | After login |
|---|---|---|---|
| Visitor | alice@example.com | `Visitor123!` | Home page |
| Member | ben@example.com | `Member123!` | `/account` (Ben holds Visitor + Member; the higher role wins) |
| Staff | staff@museum.org | `Staff123!` | `/staff` |
| Administrator | admin@museum.org | `Admin123!` | `/staff` |

To see the 403 page, sign in as Alice or Ben and open `/staff`, or as
Emma (staff) and open an `/admin/...` page such as `/admin/members`.

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

## Contributing

See `CONTRIBUTING.md`. In short: branch from `dev`, small commits,
open a pull request into `dev`; CI must pass before merge. `main` holds
released versions.

## Out of scope

- Real payment processing (booking ends at a **simulated** payment step)
- Native mobile applications
- Integration with external museum systems
