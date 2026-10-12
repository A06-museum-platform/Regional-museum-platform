# Shared target selector for DB scripts (sourced, not executed).
# Default: the compose `db` container (local dev, zero config).
# Staging: set DATABASE_URL_STAGING (session-mode pooler URL + ?sslmode=require)
#   and every command below runs against hosted Supabase Postgres instead —
#   via a throwaway postgres:16 container, so no host psql is needed.
# Usage in scripts:  source "$(dirname "$0")/lib/db_target.sh"

_db_target_init() {
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
# terminate other sessions on a remote target (no compose backend to stop).
db_stop_writers() {
  if db_is_remote; then
    db_psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity \
      WHERE datname = current_database() AND pid <> pg_backend_pid();"
  else
    docker compose stop backend > /dev/null
  fi
}
