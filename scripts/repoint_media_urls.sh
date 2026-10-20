#!/usr/bin/env bash
# Repoint stored media URLs from one backend host to another after failover.
# Keys are identical across backends (same storage_key layout + rclone sync),
# so only the URL prefix changes — rows, owners and primaries are untouched.
#   ./scripts/repoint_media_urls.sh supabase r2     # Supabase outage: serve from R2
#   ./scripts/repoint_media_urls.sh r2 supabase     # failback when Supabase recovers
# Local compose db by default; prefix DB_TARGET=staging to repoint hosted rows.
# Backends and their URL prefixes live in backend/app/services/storage.py
# (public_url) — keep them in sync when that file changes.
set -euo pipefail
source "$(dirname "$0")/lib/db_target.sh"
_db_target_init

FROM="${1:?usage: repoint_media_urls.sh <supabase|r2|local> <supabase|r2|local>}"
TO="${2:?usage: repoint_media_urls.sh <supabase|r2|local> <supabase|r2|local>}"

# Each backend's variables are required only when that backend takes part —
# keyless local-only setups (the default) must work with empty env.
prefix_for() {
  case "$1" in
    supabase)
      : "${SUPABASE_URL:?repoint involves supabase: set SUPABASE_URL (or source .env)}"
      echo "${SUPABASE_URL%/}/storage/v1/object/public/${SUPABASE_BUCKET:-museum-media}/" ;;
    r2)
      : "${R2_PUBLIC_BASE:?repoint involves r2: set R2_PUBLIC_BASE (or source .env)}"
      echo "${R2_PUBLIC_BASE%/}/" ;;
    local)    echo "/uploads/" ;;
    *) echo "unknown backend: $1" >&2; exit 1 ;;
  esac
}

FROM_P="$(prefix_for "$FROM")"
TO_P="$(prefix_for "$TO")"

echo "Repointing media_asset.url: $FROM_P -> $TO_P"
db_psql -v ON_ERROR_STOP=1 --single-transaction \
  -v from_backend="$FROM" -v to_backend="$TO" \
  -v from_prefix="$FROM_P" -v to_prefix="$TO_P" <<'SQL'
UPDATE public.media_asset
SET url = :'to_prefix' || substring(url FROM char_length(:'from_prefix') + 1),
    storage = :'to_backend'
WHERE storage = :'from_backend'
  AND left(url, char_length(:'from_prefix')) = :'from_prefix';
SQL
db_psql -v ON_ERROR_STOP=1 -c \
  "SELECT storage, count(*) FROM media_asset GROUP BY 1;"
echo "Repoint OK — set MEDIA_BACKEND=${TO} and recreate the backend container."
