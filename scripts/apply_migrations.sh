#!/usr/bin/env bash
# Apply pending SQL migrations in filename order, tracking what ran.
# Re-running is safe: applied files are skipped via schema_migrations.
# Usage: ./scripts/apply_migrations.sh   (db container must be up)
set -euo pipefail

docker compose exec -T db psql -U museum -d museum -c \
  "CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);"

# Baseline: databases created before this tracker existed (001/002 applied
# by hand) have the tables but no records. media_asset only exists via 002
# (which requires 001), so its presence proves both — record them instead
# of replaying non-idempotent files onto existing tables.
docker compose exec -T db psql -U museum -d museum -c \
  "INSERT INTO schema_migrations (filename)
   SELECT v.filename FROM (VALUES ('001_initial_schema.sql'), ('002_media_assets.sql')) AS v(filename)
   WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'media_asset')
   ON CONFLICT (filename) DO NOTHING;"

for f in database/migrations/0*.sql; do
  name="$(basename "$f")"
  done_flag="$(docker compose exec -T db psql -U museum -d museum -tAc \
    "SELECT 1 FROM schema_migrations WHERE filename = '$name';")"
  if [ "$done_flag" = "1" ]; then
    echo "skip $name (already applied)"
    continue
  fi
  echo "apply $name ..."
  docker compose exec -T db psql -U museum -d museum -v ON_ERROR_STOP=1 -f - < "$f"
  docker compose exec -T db psql -U museum -d museum -c \
    "INSERT INTO schema_migrations (filename) VALUES ('$name');"
done
echo "Migrations OK"
