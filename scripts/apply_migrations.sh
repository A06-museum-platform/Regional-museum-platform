#!/usr/bin/env bash
# Apply pending SQL migrations in filename order, tracking what ran.
# Re-running is safe: applied files are skipped via schema_migrations.
# Target: local compose db by default; set DATABASE_URL_STAGING for hosted
# Supabase Postgres (session-mode pooler URL + ?sslmode=require).
# Usage: ./scripts/apply_migrations.sh
set -euo pipefail

source "$(dirname "$0")/lib/db_target.sh"
_db_target_init
echo "Target: $DB_MODE"

db_psql -c \
  "CREATE TABLE IF NOT EXISTS schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);"

# Baseline: databases created before this tracker existed (001/002 applied
# by hand) have the tables but no records. media_asset only exists via 002
# (which requires 001), so its presence proves both — record them instead
# of replaying non-idempotent files onto existing tables.
db_psql -c \
  "INSERT INTO schema_migrations (filename)
   SELECT v.filename FROM (VALUES ('001_initial_schema.sql'), ('002_media_assets.sql')) AS v(filename)
   WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'media_asset')
   ON CONFLICT (filename) DO NOTHING;"

# The October snapshot already includes all of 003, but has no tracker.
# Check its column, constraint and index before baselining the migration.
db_psql -v ON_ERROR_STOP=1 -c \
  "INSERT INTO schema_migrations (filename)
   SELECT '003_media_storage_backend.sql'
   WHERE EXISTS (SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'public' AND table_name = 'media_asset'
       AND column_name = 'storage' AND is_nullable = 'NO')
     AND EXISTS (SELECT 1 FROM pg_constraint
       WHERE conrelid = to_regclass('public.media_asset') AND conname = 'ck_media_asset_storage')
     AND to_regclass('public.ix_media_asset_storage') IS NOT NULL
   ON CONFLICT (filename) DO NOTHING;"

for f in database/migrations/0*.sql; do
  name="$(basename "$f")"
  done_flag="$(db_psql -tAc \
    "SELECT 1 FROM schema_migrations WHERE filename = '$name';")"
  if [ "$done_flag" = "1" ]; then
    echo "skip $name (already applied)"
    continue
  fi
  echo "apply $name ..."
  db_psql -v ON_ERROR_STOP=1 -f - < "$f"
  db_psql -c \
    "INSERT INTO schema_migrations (filename) VALUES ('$name');"
done
echo "Migrations OK"
