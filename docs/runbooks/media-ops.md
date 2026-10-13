# Media ops runbook — future edits across primary + failover copies

Companion to `docs/design/media-storage.md`. The golden rule behind every
procedure below: **the app is the only writer; mirrors are dumb copies.**
Never edit a failover copy directly — fix the primary, then re-sync.

Copy inventory (what lives where):

| Copy | Holds | Updated by | Freshness |
|---|---|---|---|
| Selected Postgres (Docker by default; Supabase for staging) | All rows incl. `media_asset` | App writes + migrations | Live |
| Supabase bucket | Uploaded bytes (primary backend) | App uploads | Live |
| R2 bucket | Mirror of Supabase bucket | Nightly rclone sync | ≤24h old |
| Local volume `/app/uploads` | `local`-mode uploads | App uploads (local mode) | Live |
| Local mirror dir | Copy of active backends | Nightly rclone sync | ≤24h old |
| `pg_dump` rotation | Full DB snapshots, 7-day | Nightly cron | ≤24h old |

## 1. Schema changes (new tables/columns)

1. Write migration `database/migrations/00N_<what>.sql`. **Append-only:
   never edit a merged `001/002/003` file** — reviewers reject such PRs.
2. Apply to dev with the tracker (safe to re-run — applied files skip):
   ```bash
   docker compose up -d db && sleep 8
   ./scripts/apply_migrations.sh
   ```
   Migrations are non-idempotent by design; the `schema_migrations` table
   is the applied-version mechanism. Never run raw `psql -f` loops over
   `00*.sql` on an existing database — replays fail on already-applied files.
3. Mirror the change in `backend/app/models/` + `schemas/` in the same PR.
4. Failover copies need **no action**: dumps pick up new tables
   automatically; file mirrors are schema-blind; R2/local store bytes,
   not columns.
5. Verify: `\d <table>` in psql + `pytest backend/tests` + app boot.

## 2. Seed / placeholder data changes

- Edit `database/seed/seed.sql` (keep section numbering; media rows stay in
  §14+ with `storage='remote'`), then reseed a scratch DB and re-run the
  app smoke query below. Seeds are placeholders — real staff uploads
  always come through the API (§4).
- Adding a new ownable entity? Follow the 5-step recipe in
  `docs/design/media-storage.md` §5.2 (migration + model + `OWNERS` map +
  seeds + `media.js` PATHS key).

## 3. Media file changes (the important one)

**Normal path — always through the API:**
`POST /api/staff/{collection-items|exhibitions|events}/{id}/media`
lands bytes in the *active* backend and stamps `media_asset.storage`.
Reads, deletes and mirrors all key off that column. Prefer this even for
bulk work — loop the endpoint from a script.

**Bulk import (dozens of files):** write a throwaway script that calls the
upload endpoint per file (auth as staff), rather than dropping files into
a bucket. Rationale: direct bucket drops create bytes with no DB rows —
invisible to reads, mirrors, and deletes.

**If files were dropped directly** (emergency only): backfill rows so the
copies agree:
```sql
INSERT INTO media_asset
  (collection_item_id, url, media_type, storage, sort_order, is_primary)
VALUES (1, 'https://…/seeds/collections/1_1.jpg', 'image', 'supabase', 0, TRUE);
```
then re-run the mirror (§5). Direct drops without backfill rows are the
#1 cause of "the file exists but the page shows nothing."

## 4. Keeping failover copies in agreement

Nightly (02:00 DB dump, 02:05 media mirror):
```bash
./scripts/backup_database.sh              # pg_dump -Fc → backups/, 7-day rotation
./scripts/mirror_media.sh                 # Supabase -> local mirror dir
./scripts/mirror_media.sh --dest r2       # Supabase -> R2 warm standby (needs R2 keys)
./scripts/mirror_media.sh --from volume   # uploads volume (local-mode files) -> mirror dir
```
Manual re-sync after any bulk change: same commands, then verify:
```bash
docker compose exec -T db psql -U museum -d museum -c \
  "SELECT storage, media_type, count(*) FROM media_asset GROUP BY 1, 2;"
rclone check <src> <dst>   # byte-level agreement, non-zero exit on drift
```

### 4b. Installing the nightly jobs (one-time, cron host)

Pick ONE always-on machine (propose: whoever owns DB ops — Molly — or a
shared spot; record the choice in the drill log below). On that host, with
an absolute repo path and rclone remotes configured:

```bash
crontab -e
# Regional Museum Platform — nightly backup (Tier 1 + 1b)
0 2 * * * cd /absolute/path/to/Regional-museum-platform && ./scripts/backup_database.sh
5 2 * * * cd /absolute/path/to/Regional-museum-platform && ./scripts/mirror_media.sh && ./scripts/mirror_media.sh --dest r2
```

