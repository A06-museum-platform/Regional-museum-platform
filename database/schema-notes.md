# Schema notes

## Migrations

Plain SQL, applied in filename order by `scripts/apply_migrations.sh`, which
records each in `schema_migrations` so re-running is safe. **Never edit an
applied migration — add a new numbered file.** CI rebuilds a database from
all of them for every integration test, so a broken migration fails CI.

| File | What it does |
|---|---|
| `001_initial_schema.sql` | Core ERD: accounts and roles, exhibitions, collection items, museum information, opening hours, facilities, ticket types and reservations, events and registrations, memberships |
| `002_media_assets.sql` | `media_asset` — images/video for items, exhibitions, events |
| `003_media_storage_backend.sql` | `media_asset.storage` — which backend holds each file |
| `004_snapshot_media_storage.sql` | Aligns databases restored from the October snapshot |
| `005_backend_only_database.sql` | Revokes Supabase `anon`/`authenticated` access (the API is the only client) |
| `006_backend_default_privileges.sql` | Same, for tables created later; re-applied on every run |
| `007_user_account_is_active.sql` | `user_account.is_active` — disable sign-in without deleting |
| `008_booking.sql` | `booking` groups a visit's ticket rows; `ticket_reservation.booking_id`, `unit_price` |
| `009_content_enrichment.sql` | Slugs, accession numbers, categories, galleries, year ranges, draft/published, event prices/ages, registration party size/contact/reference, `membership.children_covered`, weekly-hours `note`, `opening_hours_override` |
| `010_activity_log.sql` | Server-written audit log |
| `011_interests.sql` | Interest vocabulary (8 tags, shipped as reference data), user interests, content tags |

## Conventions

- `<table>_id` identity primary keys; constraint names `pk_`, `fk_`, `uq_`, `ck_`, index names `ix_`.
- Status columns are `VARCHAR` with `CHECK` lists (readable in `psql`, easy to extend in a migration).
- Money is `NUMERIC(10,2)` in dollars in the database and integer cents in the API.
- Older tables use `TIMESTAMP` (museum-local); tables from 008 on use `TIMESTAMPTZ`. Event dates and times are stored museum-local and converted with `AT TIME ZONE 'Australia/Adelaide'`.
- Galleries: `main_hall`, `telegraph`, `monster_mine`, `encounter_bay`. Categories: `mineral`, `instrument`, `document`, `photograph`, `machinery`.

## Notable rules held in the schema

| Rule | Where |
|---|---|
| One active registration per account and event | partial unique index `uq_event_registration_active` |
| A session starts and ends the same day, end after start | `ck_event_time` |
| A dated exception is either closed (no times) or open with close after open | `ck_opening_hours_override_times` |
| Accession numbers and slugs unique | `uq_collection_item_accession`, `uq_*_slug` |
| Deleting an event / item / exhibition removes its media and tags | `ON DELETE CASCADE` |
| Deleting an account keeps its activity entries (actor name copied) | `ON DELETE SET NULL` on `activity_log` |

Rules that need counting (capacity, member-ticket limits) are enforced in
`backend/app/services/` under locks — see `docs/diagrams/booking-flow.md`.

## Seed data

`seed/seed.sql` — load once on a freshly migrated database. Dates are
relative to `CURRENT_DATE`, so a demo always has past and upcoming events,
current exhibitions, today's arrivals and future bookings. Accounts:
`README.md`.
