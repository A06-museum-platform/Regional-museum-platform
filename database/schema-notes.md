# Database maintenance notes

Canonical schema: ordered SQL files in `database/migrations/`. Local Compose
uses PostgreSQL 16; hosted Supabase currently uses PostgreSQL 17. The migration
runner and tests support both the fresh schema and the October source snapshot.

## Application data

- `user_account`, `role`, `user_role`: active website accounts and effective roles.
  PostgreSQL stores bcrypt hashes, not recoverable passwords.
- `exhibition`, `collection_item`, `event`: content with stable primary keys,
  slugs and publication fields. Display order is not record identity.
- `media_asset`: exactly one collection/exhibition/event owner, public file URL,
  storage provider, image/video type, sort order and public-cover flag. Files
  live in object storage rather than PostgreSQL. An FK cannot prove a file exists.
- `booking`, `ticket_reservation`, `ticket_type`, `event_registration`: visits,
  ticket lines and event places. Booking references differ from numeric keys.
- `membership`: application/status/plan records; payments in this prototype
  are simulated. `activity_log` supports administrative review.
- `museum_information`, `facility`, `opening_hours`, `opening_hours_override`:
  visitor-facing information and museum-local opening rules.
- Interest/tag tables link account interests and content for recommendations.
- `schema_migrations` records applied migration filenames and timestamps.

## Migration history

001 creates the core schema; 002–003 add media ownership/provider fields;
004–006 harden legacy snapshot storage/table access; 007 adds account activation;
008 adds visit bookings; 009 enriches content and opening hours; 010 adds activity;
011 adds interests/tags; 012 reconciles missing snapshot collection fields.

`./scripts/check_migrations.sh` validates versions and critical read columns.
`./scripts/apply_migrations.sh` takes a transactional advisory lock and commits
DDL/data/version changes together. Already applied files are skipped. Keep
applied files immutable. The runner validates the known `materials` overlap
rather than silently accepting an incompatible legacy column.

Everything defaults to the local database. `DB_TARGET=staging` explicitly selects
hosted PostgreSQL; never use it for destructive test resets or demo seeding.
Back up, restore a copy and rehearse before approved hosted migrations. Use a
pg_dump client at least as new as the server (17 for the current hosted DB).

`backend/tests/integration/` rebuilds a disposable `*_test` database before
individual tests. `tests/ops/` additionally proves replay, rollback on failure,
snapshot compatibility and concurrent runner behavior. See
[testing](../docs/testing.md) and [recovery](../docs/runbooks/media-ops.md).

During the 2026-10-29 read-only review, hosted migrations 001–012 were present,
all constraints were validated, media ownership shape was valid and no owner
had duplicate primary-image flags. These checks do not establish curatorial
image accuracy or guarantee current object-storage reachability.