Check health with one command: `tail -5 backups/backup.log backups/mirror.log`
— two consecutive green nights = the system is live. If the host laptop
sleeps at 02:00, cron silently skips: prefer a machine that stays awake,
or say so in the handover notes and accept best-effort scheduling.

## 5. Failover flip (Supabase down) and failback

Flipping the env var alone only moves **new** uploads — existing rows
still point at the dead backend's URLs. The repoint step below rewrites
stored URL prefixes (keys are identical across backends thanks to the
shared `storage_key` layout + rclone sync), so old thumbnails keep working.

```bash
# 0. Precondition: the standby actually holds the bytes. If the last
#    nightly mirror is stale, sync first:
./scripts/mirror_media.sh --dest r2
# 1. Repoint existing rows supabase -> r2 (mechanical prefix rewrite):
SUPABASE_URL=... R2_PUBLIC_BASE=... ./scripts/repoint_media_urls.sh supabase r2
# 2. Flip serving to R2 (or `local` if R2 unbuilt / offline demo):
MEDIA_BACKEND=r2 docker compose up -d backend
# ... verify: upload → 201, old pages render from R2 URLs, then:
# Failback when Supabase recovers (mirror image of the above):
./scripts/mirror_media.sh --dest supabase   # copy outage-window files back
SUPABASE_URL=... R2_PUBLIC_BASE=... ./scripts/repoint_media_urls.sh r2 supabase
MEDIA_BACKEND=supabase docker compose up -d backend
```

### 5b. Flip-to-local branch (R2 unbuilt, or fully-offline demo)

Flipping to `local` without this branch leaves old rows pointing at the
dead cloud backend AND an empty volume — old media still fails. The local
branch has three steps where the R2 branch has two:

```bash
# 0. Populate the volume first (bytes must exist before URLs point at them):
./scripts/mirror_media.sh --from supabase --dest volume
# 1. Repoint existing rows supabase -> local:
SUPABASE_URL=... ./scripts/repoint_media_urls.sh supabase local
# 2. Flip serving to local:
MEDIA_BACKEND=local docker compose up -d backend
# ... verify: upload → 201, old pages render from /uploads/…, then:
# Failback: mirror volume -> supabase, repoint local -> supabase, flip back:
./scripts/mirror_media.sh --from volume --dest supabase
SUPABASE_URL=... ./scripts/repoint_media_urls.sh local supabase
MEDIA_BACKEND=supabase docker compose up -d backend
```
Note: `mirror_media.sh --from volume` uses `docker cp` (no rclone, no
cloud), so this whole branch works with zero keys — it is the offline
demo path. Log drills alongside §5 above.
Rehearse both directions once per milestone; log date + result here:
- 2026-10-13 — Codex, disposable `museum-infra-drill` stack: snapshot import
  PASS; 001/002/003 skip on replay; staff login 200; local upload 201;
  read 200 with identical bytes. Backend suite: 31 passed.
- 2026-10-13 — Codex, disposable stack: local media mirror PASS;
  simulated file loss returned 404; `restore_media.sh` restored a 200
  response with byte equality. This rehearses file loss, not deletion of
  a whole volume. No existing project volume was changed.
- 2026-10-13 — Codex, disposable stack: current-snapshot DB restore PASS
  (4 users, 13 media including test upload). Older-schema snapshot restore
  PASS: migration 003 ran before backend restart; same row counts.
- 2026-10-13 — Codex, remote code path against a disposable PostgreSQL 16
  target: public-only backup/restore PASS; unrelated `managed_guard.keep_me`
  table and its row survived; all three migrations skipped on replay.
  This was not a connection to hosted Supabase.
- Cloud flip/failback and rclone agreement: PENDING credentials and bucket
  verification. Local drills do not prove hosted availability.

## 6. Health queries (run any time)

```sql
-- rows per backend: expect supabase/remote dominant, r2/local only after flips
SELECT storage, count(*) FROM media_asset GROUP BY 1;
-- items with no primary image (pages fall back to gradient):
SELECT i.item_id, i.item_name FROM collection_item i
WHERE NOT EXISTS (SELECT 1 FROM media_asset m
  WHERE m.collection_item_id = i.item_id AND m.is_primary);
-- multiple primaries (should return nothing — app demotes on upload):
SELECT collection_item_id, exhibition_id, event_id, count(*)
FROM media_asset WHERE is_primary GROUP BY 1,2,3 HAVING count(*) > 1;
```

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Upload → 503 `STORAGE_NOT_CONFIGURED` | Keys blank for active backend | Fill `.env`, recreate backend container |
| Upload → 502 `STORAGE_ERROR` | Cloud backend unreachable | Flip `MEDIA_BACKEND` (§5), investigate after |
| `/uploads/…` → 404 in dev | Vite proxy missing | `vite.config.js` must proxy `/uploads` (present since this PR) |
| Page shows gradient, file exists in bucket | Missing/backfill-less DB row | §3 backfill query, then mirror |
| Mirror drift (`rclone check` fails) | Direct bucket edits bypassing API | Re-sync from primary; stop editing copies |
| `rclone` memorizing stale creds | Rotated keys | `rclone config` update both S3 remotes |


