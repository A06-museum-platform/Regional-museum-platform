#!/usr/bin/env bash
# Restore a pg_dump snapshot into the docker database (Tier 1).
# Usage: ./scripts/restore_database.sh backups/museum_2026-09-20_0200.dump
# WARNING: replaces all data in the `museum` database. Never point at prod.
set -euo pipefail

DUMP="${1:?usage: restore_database.sh <dump-file>}"
test -f "$DUMP" || { echo "dump file not found: $DUMP"; exit 1; }

echo "Dropping and recreating database 'museum'..."
docker compose exec -T db psql -U museum -d postgres -c \
  "DROP DATABASE museum;" -c "CREATE DATABASE museum;"
echo "Restoring $DUMP ..."
docker compose exec -T db pg_restore -U museum -d museum -f - < "$DUMP" > /dev/null
echo "Smoke check:"
docker compose exec -T db psql -U museum -d museum -c \
  "SELECT (SELECT count(*) FROM user_account) AS users, (SELECT count(*) FROM media_asset) AS media;"
echo "Restore OK"
