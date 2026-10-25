# Deployment

## Local (the demonstration path — no internet services needed)

```bash
cp .env.example .env
docker compose up --build -d
./scripts/apply_migrations.sh
docker compose exec -T db psql -U museum -d museum -v ON_ERROR_STOP=1 --single-transaction < database/seed/seed.sql
```

Front end http://localhost:5173 · API docs http://localhost:8000/docs.
`docker compose` runs the API with `--reload` for development.

## Hosted (current staging)

| Part | Where | How it updates |
|---|---|---|
| Front end | Cloudflare Pages project `regional-museum-platform` | CI deploys `frontend/dist` on every push to `dev` after tests pass (`.github/workflows/ci.yml`); build settings in `frontend/.env.production` |
| API | Render web service (`render.yaml`, region Singapore, free plan) | auto-deploys `dev` |
| Database | Supabase Postgres (session pooler URL in `DATABASE_URL_STAGING`) | migrations by hand — see below |
| Media | Supabase Storage, Cloudflare R2 standby | `docs/runbooks/media-ops.md` |

**Every time a merge to `dev` adds a migration, apply it to staging:**

```bash
DB_TARGET=staging ./scripts/apply_migrations.sh
```

To reset staging to the demo data: back it up (`DB_TARGET=staging ./scripts/backup_database.sh`), recreate the schema, apply migrations, load `seed.sql`.

When staging is migrated and seeded, switch the Pages build to the real API
by setting `VITE_USE_MOCKS=false` in `frontend/.env.production`.

## Production settings

- API: build `infra/Dockerfile.backend` — `uvicorn` with `WEB_CONCURRENCY` workers (default 2), keep-alive 75 s, no reload. On Render, set the start command to the same (`uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2 --timeout-keep-alive 75`).
- Required environment: `DATABASE_URL`, `SECRET_KEY` (long random value — tokens are signed with it), `FRONTEND_ORIGIN` (CORS), `ACCESS_TOKEN_EXPIRE_MINUTES`, `MEDIA_BACKEND` and its keys. Template: `.env.example`.
- Front end: `VITE_API_BASE_URL` pointing at the API, `VITE_USE_MOCKS=false`.
- Before go-live: replace the demo accounts (`scripts/create_admin_user.py`), remove the demonstration-accounts panel from the sign-in page (it only shows in mock-auth mode), and change `SECRET_KEY`.

Capacity evidence for sizing: `docs/load-testing.md`.
