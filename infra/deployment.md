# Deployed environment

- Frontend: https://regional-museum-platform.pages.dev/
- API: https://regional-museum-platform-api.onrender.com/api
- API docs: https://regional-museum-platform-api.onrender.com/docs
- Liveness: `/health`; database readiness: `/api/health`.

Cloudflare Pages serves the static React build. Render Free runs FastAPI
(Python 3.11) from the `backend` directory. Supabase PostgreSQL stores records;
Supabase Storage is primary for media; R2 is the media mirror. Render's local
filesystem is ephemeral and is not the durable media backup.

## Publishing

The deployment branch and current repository default branch are `dev`.
`render.yaml` describes the existing Free backend, with deploy-after-checks.
The CI frontend job publishes the existing Pages project on successful pushes
to `dev`. `main` does not currently trigger this Pages deployment.

1. Make a short-lived branch and open a PR into `dev`.
2. Run tests, dependency audits and the migration gate; obtain approval.
3. If a schema change is needed, back up, rehearse on a copy, and apply it as a
   separate reviewed operation. A code deployment does not apply migrations.
4. Merge after approval and green CI. Verify the successful Pages commit and
   Render deployment, then check both health endpoints and important user flows.
5. Refresh open browser tabs. Check the cloud recovery workflow after data or
   media changes. Rollbacks must consider schema compatibility separately.

## Configuration

Private backend environment: `DATABASE_URL`, `SECRET_KEY`, Supabase service key
and R2 bucket-scoped credentials. Preserve the existing signing key during an
ordinary deployment; changing it invalidates current sessions. Do not put any
of these values in Git, screenshots, frontend variables or handover documents.

Public frontend settings are in `frontend/.env.production`: Render API base,
Supabase project/bucket URL and R2 public base. Staff use website accounts;
FastAPI verifies Staff/Admin roles and performs storage writes privately.

## Operational limits

Render Free may sleep and needs time to wake. Image fallback has bounded
attempts but cannot rescue a stopped API or PostgreSQL outage. R2 is not a
PostgreSQL server or automatically synchronized Supabase bucket: the configured
recovery workflow copies and byte-checks objects daily, with manual dispatch
available when immediate coverage is needed.

Backups are private GitHub artifacts retained for seven days, capped at 10 MiB
per run. Monitor workflow failures, provider quotas and account ownership.
Historical load tests do not guarantee the same performance on Render Free.
See [the media/recovery runbook](../docs/runbooks/media-ops.md) for restoration
and [maintenance](../docs/handover/technical-maintenance-notes.md) for checks.
