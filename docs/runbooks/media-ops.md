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
2. Apply to dev first, in order:
   ```bash
   docker compose up -d db && sleep 8
   for f in database/migrations/00*.sql; do
     docker compose exec -T db psql -U museum -d museum -f - < "$f"
   done
   ```
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
./scripts/backup_database.sh        # pg_dump -Fc → backups/, 7-day rotation
./scripts/mirror_media.sh           # rclone: active backends → local mirror dir
./scripts/mirror_media.sh --dest r2 # same, toward R2 (needs R2 keys)
```
Manual re-sync after any bulk change: same commands, then verify:
```bash
docker compose exec -T db psql -U museum -d museum -c \
  "SELECT storage, media_type, count(*) FROM media_asset GROUP BY 1, 2;"
rclone check <src> <dst>   # byte-level agreement, non-zero exit on drift
```

## 5. Failover flip (Supabase down) and failback

```bash
# Failover: serve from R2 (or local if R2 unbuilt / offline demo)
MEDIA_BACKEND=r2 docker compose up -d backend   # or MEDIA_BACKEND=local
# ... verify: upload → 201, page renders, then:
# Failback when Supabase recovers:
./scripts/mirror_media.sh --dest supabase   # copy outage-window files back
MEDIA_BACKEND=supabase docker compose up -d backend
```
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
