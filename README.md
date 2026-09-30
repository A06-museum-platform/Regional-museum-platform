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

Then seed placeholder data:

```bash
python scripts/seed_database.py
```

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

See `CONTRIBUTING.md`. In short: branch from `main`, small commits,
open a pull request, one reviewer approval required before merge.

## Out of scope

- Real payment processing (booking ends at a **simulated** payment step)
- Native mobile applications
- Integration with external museum systems
