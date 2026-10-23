# Media ops runbook — future edits across primary + failover copies

Companion to `docs/design/media-storage.md`. The golden rule behind every
procedure below: **the app is the only writer; mirrors are dumb copies.**
Never edit a failover copy directly — fix the primary, then re-sync.

Copy inventory (what lives where):

| Copy | Holds | Updated by | Freshness |
|---|---|---|---|
| Selected Postgres (Docker by default; Supabase for staging) | All rows incl. `media_asset` | App writes + migrations | Live |
| Supabase bucket | Uploaded bytes (primary backend) | App uploads | Live |
| R2 bucket | Mirror of Supabase bucket | Manual sync now; cloud nightly after activation | Last verified sync; nightly RPO pending |
| Local volume `/app/uploads` | `local`-mode uploads | App uploads (local mode) | Live |
| Local mirror dir | Copy of active backends | Manual sync or cloud recovery artifact | Last verified copy |
| `pg_dump` rotation | Full DB snapshots, 7-day | Manual now; GitHub Actions after activation | Last verified dump; nightly RPO pending |

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

Manual commands below; the selected cloud schedule runs sequentially at
02:17 Adelaide time after spending controls and activation (§4b):
```bash
./scripts/backup_database.sh              # pg_dump -Fc → backups/, 7-day rotation
./scripts/mirror_media.sh                 # Supabase -> local mirror dir
DB_TARGET=staging ./scripts/mirror_media.sh --dest r2   # Supabase -> R2 warm standby (needs R2 keys)
./scripts/mirror_media.sh --from volume   # uploads volume (local-mode files) -> mirror dir
```
Manual re-sync after any bulk change: same commands, then verify:
```bash
docker compose exec -T db psql -U museum -d museum -c \
  "SELECT storage, media_type, count(*) FROM media_asset GROUP BY 1, 2;"
rclone check <src> <dst>   # byte-level agreement, non-zero exit on drift
```

### 4b. Cloud nightly jobs (independent of the member Mac)

Use `.github/workflows/recovery-backup.yml` on dev, the repository default
branch. Repository write access can configure repository-level Secrets and
variables; administrator access is required for environment-level Secrets.
DATABASE_URL_STAGING and MUSEUM_RCLONE_CONFIG were saved through the signed-in
GitHub browser and both names verified on 2026-10-13. The workflow remains
disabled until an organization billing owner confirms zero paid overages and
shared free allowance, then MUSEUM_BACKUP_ENABLED is set to true. The current
account cannot access organization billing controls. No Mac crontab is installed.

The cloud runner dumps PostgreSQL, mirrors Supabase to R2 and a local runner
folder, checks byte agreement, and publishes a private seven-day recovery
artifact. Download the artifact to any member machine before an offline demo.
Run the workflow manually once after activation, then check two scheduled
nights; timing and free-budget controls are detailed in §9. Manual recovery
commands remain available even if Actions is unavailable.

## 5. Failover flip (Supabase down) and failback

Flipping the env var alone only moves **new** uploads — existing rows
still point at the dead backend's URLs. The repoint step below rewrites
stored URL prefixes (keys are identical across backends thanks to the
shared `storage_key` layout + rclone sync), so old thumbnails keep working.

