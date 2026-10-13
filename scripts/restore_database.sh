#!/usr/bin/env bash
# Restore a pg_dump snapshot (Tier 1).
# Usage: ./scripts/restore_database.sh backups/museum_2026-09-20_0200.dump
# Target: local compose db by default (drop/recreate); DATABASE_URL_STAGING
# restores hosted Supabase Postgres instead (--clean into the live database,
# which hosted plans don't let you drop).
# WARNING: replaces all data in the target database. Never point at prod.
set -euo pipefail

source "$(dirname "$0")/lib/db_target.sh"
_db_target_init
echo "Target: $DB_MODE"

DUMP="${1:?usage: restore_database.sh <dump-file>}"
test -f "$DUMP" || { echo "dump file not found: $DUMP"; exit 1; }
DUMP_ABS="$(cd "$(dirname "$DUMP")" && pwd)/$(basename "$DUMP")"

# Pooled writers block destructive restore — stop local backend, or
# terminate other sessions on a remote target.
echo "Stopping writers..."
db_stop_writers

if db_is_remote; then
  # pg_restore needs a real file: mount the dump into a throwaway container.
  # --clean drops objects first (equivalent to drop/recreate, which hosted
  # plans forbid on the live database).
  echo "Restoring $DUMP ..."
  docker run --rm -v "$DUMP_ABS:/tmp/restore.dump:ro" postgres:16 \
    pg_restore -d "$DATABASE_URL_STAGING" --schema=public --no-owner --no-acl \
      --clean --if-exists --exit-on-error --single-transaction /tmp/restore.dump
else
  echo "Dropping and recreating database 'museum'..."
  docker compose exec -T db psql -U museum -d postgres -c \
    "DROP DATABASE museum;" -c "CREATE DATABASE museum;"
  # pg_restore needs a real file (custom-format archives are not streamable
  # over stdin), so copy the dump into the db container first.
  echo "Restoring $DUMP ..."
  docker compose cp "$DUMP_ABS" db:/tmp/restore.dump
  docker compose exec -T db pg_restore -U museum -d museum --no-owner --no-acl \
    --exit-on-error --single-transaction /tmp/restore.dump
  docker compose exec -T db rm /tmp/restore.dump
fi

# An older snapshot can predate the current code (e.g. no media_asset.storage
# yet) — bring the schema forward BEFORE the backend boots, or a valid
# backup produces an unusable deployment. The tracker baselines whatever the
# dump already contains, so this is safe on current-schema restores too.
echo "Applying pending migrations ..."
./scripts/apply_migrations.sh

echo "Restarting backend..."
docker compose up -d backend > /dev/null
echo "Smoke check:"
db_psql -c \
  "SELECT (SELECT count(*) FROM user_account) AS users, (SELECT count(*) FROM media_asset) AS media;"
echo "Restore OK"
