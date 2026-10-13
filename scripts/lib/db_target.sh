# Shared target selector for DB scripts (sourced, not executed).
# Default: the compose `db` container (local dev, zero config).
# Staging: set DATABASE_URL_STAGING (session-mode pooler URL + ?sslmode=require)
#   and every command below runs against hosted Supabase Postgres instead —
#   via a throwaway postgres:16 container, so no host psql is needed.
# Usage in scripts:  source "$(dirname "$0")/lib/db_target.sh"

_db_target_init() {
  # Hosted Supabase currently uses PG17; its pg_dump client must be >=17.
  DB_CLIENT_IMAGE="${DB_CLIENT_IMAGE:-postgres:17}"
  # Compose reads .env automatically; shell scripts do not. Read this one
  # setting as data, never source/evaluate the file. An explicit empty export
  # still forces local mode for offline recovery.
  if [ "${DATABASE_URL_STAGING+x}" != x ] && [ -f .env ]; then
    DATABASE_URL_STAGING="$(python3 - <<'PY'
from pathlib import Path
import shlex
value = ''
for line in Path('.env').read_text().splitlines():
    line = line.strip()
    if line.startswith('export '):
        line = line[7:].lstrip()
    key, sep, raw = line.partition('=')
    if sep and key.strip() == 'DATABASE_URL_STAGING':
        try:
            parts = shlex.split(raw, comments=True)
        except ValueError:
            raise SystemExit('Invalid quoting in DATABASE_URL_STAGING (value hidden)')
        if len(parts) > 1:
            raise SystemExit('DATABASE_URL_STAGING must be a single URL (value hidden)')
        value = parts[0] if parts else ''
print(value)
PY
)"
    export DATABASE_URL_STAGING
  fi
  if [ -n "${DATABASE_URL_STAGING:-}" ]; then
    DB_MODE="remote (DATABASE_URL_STAGING)"
  else
    DB_MODE="local compose db"
  fi
}

# db_psql [psql-args...] — SQL via -c or stdin; caller adds -c/-tAc/-v/-f.
db_psql() {
  if [ -n "${DATABASE_URL_STAGING:-}" ]; then
    docker run --rm -i postgres:16 psql "$DATABASE_URL_STAGING" "$@"
  else
    docker compose exec -T db psql -U museum -d museum "$@"
  fi
}

# db_is_remote — true when targeting staging.
db_is_remote() { test -n "${DATABASE_URL_STAGING:-}"; }

# db_stop_writers — free the database for DROP: stop local backend, or
# terminate other sessions on a remote target. Stop the local API in both
# modes: it can use staging too. External deployments must be stopped first.
db_stop_writers() {
  docker compose stop backend > /dev/null
  if db_is_remote; then
    db_psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity \
      WHERE datname = current_database() AND pid <> pg_backend_pid();"
  fi
}
