#!/usr/bin/env bash
# Restore local-mode uploads from the mirror dir into the docker volume.
# Usage: ./scripts/restore_media.sh   (uses MIRROR_DIR, default ./backups/media)
# Only meaningful for MEDIA_BACKEND=local rows; Supabase/R2 rows are
# unaffected (their bytes live in the cloud, restored via mirror_media.sh).
set -euo pipefail

# mirror_media.sh --from volume writes under <mirror>/volume/ (the key
# layout starts below it), so restore from that subdir — copying the whole
# mirror dir would nest an extra `volume/` path and restored URLs 404.
SOURCE="${1:-volume}"
case "$SOURCE" in
  volume|supabase|r2) ;;
  *) echo "usage: restore_media.sh [volume|supabase|r2]" >&2; exit 1 ;;
esac
SRC_DIR="${MIRROR_DIR:-./backups/media}/$SOURCE"
test -d "$SRC_DIR" || { echo "mirror volume dir not found: $SRC_DIR (run mirror_media.sh --from volume first)"; exit 1; }

docker compose up -d backend > /dev/null
docker compose cp "$SRC_DIR/." backend:/app/uploads/
echo "Restored $(find "$SRC_DIR" -type f | wc -l) files into uploads-data volume."
echo "Verify: curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/uploads/<key>"
