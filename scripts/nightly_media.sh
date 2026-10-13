#!/usr/bin/env bash
# Run on a cloud runner or ops host after the database dump.
set -euo pipefail
cd "$(dirname "$0")/.."
source ./scripts/lib/media_rclone.sh
./scripts/mirror_media.sh
./scripts/mirror_media.sh --dest r2
media_rclone check supabase:museum-media r2:museum-media --download
media_rclone check supabase:museum-media backups/media/supabase --download
