#!/usr/bin/env bash
# Run on a cloud runner or ops host after the database dump.
# Checks hosted media rows only with DB_TARGET=staging (as the workflow sets).
set -euo pipefail
cd "$(dirname "$0")/.."
source ./scripts/lib/media_rclone.sh
source ./scripts/lib/db_target.sh
_db_target_init
MIRROR_DIR="${MIRROR_DIR:-./backups/media}"
R2_ROWS="$(db_psql -v ON_ERROR_STOP=1 -tAc "SELECT count(*) FROM public.media_asset WHERE storage = 'r2';")"
if [ "$R2_ROWS" != 0 ]; then
  echo "R2-backed rows exist: pausing Supabase -> R2; backing up R2 outage media instead."
  ./scripts/mirror_media.sh --from r2 --dest local
  media_rclone check r2:museum-media "$MIRROR_DIR/r2" --download
  exit 0
fi
./scripts/mirror_media.sh
./scripts/mirror_media.sh --dest r2
media_rclone check supabase:museum-media r2:museum-media --download
media_rclone check supabase:museum-media "$MIRROR_DIR/supabase" --download
