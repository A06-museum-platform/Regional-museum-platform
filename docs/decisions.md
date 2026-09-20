# Decision log

## 2026-09-19 — Media storage: Supabase Storage-only (images; video-ready)

**Context.** Collections, exhibitions and events need images (multiple per
item); video may follow. The frozen API contract already promises
`thumbnail_url`, but the merged schema (`001_initial_schema.sql`) stores no
media. Tutor suggested Supabase.

**Decision.** Adopt **Supabase Storage only** — one public bucket,
`museum-media`. Postgres stores public URL strings in the new
`media_asset` table (`002_media_assets.sql`). No Supabase Postgres, Auth or
Edge Functions: our docker-compose Postgres, custom JWT auth and RBAC stay
as designed. Direct `httpx` REST calls, zero new Python dependencies.

**Alternatives rejected.**
- Full Supabase adoption — would discard the docker DB, JWT auth and
  alembic chain for no prototype benefit.
- Cloudinary — better transforms, but another vendor + SDK for the same
  free-tier job; revisit if staff need on-the-fly resizing.
- Binaries in git / `bytea` in Postgres — bloats clones, no CDN, videos
  impractical.

**Limits accepted (free tier).** 1 GB storage, 50 MB max upload, project
pauses after 1 week idle. Enforced in code: images JPEG/PNG/WebP ≤ 5 MB,
video MP4/WebM ≤ 40 MB. Demo fallback: seed/placeholder media served from
stable remote URLs (picsum) so `docker compose up` renders without a bucket.

### How to use Supabase here (one-time setup, one person)

1. Create a free project at supabase.com → Storage → **New bucket**
   named `museum-media`, **Public** ON.
2. Storage → Policies: keep public `SELECT`; ensure anon has **no**
   INSERT/UPDATE/DELETE (writes go through the backend with the
   `service_role` key only).
3. Project Settings → API: copy the project URL and the `service_role`
   (secret) key — never the `anon` key for uploads.
4. Each member copies `.env.example` to `.env` and fills in:
   `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`. Never commit `.env`.
5. Seed/demo images: Dashboard → Storage → `museum-media` → upload into
   `seeds/collections/`, `seeds/exhibitions/`, `seeds/events/` (or keep the
   picsum placeholder URLs in `database/seed/seed.sql`). Staff uploads land
   in `uploads/<collection-items|exhibitions|events>/<id>/<uuid>.<ext>`
   automatically.
6. Distribute the service key 1:1 (never group chat); rotate it in the
   dashboard if it leaks.

### Endpoints (contract amendment proposed — G2 sign-off: Ray/Harbor/Rock)

- `POST /api/staff/{collection-items|exhibitions|events}/{id}/media`
  (multipart `file`, query `is_primary`, `sort_order`) → `201`
  `{ media: {...}, thumbnail_url }`
- `GET /api/staff/{…}/{id}/media` → `200 [{...}]` (primary first)
- `DELETE /api/staff/media/{media_id}` → `204`
- Auth: anon → `401 AUTH_REQUIRED`; non-staff → `403 FORBIDDEN`;
  bad type → `400 VALIDATION_ERROR`; oversize → `413 FILE_TOO_LARGE`;
  missing owner/media → `404 NOT_FOUND`; storage down → `502 STORAGE_ERROR`.
- Public reads are unchanged: `thumbnail_url` is derived from the primary
  asset, so the frozen read contract holds.
