# Museum frontend

React/Vite application for public visitors, members, staff and administrators.
Live site: https://regional-museum-platform.pages.dev/ . See the root
[README](../README.md) for local accounts and the complete Docker setup.

## Local development

Use Node.js 22. Start the local backend/database first and apply migrations
and demo seed data as described in the root README. Then:

```bash
npm ci
VITE_API_BASE_URL=/api API_PROXY_TARGET=http://localhost:8000 npm run dev
```

The Vite proxy forwards `/api` and `/uploads` to the backend. Docker Compose
sets its proxy target to `http://backend:8000`. Real API/auth mode is the
default; set `VITE_USE_MOCKS=true` / `VITE_AUTH_USE_MOCKS=true` only for explicitly
isolated UI demos. Mock accounts are unrelated to live PostgreSQL accounts.

## Verify and build

```bash
npm run lint
npm test
npm run build
npm audit --audit-level=high
```

`npm run build` reads `.env.production`, containing public Render/Supabase/R2
URLs only. Every `VITE_*` value can enter the browser bundle: never put server,
database, Supabase service or R2 credentials there. Local Compose passes only
public frontend settings, not the backend's private environment.

## Release behavior

The `frontend` job in `.github/workflows/ci.yml` publishes the existing Pages
project after a push to `dev` passes backend tests, frontend checks and the
hosted migration gate. A build by itself is not a deployment. After release,
refresh an already open browser tab so it loads the new JavaScript.

Authenticated API 401 responses return users to sign-in, preserving their
destination. The server determines roles; UI route guards are not security
boundaries. Media Library selects real records by title and ID, and its
“Use as cover” control promotes an image already linked to that record.

See [browser checks](../tests/e2e/README.md), including isolated session,
record-selection and image-fallback regressions.
