#!/usr/bin/env bash
# Import the plain October snapshot into an EMPTY application schema.
# Local compose db by default; DB_TARGET=staging imports into hosted staging.
# Never combine this dump with seed.sql. Existing databases use restore_database.sh.
set -euo pipefail
source "$(dirname "$0")/lib/db_target.sh"
_db_target_init
DUMP="${1:-database/regional_museum_1010.sql}"
test -f "$DUMP" || { echo "dump file not found: $DUMP" >&2; exit 1; }
TABLES="$(db_psql -v ON_ERROR_STOP=1 -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")"
if [ "$TABLES" != "0" ]; then
  echo "Refusing import: public schema is not empty. Use a separate staging project or reviewed restore." >&2
  exit 1
fi
# pg_dump 17 emits this setting; PostgreSQL 15/16 do not support it.
# Filter only that exact compatibility line; preserve the source snapshot.
sed '/^SET transaction_timeout = 0;$/d' "$DUMP" | \
  db_psql -v ON_ERROR_STOP=1 --single-transaction -f -
./scripts/apply_migrations.sh
echo "Snapshot import OK (run migrations again to verify all versions skip)."
