# Load test scenarios

| Scenario | Users | Ramp | Duration | Pass criterion (proposal §6) |
|---|---:|---:|---:|---|
| Typical | 100 | 10/s | 3 min | Stable: no failed requests, 95th percentile well under 1 s |
| Peak | 500 | 25/s | 4 min | Degrades gracefully and stays available: failure rate below 1%, every page still answered |
| Last places race | 40 simultaneous bookings | — | — | A 60-place window sells exactly 30 two-ticket bookings; the rest get `INSUFFICIENT_TICKETS`, never a 500 |

User mix (see `locustfile.py`): 75% public visitors browsing, 20% signed-in
members (account page, recommendations, booking), 5% staff (front desk).
Think time 3–8 s per page (staff 5–12 s).

Results and method: `docs/load-testing.md`. Raw output: `results/`.
