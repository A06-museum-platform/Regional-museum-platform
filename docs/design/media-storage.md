# Media Storage Design — Regional Museum Platform

| Field | Value |
|---|---|
| Status | Approved for implementation (P1 merged as PR #5; P2–P4 this branch/PR) |
| Authors | Rock (backend/integration), Molly (database) — reviewers: Ray, Harbor |
| Relates to | PR #5 `feature/staff-media-upload`; API contract G2; proposal D1/D3; eval criteria: functional prototype, content manageability |
| Milestones | M4 backend operational; M5 feature-complete demo |

## 1. Purpose

Define where museum images (and later, video) live, how they get there,
how visitors receive them, and how the system survives each dependency
failing. This document is the single reference for all media decisions;
code, migrations and runbooks must trace back to a section here.

## 2. Scope

- **In:** staff upload/list/delete of images for collections, exhibitions,
  events; public read of those images; seed/placeholder media; backup and
  failover of the media subsystem.
- **Out:** video upload UI (schema-ready, disabled by cap); image
  transforms/cropping; user-generated content; migration of the museum's
  historic photo archive (future phase, same pattern applies).

## 3. Requirements

1. Multiple images per item; exactly one primary (drives the contract's
   `thumbnail_url`).
2. Staff-only writes, public reads (role matrix row 1).
3. Contract-shaped errors `{detail, code}` on every failure.
4. Zero new dependencies for the primary path; free-tier-only clouds.
5. Fully-offline demo path (risk register: demo never depends on
   internet-hosted services).
6. Every failure mode has a rehearsed response (backup §8).

## 4. Architecture

Three boxes, two links. Files (bytes) and facts (URLs) travel separately
and meet only at upload time.

- **PostgreSQL (docker)** holds facts: `media_asset` rows (owner, URL,
  type, order, primary, storage backend). No binaries, ever.
- **Supabase Storage (primary)** holds bytes: bucket `museum-media`,
  public read, writes via `service_role` from backend only.
- **Backends `r2` / `local`** are warm standbys behind one env var
  (`MEDIA_BACKEND`), not parallel writers — no split-brain by construction.

### 4.1 Traffic sequences

**F1 — Staff upload** (`MEDIA_BACKEND=supabase`):
`Browser --multipart--> API --validate--> API --PUT--> Supabase
--URL--> PG --201 {thumbnail_url}--> Browser`

**F2 — Visitor view (any mode):**
`Browser --GET--> API --SELECT--> PG --JSON{urls}--> Browser
--<img src>--> CDN directly` (backend uninvolved in step 4).

**F3 — Nightly sync:** `pg_dump --> shared drive` (02:00) and
`rclone sync Supabase --> R2 + local dir` (02:05). Two jobs: rows and
blobs live in different systems. (rclone talks to Supabase through its
S3-compatible endpoint — no custom code.)

**F4 — Outage:** set `MEDIA_BACKEND=r2`, recreate backend. Flows F1/F2
repeat with the R2 box substituted; R2 egress is free so recovery costs
nothing.

**F5 — Failback:** `rclone sync R2 --> Supabase`, flip var back. Rehearse
F4/F5 once each, log both.

### 4.2 Backend mode table

| `MEDIA_BACKEND` | Writes | Reads | Keys? | Use when |
|---|---|---|---|---|
| `supabase` | Supabase | Supabase CDN | Yes | Normal days (keys configured) |
| `r2` | R2 (S3 API, boto3) | R2 public URLs | Yes (scoped token) | Supabase outage |
| `local` (default) | Docker volume `/app/uploads` | Backend `/uploads` static | No | Keyless dev + fully-offline demo |

## 5. Data model

### 5.1 `media_asset` (migration `002`, merged)

One row per file. Nullable FK to exactly one owner, enforced by
`ck_media_asset_single_owner`; cascade delete cleans rows (storage
objects deleted explicitly by the service).

`media_id PK | collection_item_id FK | exhibition_id FK | event_id FK
| url TEXT | media_type image|video | sort_order | is_primary
| uploaded_by FK | created_at`

Migration `003` adds `storage VARCHAR(10) ∈ {supabase|r2|local|remote}`,
default `remote` (existing seed rows are remote URLs — truthful, and
delete skips them: nothing to delete).

Reads derive the frozen-contract `thumbnail_url` from the primary asset;
no contract change for reads. The four write endpoints are a G2 amendment
(Ray/Harbor/Rock sign-off).

### 5.2 Adding a future ownable entity (recipe)

New entities (e.g. `blog_post`, `homepage_hero`, `membership_card`) are
expected. To make one ownable, all five steps (checklist enforced in PR
review):

1. Migration `00N_`: `ALTER TABLE media_asset ADD COLUMN <entity>_id
   INTEGER REFERENCES <entity>(id) ON DELETE CASCADE`; extend the
   single-owner CHECK with `+ (<entity>_id IS NOT NULL)::int`; add index.
2. ORM model: matching `Mapped[Optional[int]]` FK field.
3. Router: one entry in the `OWNERS` map
   `{url-segment: (table, pk, fk)}` — routes, validation and delete are
   generated from the map, no new endpoint code.
4. Seeds: `seeds/<entity>/` bucket folder + rows flagged primary.
5. Frontend: one key in `media.js` `PATHS` (+ optional `MediaUploader`
   instance on the entity's management page).

**Scaling note:** nullable-FKs stay clean up to ~5 owners. Beyond that,
migrate to per-entity link tables (`<entity>_media(entity_id, media_id)`)
and retire the FK columns in one dedicated migration — do not grow a
sixth nullable FK. The service layer (`upload`/`remove`/URL building) is
owner-agnostic and survives either shape unchanged.

### 5.3 Seed media convention

- Bucket/paths: `seeds/<entity>/<owner_id>_<n>.jpg` for real files;
  picsum placeholder URLs until client photos arrive.
- DB: `seed.sql` §14+, first row per owner `is_primary`, `storage='remote'`.
- Seeds must render with zero keys and zero bucket (offline-safe reads).

## 6. API surface

- `POST /api/staff/{collection-items|exhibitions|events}/{id}/media`
  (multipart `file`, query `is_primary`, `sort_order`) → `201`
  `{ media, thumbnail_url }`
- `GET /api/staff/{…}/{id}/media` → `200 [...]` (primary first)
- `DELETE /api/staff/media/{media_id}` → `204`
- Errors: anon `401 AUTH_REQUIRED`; non-staff `403 FORBIDDEN`;
  bad type `400 VALIDATION_ERROR`; oversize `413 FILE_TOO_LARGE`;
  missing owner/media `404 NOT_FOUND`; storage down `502 STORAGE_ERROR`;
  unconfigured `503 STORAGE_NOT_CONFIGURED`.
- Validation caps: images JPEG/PNG/WebP ≤ 5 MB; video MP4/WebM ≤ 40 MB
  (under the 50 MB free cap; video endpoints schema-ready, UI deferred).

## 7. Configuration

`.env` (gitignored, ≤2 holders for secrets): `SUPABASE_URL`,
`SUPABASE_SERVICE_KEY`, `SUPABASE_BUCKET`, `R2_*` (P3), `MEDIA_BACKEND`
(default `local`), `MAX_IMAGE_MB`, `MAX_VIDEO_MB`. Placeholders in
`.env.example`. Never in images, compose files, chats, or screenshots.

## 8. Backup, failover, restore

| Failure | Response | RPO/RTO (prototype) |
|---|---|---|
| Supabase down | Flip `MEDIA_BACKEND` supabase → r2 (or → local if R2 unbuilt/offline) | Minutes; rehearsed |
| Volume lost | Restore from rclone mirror (`restore_media.sh`) | Nightly RPO |
| PG down | `restore_database.sh` from `pg_dump` rotation (7-day) | 24h RPO, <30min RTO |
| Whole venue offline | Screen recording (risk register) | — |
| Free-tier expiry/pause | Handover notes name owner + successor; system degrades to fully local | M7 sign-off item |

Restore drills (one DB, one media) run before M4 gate; results logged.
Cloud accounts transfer or decommission at M7 — no orphaned cloud.
Operational detail: `docs/runbooks/media-ops.md`.

## 9. Security notes

Bucket public-read, anon write denied; all writes via backend-held
`service_role`. Filenames uuid-renamed (no user input in paths);
extension↔content-type match enforced; keys env-only with rotation
procedure. R2 tokens scoped to one bucket when built.

## 10. Open decisions

- D1: R2 as warm standby vs primary (recommendation: standby; Supabase
  primary unchallenged unless pausing bites over the break).
- D2: Volume vs bytea for local mode (recommendation: volume).
- D3: R2 account owner + M7 successor.
- D4: Real seed photos vs picsum (awaiting client via Natalie).

## 11. Implementation plan (phases)

- **P1 — Foundation (PR #5, merged):** 002 + seeds §14, config,
  `SupabaseStorage`, model/schemas, staff router + `require_staff`,
  19 tests, `media.js` + `MediaUploader` + mock images, decisions entry.
- **P2 — Local fallback (this PR):** 003 (`storage` col), `LocalStorage`
  + factory, StaticFiles mount, compose volume, Vite `/uploads` proxy,
  mode tests, flip drill.
- **P3 — R2 standby (this PR, code):** `S3Storage` (boto3), rclone S3
  remotes both ends, nightly sync cron, F4/F5 rehearsal logs. Cloudflare
  account + keys remain manual setup (see runbook).
- **P4 — Backup jobs (this PR, scripts):** `backup_database.sh` +
  `restore_database.sh` + `restore_media.sh`, cron host decision, first
  fire drills, handover runbook sections.
- **P5 — Hardening/closeout (follow-up):** real seed photos, contract
  amendment merged, video enable/disable call, M7 cloud-lifecycle sign-off.

## 12. Glossary

- **Blob / object storage:** cloud files addressed by key over HTTPS, not
  by path on a disk.
- **Bucket / key:** a flat container / a file's full name inside it
  (`uploads/events/1/a3f9.jpg`).
- **RLS (Row Level Security):** Supabase Postgres policies; our bucket
  denies anon writes at this layer.
- **service_role:** Supabase's server-side master key — backend only,
  never browsers, never chat.
- **Warm standby:** a copy kept current (rclone sync) but not serving
  until flipped to.
- **Split-brain:** two writers diverging with no canonical copy — the
  reason failover is a manual switch, not automatic.
- **RPO / RTO:** how much data you can lose / how long restore takes.
- **3-2-1 rule:** 3 copies, 2 different media, 1 offsite (Supabase +
  volume + R2/Drive).
