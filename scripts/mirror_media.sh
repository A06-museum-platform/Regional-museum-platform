#!/usr/bin/env bash
# Mirror media files between backends (Tier 1b). Run from the repo root.
#   ./scripts/mirror_media.sh                       # Supabase -> local mirror dir (default nightly)
#   ./scripts/mirror_media.sh --dest r2             # Supabase -> R2 warm standby
#   ./scripts/mirror_media.sh --dest supabase       # R2 -> Supabase (failback)
#   ./scripts/mirror_media.sh --from volume --dest r2    # uploads volume -> R2
#   ./scripts/mirror_media.sh --from volume              # uploads volume -> local mirror dir
#   ./scripts/mirror_media.sh --from r2 --dest volume    # R2 -> uploads volume (failback to local)
#   ./scripts/mirror_media.sh --from volume --dest supabase  # uploads volume -> Supabase (failback from local)
# Requires: rclone with S3 remotes named `supabase` and `r2`
# (Supabase S3 endpoint + R2 S3 endpoint; see docs/runbooks/media-ops.md).
# Volume transfers use `docker cp` (no extra dependencies) and need the
# backend container present (it is, whenever uploads happen).
# Cron example: 5 2 * * * cd /path/to/Regional-museum-platform && ./scripts/mirror_media.sh
set -euo pipefail
source "$(dirname "$0")/lib/media_rclone.sh"

FROM="supabase"
FROM_EXPLICIT=0
DEST="local"
while [ $# -gt 0 ]; do
  case "$1" in
    --from) FROM="${2:-supabase}"; FROM_EXPLICIT=1; shift 2 ;;
    --dest) DEST="${2:-local}"; shift 2 ;;
    *) DEST="$1"; shift ;;
  esac
done

# Preserve the documented failback shorthand: --dest supabase means R2 ->
# Supabase unless the caller explicitly chose a source (e.g. volume).
if [ "$FROM_EXPLICIT" = 0 ] && [ "$DEST" = supabase ]; then
  FROM=r2
fi

MIRROR_DIR="${MIRROR_DIR:-./backups/media}"
LOG="${LOG:-./backups/mirror.log}"
mkdir -p "$MIRROR_DIR"

# R2 outage uploads are newer than Supabase. Never let a scheduled sync
# overwrite/delete them before the operator completes failback.
if [ "$FROM" = supabase ] && [ "$DEST" = r2 ]; then
  source "$(dirname "$0")/lib/db_target.sh"
  _db_target_init
  R2_ROWS="$(db_psql -v ON_ERROR_STOP=1 -tAc "SELECT count(*) FROM public.media_asset WHERE storage = 'r2';")"
  if [ "$R2_ROWS" != 0 ]; then
    echo "Refusing Supabase -> R2: R2-backed rows exist. Complete R2 -> Supabase failback first." >&2
    exit 1
  fi
fi

case "$FROM->$DEST" in
  supabase-\>local)   media_rclone sync supabase:museum-media "$MIRROR_DIR/supabase" --log-file "$LOG" --log-format date,time ;;
  r2-\>local)         media_rclone sync r2:museum-media "$MIRROR_DIR/r2" --log-file "$LOG" --log-format date,time ;;
  supabase-\>r2)      media_rclone sync supabase:museum-media r2:museum-media --log-file "$LOG" --log-format date,time ;;
  r2-\>supabase)      media_rclone sync r2:museum-media supabase:museum-media --log-file "$LOG" --log-format date,time ;;
  volume-\>local)     mkdir -p "$MIRROR_DIR/volume"; docker compose cp "backend:/app/uploads/." "$MIRROR_DIR/volume/" ;;
  volume-\>r2)        mkdir -p "$MIRROR_DIR/volume"; docker compose cp "backend:/app/uploads/." "$MIRROR_DIR/volume/"; media_rclone sync "$MIRROR_DIR/volume" r2:museum-media --log-file "$LOG" --log-format date,time ;;
  r2-\>volume)        docker compose up -d backend > /dev/null; media_rclone sync r2:museum-media "$MIRROR_DIR/volume" --log-file "$LOG" --log-format date,time; docker compose cp "$MIRROR_DIR/volume/." backend:/app/uploads/ ;;
  supabase-\>volume)  docker compose up -d backend > /dev/null; media_rclone sync supabase:museum-media "$MIRROR_DIR/volume" --log-file "$LOG" --log-format date,time; docker compose cp "$MIRROR_DIR/volume/." backend:/app/uploads/ ;;
  volume-\>supabase)  mkdir -p "$MIRROR_DIR/volume"; docker compose cp "backend:/app/uploads/." "$MIRROR_DIR/volume/"; media_rclone sync "$MIRROR_DIR/volume" supabase:museum-media --log-file "$LOG" --log-format date,time ;;
  *) echo "unsupported: --from $FROM --dest $DEST"; echo "from: supabase|r2|volume   dest: local|r2|supabase|volume"; exit 1 ;;
esac
echo "[$(date +%F_%T)] mirror $FROM -> $DEST OK" | tee -a "$LOG"
