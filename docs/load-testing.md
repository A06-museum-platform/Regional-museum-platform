# Load testing

**Evaluation criterion (proposal §6):** *Concurrent User Capacity* — "Stable
response under 100 concurrent users; degrades gracefully and remains
available at 500."
**Source of the targets:** client questionnaire Q1 ("a fully functional
prototype capable of handling typical concurrent user load of 100") and Q2
("Max concurrent users expected: 500").

**Result: both targets met.** At 100 and at 500 concurrent users, **no
request failed** (0 of 7,370 and 0 of 46,325), and an independent probe
measured the server answering in **under 10 ms at the 95th percentile**
throughout. A separate race test confirmed that simultaneous bookings never
oversell an arrival window.

| | Typical — 100 users | Peak — 500 users |
|---|---:|---:|
| Duration (after a 10 s / 20 s ramp-up) | 3 min | 4 min |
| Requests | 7,370 | 46,325 |
| Throughput | 41 req/s | 193 req/s |
| **Failed requests** | **0 (0.00%)** | **0 (0.00%)** |
| Median response (load generator) | 4 ms | 4 ms |
| 95th percentile (load generator) | 9 ms | 28 ms |
| **Independent probe, 95th percentile** — opening hours / events list | **4.8 / 6.1 ms** | **6.8 / 8.9 ms** |
| Independent probe, slowest request | 11 ms | 20 ms |
| Sign-in, median | 360 ms | 1.7 s |
| Booking confirmation, median / 95th | 10 / 20 ms | 11 / 32 ms |

Raw results: `tests/load/results/` — Locust CSV and HTML reports per run,
the probe logs (`*_probe.txt`) and the race test output.

## Method

### Traffic model (`tests/load/locustfile.py`)

A simulated user is a person with the site open: they load a page, read it
for 3–8 seconds and move on. The mix follows the audience in the brief:

| Share | Who | What they do |
|---:|---|---|
| 75% | Public visitors | Home page (four API calls), collection search and object pages, events list and detail, exhibitions, plan-your-visit, checking booking availability |
| 20% | Signed-in members | Sign in once, open their account (membership, bookings, registrations, activity, recommendations), browse, and **book visits** (573 real bookings during the peak run) |
| 5% | Staff | Sign in once, front desk: today's summary and bookings, events list |

Every request goes through the real API to the real PostgreSQL database
loaded with the demo seed; nothing is cached or mocked.

### Configuration

| | |
|---|---|
| Machine | one cloud container: **2 vCPU**, 7 GB RAM — shared by the API, PostgreSQL 16 *and* the load generator |
| API | `uvicorn --workers 2 --timeout-keep-alive 75` — exactly the production command in `infra/Dockerfile.backend` |
| Database | PostgreSQL 16, default settings, SQLAlchemy async pool (5 + 10 overflow per worker) |
| Load generator | Locust 2.47, `FastHttpUser`, one process |
| Commands | `locust -f tests/load/locustfile.py --host http://localhost:8000 --headless -u 100 -r 10 -t 3m` and `-u 500 -r 25 -t 4m` |

The database was reset and re-seeded before each run.

### Why there are two latency measurements

The generator, the API and the database all shared two CPU cores. One Locust
process driving 500 users also has to schedule all of them, and the time a
request waits inside Locust before it is sent is counted in Locust's own
figures. That is why the generator's 99th percentile at 500 users (2.0 s)
looks very different from its median (4 ms).

To measure the server rather than the generator, `tests/load/probe.sh` ran
alongside each test as a separate client, requesting a page backed by a
database query four times a second. It never saw a slow response: the
slowest of 682 probe requests during the peak run took 20 ms, and the CPU
stayed 60–80% idle. The slow tail is therefore the load generator, not the
platform. Running the generator on a separate machine (or with Locust's
distributed mode across machines) would remove it from the figures.

### Concurrency correctness

`tests/load/race_last_places.py` fires 40 simultaneous bookings of two
tickets at one 60-place arrival window:

```
2026-11-04 09:00: 40 simultaneous attempts of 2 tickets
  201 created: 30
  400 INSUFFICIENT_TICKETS: 10
  places left afterwards: 0 (of 60)
PASS
```

Exactly 30 succeed and the rest are told the window is full: the
per-window advisory lock in `booking_service.create_booking` holds under
contention. Event registrations use a row lock on the event for the same
reason.

## Findings and changes made

- **Production server settings.** The image previously ran
  `uvicorn --reload` (a development setting: one process that watches the
  file system). It now runs 2 workers with no reload, configurable with
  `WEB_CONCURRENCY`; `docker-compose.yml` keeps `--reload` for development.
- **Keep-alive.** Uvicorn's default 5-second keep-alive is shorter than the
  time a visitor spends reading a page, so many next clicks had to open a new
  connection; at peak ramp-up this showed up as a handful of connection
  resets. Keep-alive is now 75 s; the final runs had none.
- **Sign-in is the slowest operation by design.** Passwords are hashed with
  bcrypt, which is deliberately expensive. At peak (125 sign-ins during a
  20-second ramp on two cores) the median was 1.7 s; in normal use it is
  about 0.35 s. More CPU or more workers reduce it; weakening the hash
  would not be the right fix.

## Interpreting the result for deployment

These figures come from a deliberately small machine with the load
generator competing for the same CPU, so they are a conservative lower
bound. The client's peak of 500 concurrent visitors produced about 190
requests per second; a single small host with 2 vCPU served that with no
errors and single-digit-millisecond server latency. For a public launch,
put the API behind the hosting provider's HTTPS proxy, keep at least 2
workers, and give PostgreSQL its own instance (see
`docs/handover/technical-maintenance-notes.md`).

## Re-running the tests

```bash
docker compose down -v && docker compose up -d --build   # fresh database
./scripts/apply_migrations.sh
docker compose exec -T db psql -U museum -d museum -v ON_ERROR_STOP=1 --single-transaction < database/seed/seed.sql
pip install locust httpx

tests/load/probe.sh http://localhost:8000 170 tests/load/results/typical_100_probe.txt &
locust -f tests/load/locustfile.py --host http://localhost:8000 --headless \
    -u 100 -r 10 -t 3m --csv tests/load/results/typical_100 --html tests/load/results/typical_100.html

# re-seed, then
locust -f tests/load/locustfile.py --host http://localhost:8000 --headless \
    -u 500 -r 25 -t 4m --csv tests/load/results/peak_500 --html tests/load/results/peak_500.html

python tests/load/race_last_places.py http://localhost:8000 40
```

Note: `docker-compose.yml` runs the API with `--reload` for development.
For figures comparable to these, start it with the production command:
`docker compose run --rm -p 8000:8000 backend sh -c "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --timeout-keep-alive 75 --no-access-log"`.
