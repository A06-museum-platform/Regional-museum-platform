#!/usr/bin/env bash
# Mirror media files between backends (Tier 1b). Run from the repo root.
#   ./scripts/mirror_media.sh               # Supabase -> local mirror dir (default)
#   ./scripts/mirror_media.sh --dest r2     # Supabase -> R2 warm standby
#   ./scripts/mirror_media.sh --dest supabase  # R2 -> Supabase (failback)
# Requires: rclone with S3 remotes named `supabase` and `r2`
# (Supabase S3 endpoint + R2 S3 endpoint; see docs/runbooks/media-ops.md).
# Cron example: 5 2 * * * cd /path/to/Regional-museum-platform && ./scripts/mirror_media.sh
set -euo pipefail

# Allow both `./mirror_media.sh r2` and `./mirror_media.sh --dest r2`.
DEST="local"
if [ "${1:-}" = "--dest" ]; then DEST="${2:-local}"; elif [ -n "${1:-}" ]; then DEST="$1"; fi
MIRROR_DIR="${MIRROR_DIR:-./backups/media}"
LOG="${LOG:-./backups/mirror.log}"
mkdir -p "$MIRROR_DIR"

case "$DEST" in
  local)   rclone sync supabase:museum-media "$MIRROR_DIR" --log-file "$LOG" --log-format date,time ;;
  r2)      rclone sync supabase:museum-media r2:museum-media --log-file "$LOG" --log-format date,time ;;
  supabase) rclone sync r2:museum-media supabase:museum-media --log-file "$LOG" --log-format date,time ;;
  *) echo "unknown dest: $DEST (local|r2|supabase)"; exit 1 ;;
esac
echo "[$(date +%F_%T)] mirror -> $DEST OK" | tee -a "$LOG"
