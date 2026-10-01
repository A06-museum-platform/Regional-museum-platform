#!/usr/bin/env bash
# Restore a pg_dump snapshot into the docker database (Tier 1).
# Usage: ./scripts/restore_database.sh backups/museum_2026-09-20_0200.dump
# WARNING: replaces all data in the `museum` database. Never point at prod.
set -euo pipefail

DUMP="${1:?usage: restore_database.sh <dump-file>}"
test -f "$DUMP" || { echo "dump file not found: $DUMP"; exit 1; }

# The backend holds pooled connections, and Postgres refuses to drop a
# database with open sessions — stop it first, restart at the end.
echo "Stopping backend (open connections block DROP DATABASE)..."
docker compose stop backend > /dev/null

echo "Dropping and recreating database 'museum'..."
docker compose exec -T db psql -U museum -d postgres -c \
  "DROP DATABASE museum;" -c "CREATE DATABASE museum;"

# pg_restore needs a real file (custom-format archives are not streamable
# over stdin), so copy the dump into the db container first.
echo "Restoring $DUMP ..."
docker compose cp "$DUMP" db:/tmp/restore.dump
docker compose exec -T db pg_restore -U museum -d museum /tmp/restore.dump
docker compose exec -T db rm /tmp/restore.dump

# An older snapshot can predate the current code (e.g. no media_asset.storage
# yet) — bring the schema forward BEFORE the backend boots, or a valid
# backup produces an unusable deployment. The tracker baselines whatever the
# dump already contains, so this is safe on current-schema restores too.
echo "Applying pending migrations ..."
./scripts/apply_migrations.sh

echo "Restarting backend..."
docker compose up -d backend > /dev/null
echo "Smoke check:"
docker compose exec -T db psql -U museum -d museum -c \
  "SELECT (SELECT count(*) FROM user_account) AS users, (SELECT count(*) FROM media_asset) AS media;"
echo "Restore OK"
