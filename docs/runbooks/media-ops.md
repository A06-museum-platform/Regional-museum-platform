# Media ops runbook — future edits across primary + failover copies

Companion to `docs/design/media-storage.md`. The golden rule behind every
procedure below: **the app is the only writer; mirrors are dumb copies.**
Never edit a failover copy directly — fix the primary, then re-sync.

Copy inventory (what lives where):

| Copy | Holds | Updated by | Freshness |
|---|---|---|---|
| docker Postgres (primary) | All rows incl. `media_asset` | App writes + migrations | Live |
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
- _Flip drill: ____-__-__ by ____ → result: _____
- _Failback drill: ____-__-__ by ____ → result: _____

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
