#!/usr/bin/env bash
# Restore local-mode uploads from the mirror dir into the docker volume.
# Usage: ./scripts/restore_media.sh   (uses MIRROR_DIR, default ./backups/media)
# Only meaningful for MEDIA_BACKEND=local rows; Supabase/R2 rows are
# unaffected (their bytes live in the cloud, restored via mirror_media.sh).
set -euo pipefail

MIRROR_DIR="${MIRROR_DIR:-./backups/media}"
test -d "$MIRROR_DIR" || { echo "mirror dir not found: $MIRROR_DIR"; exit 1; }

docker compose up -d backend > /dev/null
docker compose cp "$MIRROR_DIR/." backend:/app/uploads/
echo "Restored $(find "$MIRROR_DIR" -type f | wc -l) files into uploads-data volume."
echo "Verify: curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/uploads/<key>"
