# Technical maintenance handover

Start with the root [README](../../README.md) and
[deployment notes](../../infra/deployment.md). The deployed environment follows
`dev`, not `main`. Record a release's commit, successful CI/deployment runs,
health results and any separately applied migration versions.

## Routine checks

- `/health` confirms API liveness; `/api/health` checks PostgreSQL readiness.
- Review the latest CI and Nightly recovery backup workflow runs, not only
  whether their configuration is enabled. Schedules may be delayed.
- Keep secrets in the existing private provider environments / GitHub Secrets;
  pass only public `VITE_*` settings to React. Preserve the backend signing key.
- Check schema versions using `DB_TARGET=staging ./scripts/check_migrations.sh`.
  This is read-only. Credentials stay in private `.env` or the secret store.
- Re-run dependency audits and tests before releasing updates. Database tests
  require a disposable database ending in `_test`; they rebuild its schema.

## Database changes and recovery

Migrations are ordered SQL files in `database/migrations/`. Do not edit applied
migration files. Add a new migration, back up, rehearse a restore/migration on a
copy, and obtain approval before hosted application. Do not import demo seed
accounts or reset tables during deployment. Harbor/team-owned account imports
remain a separate operation; preserve account IDs, roles and password hashes.

The cloud workflow backs up the public PostgreSQL schema and media and retains
private artifacts for seven days. It runs daily at 02:17 Australia/Adelaide and
has a 10 MiB artifact cap. Restore only with a verified backup, identified target
and the procedure in [media operations](../runbooks/media-ops.md). Image mirroring
is not continuous database replication or an automatic PostgreSQL failover.

## Media and permissions

Staff authenticate to the website. Server-side checks load the current active
account and role before storage writes. No individual Supabase membership is
required. `media_asset` stores a file URL plus its owner and cover flag; record
IDs and image IDs are different. Do not renumber either sequence.

The browser tries Supabase then the same mirrored R2 object after an error or
ten-second timeout. New files need mirroring before fallback can work. Upload
backend switching is an operator action; image reads alone fall back automatically.
Keep R2 outage uploads safe using the existing synchronization guards.

Reference images are contextual rather than accession photographs; their
immutable-key credits and licenses are documented [here](../media/reference-catalog-images.md).
Existing exhibition mislinks need Natalie/the curator's confirmed mapping;
do not guess ownership from record order. A missing object can coexist with a
valid database URL, so check file bytes/reachability as well as foreign keys.

## Remaining team deliverables

The academic final report, requirements/personas/journeys/usability records and
some diagrams remain empty on the reviewed `dev` baseline. PR #30 contains
separate pending documentation work; review it against the current system before
merging. Do not invent usability results or treat empty files as completed
handover evidence. Historical load-test numbers apply to their documented test
machine, not the current Free hosting plan.