## 8. Supabase Postgres staging

Keep `.env` private and gitignored. Use the Connect dialog's **Session
pooler**, port 5432 (IPv4), with `sslmode=require`. URL-encode the database
password; the dashboard only shows `[YOUR-PASSWORD]`, not the existing
password. Store the completed URL as `DATABASE_URL_STAGING` in `.env`.
Database scripts read this single setting without executing the env file
(requires host Python 3); a pre-exported value takes precedence. Compose
passes it to the API as `DATABASE_URL`; recreate the backend after changes.
Never paste credentials into logs, chat, PRs or screenshots.

Initial import is for an **empty public schema only**:

```bash
./scripts/import_database.sh database/regional_museum_1010.sql
./scripts/apply_migrations.sh   # all three versions must skip
```

The importer uses psql for plain SQL in one transaction, filters the exact
PG17-only `SET transaction_timeout = 0;` line for PostgreSQL 15/16, and
leaves the snapshot unchanged. Never load seed.sql alongside it. Tracker
baselining recognises 003 only when its column, constraint and index exist.
If public already has tables, stop and inventory them; this is not a license
to overwrite an existing hosted project.

Hosted backups contain **only public**, with ownership/ACL commands omitted.
They are application backups, not backups of Supabase Auth, Storage metadata
or other managed schemas. Hosted restore filters to public, runs atomically
and exits on the first error. Stop any external API deployments before
restore; the script stops/restarts the local Compose API, and terminates
remaining database sessions. It cannot prevent external writers reconnecting.
Verify staff login, upload, row counts by storage, migration replay and a
fresh dump on the actual hosted target before declaring migration complete.

Explicit offline switch (new shell invocation):

```bash
DATABASE_URL_STAGING='' ./scripts/apply_migrations.sh
DATABASE_URL_STAGING='' docker compose up -d --force-recreate backend
```

Use the same empty override for offline backup/restore. Docker and hosted
Postgres are separate databases; changing the URL does not copy their rows.
Keep a recent hosted dump and media mirror available for offline restore.

Pre-demo wake: open the Supabase dashboard, restore/resume the project if
paused, wait for healthy status, then test API login and one existing image.
If it cannot wake, restore the saved DB and media into Docker, repoint cloud
URLs after copying bytes, then start local mode. Free projects may pause
following seven days of low activity; scheduled dumps are the backup strategy,
not PITR. See [pausing](https://supabase.com/docs/guides/platform/free-project-pausing),
[connections](https://supabase.com/docs/guides/database/connecting-to-postgres)
and [backups](https://supabase.com/docs/guides/platform/backups).

Snapshot caveat: the October dump has 12 Supabase public media URLs stamped
`storage=remote`. They will not be touched by the current repoint command.
Confirm which objects this project owns, then correct classifications in a
new append-only migration before rehearsing failover of those images.

## 9. Deployment and account closeout

R2 stores media and can store pg_dump files; it does not host a live
PostgreSQL server. Its [subscription](https://developers.cloudflare.com/r2/get-started/)
includes free monthly usage but charges usage above the allowance. The user
reports an existing R2 account; plan, bucket scope and credentials are still
unverified. No paid service or card-required signup has been performed.

Hosting remains a decision: prefer one Always Free VM for the Compose stack
if the owner accepts the signup requirements and capacity is available.
[Oracle's FAQ](https://www.oracle.com/cloud/free/faq/) requires a card for
identity verification, so creating an account requires explicit approval.
Render with Supabase remains the fallback candidate, subject to current
free-plan limits. Neither deployment has been provisioned or tested.

Scheduling decision for the current undeployed state: backups/mirrors run
manually from Rock's member machine before demos and after important edits.
Nightly cron is deliberately not installed on a sleeping laptop. Once an
always-on host is chosen, move jobs to that host and require two successful
nightly runs before treating nightly RPO as achieved.

Account inventory: Safari identifies Museum Platform Project in RockENZO's
Org; confirmed ownership, second secret holder and M7 successor remain to be
recorded. R2 owner/successor, hosting owner, key rotation status, and handover
acceptance remain open. Keep secrets with no more than two holders.
