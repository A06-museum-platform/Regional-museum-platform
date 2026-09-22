#!/usr/bin/env bash
# Repoint stored media URLs from one backend host to another after failover.
# Keys are identical across backends (same storage_key layout + rclone sync),
# so only the URL prefix changes — rows, owners and primaries are untouched.
#   ./scripts/repoint_media_urls.sh supabase r2     # Supabase outage: serve from R2
#   ./scripts/repoint_media_urls.sh r2 supabase     # failback when Supabase recovers
# Backends and their URL prefixes live in backend/app/services/storage.py
# (public_url) — keep them in sync when that file changes.
set -euo pipefail

FROM="${1:?usage: repoint_media_urls.sh <supabase|r2|local> <supabase|r2|local>}"
TO="${2:?usage: repoint_media_urls.sh <supabase|r2|local> <supabase|r2|local>}"

SUPABASE_URL="${SUPABASE_URL:?set SUPABASE_URL (or source .env)}"
SUPABASE_BUCKET="${SUPABASE_BUCKET:-museum-media}"
R2_PUBLIC_BASE="${R2_PUBLIC_BASE:?set R2_PUBLIC_BASE (or source .env)}"

prefix_for() {
  case "$1" in
    supabase) echo "${SUPABASE_URL%/}/storage/v1/object/public/${SUPABASE_BUCKET}/" ;;
    r2)       echo "${R2_PUBLIC_BASE%/}/" ;;
    local)    echo "/uploads/" ;;
    *) echo "unknown backend: $1" >&2; exit 1 ;;
  esac
}

FROM_P="$(prefix_for "$FROM")"
TO_P="$(prefix_for "$TO")"

echo "Repointing media_asset.url: $FROM_P -> $TO_P"
docker compose exec -T db psql -U museum -d museum -c \
  "UPDATE media_asset SET url = regexp_replace(url, '^${FROM_P}', '${TO_P}') WHERE storage = '${FROM}';"
docker compose exec -T db psql -U museum -d museum -c \
  "UPDATE media_asset SET storage = '${TO}' WHERE storage = '${FROM}';"
docker compose exec -T db psql -U museum -d museum -c \
  "SELECT storage, count(*) FROM media_asset GROUP BY 1;"
echo "Repoint OK — set MEDIA_BACKEND=${TO} and recreate the backend container."
