#!/usr/bin/env bash
# Read-only release gate. Does not apply migrations or copy account records.
set -euo pipefail
source "$(dirname "$0")/lib/db_target.sh"
_db_target_init
applied="$(db_psql -v ON_ERROR_STOP=1 -tAc 'SELECT filename FROM public.schema_migrations ORDER BY filename;')"
missing=0
for f in database/migrations/0*.sql; do
  name="$(basename "$f")"
  case $'\n'"$applied"$'\n' in
    *$'\n'"$name"$'\n'*) ;;
    *) echo "Missing database migration: $name" >&2; missing=1 ;;
  esac
done
if [ "$missing" != 0 ]; then
  echo "Release blocked: back up, validate and apply pending migrations before deploying." >&2
  exit 1
fi
echo "Database migration versions match this release."
