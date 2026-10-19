# Shared target selector for DB scripts (sourced, not executed).
# Default: the compose `db` container (local dev, zero config).
# Staging is an explicit per-command opt-in from the shell:
#   DB_TARGET=staging ./scripts/<script>.sh
# DB_TARGET is read from the environment only; .env is never consulted for
# it, so a URL saved in .env cannot silently select the hosted database.
# With DB_TARGET=staging, DATABASE_URL_STAGING (session-mode pooler URL +
# ?sslmode=require) comes from the environment or, failing that, is read
# from .env as data. Commands then run against hosted Supabase Postgres via
# a throwaway postgres container, so no host psql is needed.
# Usage in scripts:  source "$(dirname "$0")/lib/db_target.sh"; _db_target_init

_db_target_init() {
  # Hosted Supabase currently uses PG17; its pg_dump client must be >=17.
  DB_CLIENT_IMAGE="${DB_CLIENT_IMAGE:-postgres:17}"
  DB_TARGET="${DB_TARGET:-local}"
  case "$DB_TARGET" in
    local)
      DB_REMOTE=0
      DB_MODE="local compose db"
      ;;
    staging)
      # Compose reads .env automatically; shell scripts do not. Read this one
      # setting as data, never source/evaluate the file. An exported value
      # takes precedence.
      if [ -z "${DATABASE_URL_STAGING:-}" ] && [ -f .env ]; then
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
)" || exit 1
      fi
      if [ -z "${DATABASE_URL_STAGING:-}" ]; then
        echo "DB_TARGET=staging but DATABASE_URL_STAGING is empty (not exported and not set in .env)." >&2
        exit 1
      fi
      export DATABASE_URL_STAGING
      DB_REMOTE=1
      DB_MODE="REMOTE staging (DATABASE_URL_STAGING)"
      ;;
    *)
      echo "Unknown DB_TARGET='$DB_TARGET' (expected: local or staging)." >&2
      exit 1
      ;;
  esac
  # Child scripts (e.g. restore -> apply_migrations) inherit the same target.
  export DB_TARGET
  echo "DB target: $DB_MODE" >&2
}

# db_psql [psql-args...] — SQL via -c or stdin; caller adds -c/-tAc/-v/-f.
db_psql() {
  if db_is_remote; then
    docker run --rm -i postgres:16 psql "$DATABASE_URL_STAGING" "$@"
  else
    docker compose exec -T db psql -U museum -d museum "$@"
  fi
}

# db_is_remote — true only when DB_TARGET=staging was selected.
db_is_remote() { [ "${DB_REMOTE:-0}" = 1 ]; }

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
