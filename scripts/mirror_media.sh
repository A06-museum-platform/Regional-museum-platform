#!/usr/bin/env bash
# Mirror media files between backends (Tier 1b). Run from the repo root.
#   ./scripts/mirror_media.sh                       # Supabase -> local mirror dir (default nightly)
#   ./scripts/mirror_media.sh --dest r2             # Supabase -> R2 warm standby
#   ./scripts/mirror_media.sh --dest supabase       # R2 -> Supabase (failback)
#   ./scripts/mirror_media.sh --from volume --dest r2    # uploads volume -> R2
#   ./scripts/mirror_media.sh --from volume              # uploads volume -> local mirror dir
#   ./scripts/mirror_media.sh --from r2 --dest volume    # R2 -> uploads volume (failback to local)
# Requires: rclone with S3 remotes named `supabase` and `r2`
# (Supabase S3 endpoint + R2 S3 endpoint; see docs/runbooks/media-ops.md).
# Volume transfers use `docker cp` (no extra dependencies) and need the
# backend container present (it is, whenever uploads happen).
# Cron example: 5 2 * * * cd /path/to/Regional-museum-platform && ./scripts/mirror_media.sh
set -euo pipefail

FROM="supabase"
DEST="local"
while [ $# -gt 0 ]; do
  case "$1" in
    --from) FROM="${2:-supabase}"; shift 2 ;;
    --dest) DEST="${2:-local}"; shift 2 ;;
    *) DEST="$1"; shift ;;
  esac
done

MIRROR_DIR="${MIRROR_DIR:-./backups/media}"
LOG="${LOG:-./backups/mirror.log}"
mkdir -p "$MIRROR_DIR"

case "$FROM->$DEST" in
  supabase-\>local)   rclone sync supabase:museum-media "$MIRROR_DIR" --log-file "$LOG" --log-format date,time ;;
  supabase-\>r2)      rclone sync supabase:museum-media r2:museum-media --log-file "$LOG" --log-format date,time ;;
  r2-\>supabase)      rclone sync r2:museum-media supabase:museum-media --log-file "$LOG" --log-format date,time ;;
  volume-\>local)     mkdir -p "$MIRROR_DIR/volume"; docker compose cp "backend:/app/uploads/." "$MIRROR_DIR/volume/" ;;
  volume-\>r2)        mkdir -p "$MIRROR_DIR/volume"; docker compose cp "backend:/app/uploads/." "$MIRROR_DIR/volume/"; rclone sync "$MIRROR_DIR/volume" r2:museum-media --log-file "$LOG" --log-format date,time ;;
  r2-\>volume)        docker compose up -d backend > /dev/null; rclone sync r2:museum-media "$MIRROR_DIR/volume" --log-file "$LOG" --log-format date,time; docker compose cp "$MIRROR_DIR/volume/." backend:/app/uploads/ ;;
  supabase-\>volume)  docker compose up -d backend > /dev/null; rclone sync supabase:museum-media "$MIRROR_DIR/volume" --log-file "$LOG" --log-format date,time; docker compose cp "$MIRROR_DIR/volume/." backend:/app/uploads/ ;;
  *) echo "unsupported: --from $FROM --dest $DEST"; echo "from: supabase|r2|volume   dest: local|r2|supabase|volume"; exit 1 ;;
esac
echo "[$(date +%F_%T)] mirror $FROM -> $DEST OK" | tee -a "$LOG"
