# Decision log

## 2026-10-23 — Integration: real backend by default, one error envelope

**Status:** accepted (Harbor now owns the whole codebase).

- **Migration 008 restored.** PR #21 merged `booking_service.py` but not
  `database/migrations/008_booking.sql` or its tests (they were on
  `backend/bookings/ray`), so `POST /api/bookings` failed on a fresh database.
  Both are now on `dev`.
- **Booking amendment accepted as implemented.** `GET /api/bookings/me` and
  `POST /api/bookings/{reference}/cancel` added; cancelling frees the places.
- **Paths and shapes follow the working front end, not the frozen contract**
  where the two disagree and the front end is already built
  (`/collection-items`, slugs, `page_size`). `docs/api-contract.md` will be updated
  to match the code, not the other way round.
- **Error envelope.** Every error is `{detail, code}`; validation errors add
  `fields` and stay `422`. The front end's `client.js` reads this shape (it
  previously read `{error: {code, message}}`, so real error messages showed as
  "Something went wrong").
- **Mocks off by default.** `VITE_USE_MOCKS` defaults to `false`; mocks remain
  for UI work without a backend.
- **Integration tests** in `backend/tests/integration/` run against a real
  `*_test` database rebuilt from the migrations and seed for every test.

## 2026-10-11 — Booking and membership: front end built against mocks, contract amendment proposed

**Status:** proposed — needs G2 sign-off (Ray/Harbor/Rock) before the
backend endpoints are written.

**Why.** The frozen contract books tickets per event
(`POST /api/events/{id}/bookings`, Flow 5). The client's "ticket booking
with simulated payment" requirement, the revised booking screens and Molly's
`ticket_type` / `ticket_reservation` tables are all about **general admission
on a date** (date, arrival time, ticket type, quantity). The front end
follows the tables and the screens; Flow 5 stays as-is for event-specific
bookings if we keep them.

**What the front end now does (all on mocks, `VITE_USE_MOCKS=true`).**

- `/book` → `/book/details` → `/book/confirmation/:reference` — three steps
  as on the design board. Step 1 is public; steps 2–3 need an account
  (contract role "Member", which Staff/Admin inherit). The choice is kept in
  `sessionStorage` so it survives the trip through sign-in.
- Payment is a clearly labelled simulated step with a required
  acknowledgement. No card fields.
- Arrival windows are two hours, generated from the opening-hours table;
  60 places per window. Member tickets ($0) are only offered to an account
  with an active membership, up to `adults_covered + children_covered`.
- `/membership` lists Individual $65 / Family $120 / Patron $280 and creates
  a **pending** application; an administrator approves it on
  `/admin/members` (same mock data, so the chain works end to end).
- `/account` shows the member's own membership and bookings.

### Endpoints (contract amendment proposed)

| Method | Path | Role | Notes |
|---|---|---|---|
| GET | `/api/ticket-types` | Public | `ticket_type` rows; price in integer cents; Member type only when the caller has an active membership, with `max_quantity` |
| GET | `/api/bookings/availability?date=YYYY-MM-DD` | Public | `{ date, is_closed, opens_at, closes_at, note, windows: [{ start, end, places_left }] }` |
| POST | `/api/bookings` | Member | body `{ visit_date, arrival_window: {start,end}, lines: [{ticket_type_id, quantity}], visitor: {first_name,last_name,email,mobile}, accessibility: [], payment_acknowledged: true }` → `201` booking with `reference`; `400 INSUFFICIENT_TICKETS`, `409 BOOKING_LIMIT_EXCEEDED` (more than 10 tickets) |
| GET | `/api/bookings/me` | Member | `{ items, total, page, size }` |
| GET | `/api/bookings/{reference}` | Member | own booking only (Staff: any); someone else's → `404`, not `403` |
| POST | `/api/bookings/{reference}/cancel` | Member | only while `reserved`; `409` otherwise |
| GET | `/api/memberships/me` | Member | caller's current record, or `404` |
| POST | `/api/membership-applications` | Member | existing Flow 6 endpoint, plus optional `children_covered` |

### Schema questions for Molly

1. `ticket_reservation` stores one ticket type per row. A booking with
   adults + children is several rows — either add a `booking_reference`
   column to group them, or add a parent `booking` table.
2. Arrival window: `visit_time` holds the window start; capacity per window
   (60) is a constant for now — table or config?
3. `membership` has no `adults_covered` / `children_covered`, which the
   locked scope decision and the admin screen already use.
4. No `membership_plan` table — plans are hard-coded on the front end for
   now (`frontend/src/api/mocks/membershipPlans.js`).

## 2026-09-22 — Media failover: explicit `MEDIA_BACKEND` switch (local + R2 standbys)

**Context.** Tutor asked for a total-backup story: what happens when
Supabase is down, and where the second copy lives. Constraint: free-tier
clouds only, simpler-the-better.

**Decision.** One env var picks exactly one backend —
`supabase | r2 | local` (default `local`, zero-config). No automatic
failover: a manual flip can't split-brain, is trivially testable, and is
demoable as a kill-switch drill. Local = docker volume + StaticFiles
(answers the tutor's "blob in docker" with files instead of `bytea`:
same code size, no DB bloat, direct serving). R2 = warm standby via S3
API (10 GB permanent free, zero egress, scoped tokens); Supabase's own
S3 endpoint lets rclone sync both ends with zero custom code.
`media_asset.storage` records which backend holds each file; full design
in `docs/design/media-storage.md`, operations in `docs/runbooks/media-ops.md`.

**Alternatives rejected/parked.**
- Automatic try-Supabase-catch-to-local — divergent copies, no canonical
  source; rejected.
- `bytea` blobs in Postgres — viable but bloats backups, needs streaming
  endpoints, videos impractical; parked as last resort.
- Patroni auto-failover for Postgres — consensus cluster for a prototype
  with no availability criterion; rejected, rationale logged for tutor.
- Azure Blob as mirror — viable but non-S3 API means a second SDK path;
  parked; rclone destination flag reserved if the proposer owns it.

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
