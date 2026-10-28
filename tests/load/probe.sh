#!/usr/bin/env bash
# Independent latency probe: while a load test runs, request one public
# endpoint (with a DB query) and the DB-free liveness check four times a
# second and record how long each took. The probe is a separate client, so
# it measures the server, not the load generator's own scheduling delay.
# Usage: tests/load/probe.sh http://localhost:8000 SECONDS OUTFILE
HOST=${1:-http://localhost:8000}; SECONDS_TO_RUN=${2:-180}; OUT=${3:-probe.txt}
: > "$OUT"
end=$(( $(date +%s) + SECONDS_TO_RUN ))
while [ "$(date +%s)" -lt "$end" ]; do
  a=$(curl -s -o /dev/null -w "%{http_code} %{time_total}" "$HOST/api/opening-hours")
  e=$(curl -s -o /dev/null -w "%{http_code} %{time_total}" "$HOST/api/events?page_size=10")
  echo "$(date +%s) $a $e" >> "$OUT"
  sleep 0.25
done
