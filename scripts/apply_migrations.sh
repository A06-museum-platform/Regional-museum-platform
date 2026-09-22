#!/usr/bin/env bash
# Apply pending SQL migrations in filename order, tracking what ran.
# Re-running is safe: applied files are skipped via schema_migrations.
# Usage: ./scripts/apply_migrations.sh   (db container must be up)
set -euo pipefail

docker compose exec -T db psql -U museum -d museum -c \
  "CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);"

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
