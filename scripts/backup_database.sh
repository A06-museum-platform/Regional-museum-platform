#!/usr/bin/env bash
# Nightly Postgres backup (Tier 1). Run from the repository root.
# Target: local compose db by default; DB_TARGET=staging dumps hosted
# Supabase Postgres instead (same file format, same restore path).
# Cron example: 0 2 * * * cd /path/to/Regional-museum-platform && ./scripts/backup_database.sh
set -euo pipefail

source "$(dirname "$0")/lib/db_target.sh"
_db_target_init

BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
STAMP="$(date +%F_%H%M)"
mkdir -p "$BACKUP_DIR"
LOG="$BACKUP_DIR/backup.log"

echo "[$STAMP] starting pg_dump ($DB_MODE)" | tee -a "$LOG"
if db_is_remote; then
  docker run --rm "$DB_CLIENT_IMAGE" pg_dump "$DATABASE_URL_STAGING" -Fc --schema=public --no-owner \
    > "$BACKUP_DIR/museum_${STAMP}.dump"
else
  docker compose exec -T db pg_dump -U museum -Fc museum \
    > "$BACKUP_DIR/museum_${STAMP}.dump"
fi
echo "[$STAMP] wrote museum_${STAMP}.dump ($(du -h "$BACKUP_DIR/museum_${STAMP}.dump" | cut -f1))" | tee -a "$LOG"

# Retention: keep KEEP_DAYS of dumps, prune older.
# shellcheck disable=SC2086
find "$BACKUP_DIR" -name 'museum_*.dump' -mtime +$KEEP_DAYS -delete
echo "[$STAMP] backup OK" | tee -a "$LOG"