```bash
# 0. Precondition: the standby actually holds the bytes. If the last
#    nightly mirror is stale, sync first:
DB_TARGET=staging ./scripts/mirror_media.sh --dest r2
# 1. Repoint existing rows supabase -> r2 (mechanical prefix rewrite;
#    drop DB_TARGET=staging only when the rows live in the local db):
DB_TARGET=staging SUPABASE_URL=... R2_PUBLIC_BASE=... ./scripts/repoint_media_urls.sh supabase r2
# 2. Flip serving to R2 (or `local` if R2 unbuilt / offline demo).
#    Compose uses the local db; if this API serves staging, add
#    -f docker-compose.yml -f docker-compose.staging.yml to each `up`:
MEDIA_BACKEND=r2 docker compose up -d backend
# ... verify: upload → 201, old pages render from R2 URLs, then:
# Failback when Supabase recovers (mirror image of the above):
./scripts/mirror_media.sh --dest supabase   # copy outage-window files back
DB_TARGET=staging SUPABASE_URL=... R2_PUBLIC_BASE=... ./scripts/repoint_media_urls.sh r2 supabase
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
- Cloud flip/failback and rclone agreement: later verified on hosted staging;
  see the dated results in §10.

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
Storing it selects nothing: scripts and Compose use the local Docker db by
default. Opt in to staging per command, from the shell:

```bash
DB_TARGET=staging ./scripts/apply_migrations.sh   # likewise backup/import/restore/repoint
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --force-recreate backend
```

With `DB_TARGET=staging`, scripts read only this setting from `.env` without
executing the env file (requires host Python 3); a pre-exported value takes
precedence. They fail if it is empty, reject unknown `DB_TARGET` values, and
print the target first. Never put `DB_TARGET` in `.env`. Hosted restore also
requires typing `staging` (or `--yes-i-mean-staging`). The guarded
`mirror_media.sh --dest r2` (Supabase -> R2) checks hosted rows, so it also
needs `DB_TARGET=staging`.
Never paste credentials into logs, chat, PRs or screenshots.

Initial import is for an **empty public schema only**:

```bash
DB_TARGET=staging ./scripts/import_database.sh database/regional_museum_1010.sql
DB_TARGET=staging ./scripts/apply_migrations.sh   # all migration versions must skip
```

The importer uses psql for plain SQL in one transaction, filters the exact
PG17-only `SET transaction_timeout = 0;` line for PostgreSQL 15/16, and
leaves the snapshot unchanged. Never load seed.sql alongside it. Tracker
baselining recognises 003 only when its column, constraint and index exist.
If public already has tables, stop and inventory them; this is not a license
to overwrite an existing hosted project.

Hosted backups contain **only public**, with ownership commands omitted.
Keep ACLs for hosted restore so browser-role revocations survive recovery;
the offline decoder strips ACLs because Docker has no Supabase roles.
They are application backups, not backups of Supabase Auth, Storage metadata
or other managed schemas. Hosted PG17.6 was verified on 2026-10-13; backups use a PG17 client.
Offline custom-archive restore decodes with PG17, filters its unsupported
transaction timeout and redundant public-schema creation, then restores to
Docker PG16 in one psql transaction. Hosted restore filters to public, runs atomically
and exits on the first error. Stop any external API deployments before
restore; the script stops/restarts the local Compose API, and terminates
remaining database sessions. It cannot prevent external writers reconnecting.
Verify staff login, upload, row counts by storage, migration replay and a
fresh dump on the actual hosted target before declaring migration complete.

Offline (local) is the default, so no override is needed:

```bash
./scripts/apply_migrations.sh
MEDIA_BACKEND=local docker compose up -d --force-recreate backend
```

Offline backup/restore likewise run without `DB_TARGET`. Docker and hosted
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

Snapshot correction: migration 004 labels the 12 existing URLs in this
project/bucket as supabase. Migration 005 removes anonymous/authenticated
Data API access to application tables and sets restrictive future grants.
Migration 006 also removes global creator defaults. The explicitly
idempotent permission policy is enforced after migration replay/restores,
because target-default grants can survive an archive ACL restore. All three
were verified on hosted PG17 and keyless Docker PG16.

## 9. Deployment and account closeout

R2 stores media and can store pg_dump files; it does not host a live
PostgreSQL server. Its [subscription](https://developers.cloudflare.com/r2/get-started/)
includes free monthly usage but charges usage above the allowance. The user
uses an existing R2 account; bucket-scoped credentials and public reads have
been verified (§10). No new paid service or card-required signup was performed.

Hosting decision (2026-10-13, user): Render Free API + Cloudflare Pages
frontend, Supabase PG/Storage primary and R2 object standby. Docker Compose
remains the offline fallback. Oracle is not being provisioned.
[Oracle's FAQ](https://www.oracle.com/cloud/free/faq/) requires a card for
identity verification, so creating an account requires explicit approval.
Pages is deployed at https://regional-museum-platform.pages.dev/ from a
compiled direct upload. The organization approved the Render integration;
the Free API is live at https://regional-museum-platform-api.onrender.com.
The current account is an organization
member with repository push access, not an administrator.

Scheduling decision (user requires independence from their Mac): cloud GitHub
Actions, not local cron. No recurring Mac jobs were installed. The workflow
runs at 02:17 Australia/Adelaide (DST-aware), first dumping the database then
mirroring/checking media, and retaining a private recovery artifact for seven
days. Both encrypted repository secrets DATABASE_URL_STAGING and
MUSEUM_RCLONE_CONFIG (the private rclone.conf content) were configured through
the browser on 2026-10-13. It remains disabled until the organization billing
owner confirms zero paid overages, then MUSEUM_BACKUP_ENABLED can be set to
true. Never send either secret value through chat.
Merge the workflow to dev (the default branch), run it manually once, then
require two green scheduled nights before claiming nightly RPO.

[GitHub scheduling](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
can be delayed; failures must be reviewed. The five-minute job timeout bounds
this workflow to about 155 minutes/month; its 10 MiB artifact guard and seven-day retention bound its stored artifacts to about 70 MiB. Other organization
workloads share the allowance. The [Free allowance](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
is 2,000 minutes and 500 MB, so an administrator must review shared usage and
disable paid overages. Activation remains pending; manual commands are verified.

Account inventory: Safari identifies Museum Platform Project in RockENZO's
Org; confirmed ownership, second secret holder and M7 successor remain to be
recorded. R2 owner/successor, hosting owner, key rotation status, and handover
acceptance remain open. Keep secrets with no more than two holders.


## 10. Verified cloud drills and deployment gaps (2026-10-13)

- Hosted PG17.6: psql client-to-session-pooler TLSv1.3 verified with
  \conninfo (pg_stat_ssl reports the separate internal pooled connection).
  Empty-public-schema import PASS; 4 users and 12 original
  media rows; 001–006 tracker replay PASS; real API login 200 and Supabase
  upload 201 with byte-equal public read 200. New backend-only secret key is
  saved in .env and maps to service_role; legacy JWT keys were not revoked.
- Bucket museum-media is public-read. There are no storage.objects write
  policies; a publishable-key write was denied (HTTP 400 wrapper, storage
  status 403 / RLS violation). Anonymous account-table SELECT/INSERT changed
  from true to false after 005; staff login remained 200.
- Supabase S3 mirror -> R2: PASS, rclone check --download exit 0.
  Final post-cleanup agreement: 13 matching objects, zero differences.
  Local Supabase mirror also has 13 matching objects, about 2.15 MB total.
- Actual staging media flip Supabase -> local -> Supabase: PASS; 13 old
  image reads returned 200; local upload 201 and byte-equal read; failback
  retained that upload. Supabase -> R2 -> Supabase: PASS; 15 old image reads
  returned 200; R2 upload 201 and byte-equal read; final failback read all
  16 original/drill images successfully. Temporary uploads 14–17 were then
  deleted through the API, leaving the original 12 rows on Supabase.
- R2 token is Object Read & Write scoped only to museum-media; its public
  development URL is enabled. It is rate-limited and is a prototype standby,
  not a production SLA. Normal browser user-agent reads returned 200; plain
  Python urllib's default user-agent returned 403 during verification.
- Real hosted PG17 custom dump -> disposable Docker PG16 restore: PASS,
  including a clean dump with ACLs (offline restore strips managed-role ACLs).
  Hosted restore against a disposable PG17 target with pre-existing browser
  defaults also PASS after policy enforcement: anon SELECT=false,
  authenticated INSERT=false, unrelated managed_guard row retained.
  Older-schema restore applies pending migrations before restarting the API.
- Actual disposable uploads-volume deletion: old image 404; restored mirror
  produced 200 with bytes matching. All 13 copied DB images served locally.
  No existing project data volume was deleted.
- Backend suite: 35 passed. Configured frontend origin and localhost passed
  CORS preflight; unrelated origin was rejected. Frontend build and Pages
  homepage/SPA route/assets HTTP checks passed.

Mirrors keep distinct folders: backups/media/supabase for the cloud copy,
backups/media/volume for local-mode files. This prevents rclone sync of the
cloud copy from deleting the local-volume backup. Offline recovery can use
`./scripts/restore_media.sh supabase` without cloud access; the default
`./scripts/restore_media.sh` uses the volume snapshot. Installed rclone is
optional: the verified official container v1.75.2 is pinned by digest and
reads only the ignored repository rclone.conf. Keep that file mode 0600.

Render setup is recorded in render.yaml: Free Python service, backend root,
private DATABASE_URL copied from the staging URL, generated signing secret,
MEDIA_BACKEND=supabase, /health check and FRONTEND_ORIGIN set to the Pages URL.
LOCAL_UPLOAD_DIR is /tmp/museum-uploads so application boot does not require
writing /app on Render. Set private Supabase/R2 values in Render's environment.
No Render database, disk, paid plan or payment method is required. Its
[Free service](https://render.com/docs/free) sleeps after 15 idle minutes and
wakes on request; warm /health, then test login/media before the demo.

The frontend keeps existing mock business data, while auth and the new
/staff/media Media library use the real Render API (VITE_AUTH_USE_MOCKS=false).
The API
implements auth, staff media and user administration; collection/event/
membership APIs remain team integration work. Do not switch all frontend
requests to real mode before those routes are implemented. Pages is built with VITE_API_BASE_URL=https://regional-museum-platform-api.onrender.com/api.
No API credentials belong in frontend builds.

GitHub PR CI checks were not reported for this branch at handoff; local
pytest/build/drill evidence is verified, but no remote CI pass is claimed.

Open handover items: organization billing owner confirms zero paid
overages and shared quota; enable the cloud backup variable; first scheduled backup run; two green scheduled nights; frontend business API
integration; named second secret holder and M7 successor/transfer acceptance.
Current cloud access is held by Rock: Supabase organization RockENZO's Org,
Cloudflare's signed-in account (existing R2 subscription), and Render My
Workspace. Account-owner identity/transfer must be confirmed at handover.


## 11. Automatic image fallback and recording preparation

The Pages build needs only public values: VITE_SUPABASE_URL,
VITE_SUPABASE_BUCKET=museum-media, and VITE_R2_PUBLIC_BASE. MediaImage maps
only this project/bucket's public image URLs to the same object key in R2.
A primary load error triggers one R2 attempt; a second error shows Image
unavailable. Loading another source resets the attempt. Foreign/local/R2
URLs never redirect. This changes browser reads, not DB rows or upload mode.
The reusable component is used in the real staff Media library; unfinished
business pages still need their normal API/image integration.

Cloud sync setup: PR #16 is merged, so R2 outage safeguards are on default
dev. Both repository Secrets have been configured and verified by name at
Settings → Secrets and variables → Actions. Only repository write access was
needed. After the organization billing owner confirms zero paid overages
and available shared quota, set Actions variable MUSEUM_BACKUP_ENABLED=true.
Run Nightly recovery
backup manually, inspect success and its private artifact, then verify two
scheduled nights. It runs independently of Render and any member laptop.
This is daily replication, not instantaneous dual writing; newly uploaded
images have no standby until the next successful mirror.

Before an operator switches writes to R2, disable the scheduled workflow and
wait for any running backup to finish. The media scripts also refuse a
Supabase→R2 sync when R2-backed rows exist (or the DB query fails). During
R2 mode, nightly_media backs up R2 into backups/media/r2 and byte-checks it.
Fail back R2→Supabase, verify bytes, repoint rows, restart the sole writer,
then re-enable scheduling. These guards do not replace operator coordination
of a running sync. restore_media.sh r2 can load the outage copy into Docker.

Recording A (automatic image-read failover, storage-only simulation):
1. Warm Render /health, confirm Supabase DB is available and a successful
   mirror/check has completed. Sign in as staff and open /staff/media,
   collection object ID 6. Show the image's Supabase URL and successful load.
2. In a browser with request blocking, block only
   */storage/v1/object/public/museum-media/* on this Supabase host; disable
   cache and reload. Keep Render and PostgreSQL connections available.
3. Show the failed Supabase request, successful matching R2 request and the
   visible image. No manual URL rewrite or upload-backend switch is involved.
4. Unblock and reload: image loads from Supabase again. State explicitly
   that this simulates browser image access failure, not a whole Supabase outage.

Recording B (whole Supabase unavailable): use the existing disposable Docker
recovery drill and a downloaded cloud dump/media artifact. Restore Postgres,
restore media, repoint URLs to local, test login/read/upload offline, and
rehearse failback. R2 does not provide a PostgreSQL server; image fallback
alone cannot rescue a DB-dependent page when the database is down.

Verification 2026-10-13: Render Free Singapore deploy from dev eb19265 live;
health/login/me/media/CORS HTTP 200; own temporary upload HTTP 201, byte-equal
public read HTTP 200, cleanup HTTP 204. Backend 35 tests pass. Frontend build,
scoped ESLint and three URL-mapping tests pass. Stubbed cloud-command drills:
R2 overwrite refused; DB failure prevents sync; normal mirror path passes;
R2 outage path backs up R2 and does not touch Supabase. Cloud automatic
schedule remains pending billing confirmation and activation.


Live Pages browser verification (2026-10-13): production bundle
index-C6Nte3ye.js published; /, /signin, /staff/media and JS/CSS assets returned
HTTP 200. Safari real staff login rendered Emma Taylor and collection object
6's Supabase image (naturalWidth > 0). A temporary browser-document CSP
blocked the Supabase image host: MediaImage switched automatically to
R2 aboriginal-painted-shield.jpg with data-media-fallback=true and a loaded
image. A second CSP blocked both hosts: Image unavailable appeared and no
image retry remained. Reload removes these browser-only policies. Hosted
rows, active writer and stored image objects were unchanged. This verifies
browser image-access failure handling, not an actual provider outage.


Actions Secrets browser setup (2026-10-13): DATABASE_URL_STAGING and
MUSEUM_RCLONE_CONFIG saved successfully; GitHub confirmed Repository secret
added for each and displayed both names. Credentials were read from ignored
local configuration and never printed. PR #16 is merged. Repository Secrets
are available with write access; the earlier admin-only statement was wrong.
The organization's billing budgets page/API was unavailable to this account,
so no paid overages setting is claimed and recurring execution stays disabled.
GitHub Free includes 2,000 standard runner minutes and 500 MB artifact storage,
shared with other organization workloads. Secret storage has no separate fee.
See [Secrets permissions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
and [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).


## 12. Automatic code deployment from dev (2026-10-23)

Render's live service dashboard was verified: Free Python service, linked
private repository A06-museum-platform/Regional-museum-platform, dev branch,
backend root and Auto-Deploy On Commit. Commit 693b24e was already live.
render.yaml now explicitly records branch dev and autoDeployTrigger commit;
the dashboard is the actual configuration for this existing non-Blueprint
service. Changes outside backend may not trigger a backend rebuild.

The existing Pages Direct Upload project cannot be converted to native Git
integration. Preserve its URL and use the existing CI frontend job instead.
Cloudflare's production branch is dev. After backend tests pass, CI installs
Node 22 dependencies, builds the frontend, checks image URL mapping, and
publishes frontend/dist with the pinned official Wrangler action only on
push to refs/heads/dev. PR builds and main builds do not publish production.
The ten-minute frontend timeout bounds each invocation; concurrency cancels
an obsolete build for the same ref. No additional scheduled job, runner job,
paid plan or automatic migration is added. CI still consumes shared Actions
allowance; organization billing controls remain the billing owner's scope.
This deployment integration does not enable MUSEUM_BACKUP_ENABLED.

The Pages token has only this Cloudflare account's Cloudflare Pages Edit
permission and is stored as repository Secret CLOUDFLARE_API_TOKEN, with an
ignored local copy in .env as CLOUDFLARE_PAGES_API_TOKEN. The user explicitly
authorized both destinations. Cloudflare scopes this permission by account;
workflow commands target only regional-museum-platform. Rotate/revoke this
token from Cloudflare's user API Tokens page and replace the repository
Secret when ownership changes. Never copy it into frontend configuration.

frontend/.env.production contains public build values only: the Render API
URL and Supabase/R2 public image endpoints. It preserves VITE_USE_MOCKS=true
and real auth (VITE_AUTH_USE_MOCKS=false) from the previous deployed prototype.
Switch business screens to real mode only after the team's remaining API
integration is verified. npm run dev retains its usual local configuration;
production build variables can be overridden by the invoking environment.

Workflow: open a feature PR into dev, require passing CI, merge, then inspect
Render Deploys and the CI Deploy existing Cloudflare Pages site step. Verify
the Pages canonical deployment commit matches the merge SHA and the API
health endpoints respond. Frontend and backend deploy independently, so use
backward-compatible API changes. Database migrations remain an explicit
operator step; deploying code neither migrates nor copies hosted data.

For rollback, redeploy a known good commit in Render and roll back to the
previous production deployment in Cloudflare Pages. Fix/revert dev as well,
otherwise a later automatic deployment will reintroduce the bad code.
For pause, turn Render Auto-Deploy Off and disable/remove only the CI Pages
publishing step (not the unrelated recovery workflow).

References: [Cloudflare Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/),
[CI upload integration](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/),
and [Render automatic deploys](https://render.com/docs/deploys).
