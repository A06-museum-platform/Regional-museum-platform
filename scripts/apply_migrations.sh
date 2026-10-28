#!/usr/bin/env bash
# Apply pending SQL migrations in filename order, tracking what ran.
# Re-running is safe: applied files are skipped via schema_migrations.
# Target: local compose db by default; DB_TARGET=staging selects hosted
# Supabase Postgres via DATABASE_URL_STAGING (see scripts/lib/db_target.sh).
# Usage: ./scripts/apply_migrations.sh
#        DB_TARGET=staging ./scripts/apply_migrations.sh
set -euo pipefail

source "$(dirname "$0")/lib/db_target.sh"
_db_target_init

# Baseline and each migration use the same transaction-scoped lock. The
# migration body and version marker commit together, including under retries.
db_psql -v ON_ERROR_STOP=1 --single-transaction -f - <<'SQL'
SELECT pg_advisory_xact_lock(747104606);
CREATE TABLE IF NOT EXISTS public.schema_migrations (filename TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);

-- Baseline databases created before this tracker existed. media_asset
-- proves 001/002 were already applied; do not replay their table creation.
INSERT INTO public.schema_migrations (filename)
   SELECT v.filename FROM (VALUES ('001_initial_schema.sql'), ('002_media_assets.sql')) AS v(filename)
   WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'media_asset')
   ON CONFLICT (filename) DO NOTHING;

-- The October snapshot already includes 003. Check the column, constraint
-- and index before recording it as applied.
INSERT INTO public.schema_migrations (filename)
   SELECT '003_media_storage_backend.sql'
   WHERE EXISTS (SELECT 1 FROM information_schema.columns
     WHERE table_schema = 'public' AND table_name = 'media_asset'
       AND column_name = 'storage' AND is_nullable = 'NO')
     AND EXISTS (SELECT 1 FROM pg_constraint
       WHERE conrelid = to_regclass('public.media_asset') AND conname = 'ck_media_asset_storage')
     AND to_regclass('public.ix_media_asset_storage') IS NOT NULL
   ON CONFLICT (filename) DO NOTHING;
SQL

# Render completely before opening a transaction. A failed SQL generator must
# never leave a partial input stream that psql could otherwise commit.
sql_file="$(mktemp)"
trap 'rm -f "$sql_file"' EXIT

for f in database/migrations/0*.sql; do
  name="$(basename "$f")"
  done_flag="$(db_psql -tAc \
    "SELECT 1 FROM public.schema_migrations WHERE filename = '$name';")"
  if [ "$done_flag" = "1" ]; then
    echo "skip $name (already applied)"
    continue
  fi
  echo "apply $name ..."
  python3 scripts/lib/migration_sql.py "$f" \
    --policy database/migrations/006_backend_default_privileges.sql > "$sql_file"
  db_psql -v ON_ERROR_STOP=1 --single-transaction -f - < "$sql_file"
done
# ACL restoration does not purge grants inherited from target defaults.
# Re-enforce this explicitly idempotent, permission-only policy even when
# its tracker entry was restored. Do not replay schema/data migrations.
db_psql -v ON_ERROR_STOP=1 -f - < database/migrations/006_backend_default_privileges.sql
echo "Backend-only database access enforced"
echo "Migrations OK"
