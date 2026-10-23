# Testing

How the platform is tested, what each layer proves, and the results at
hand-over to the evaluation phase (M6). Load testing and usability testing
have their own reports: `load-testing.md`, `usability-testing.md`.

## Summary (23 October 2026)

| Layer | Where | Count | Result |
|---|---|---:|---|
| Backend unit tests (fake database session) | `backend/tests/unit/` | 130 | all pass |
| Permission tests (fake session) | `backend/tests/permissions/` | 32 | all pass |
| **Integration tests (real PostgreSQL)** | `backend/tests/integration/` | 64 | all pass |
| — of which the role-permission matrix | `integration/test_role_matrix.py` | 22 (19 rows × 5 callers + 3) | all pass |
| Front-end unit tests | `frontend/tests/` | 3 | all pass |
| Front-end lint | `npm run lint` | — | 0 problems |
| Browser end-to-end checks (Playwright) | `tests/e2e/` | 6 scripts | all pass |
| Load: 100 / 500 users | `tests/load/` | 2 runs | 0 failed requests |
| Concurrency race (last places) | `tests/load/race_last_places.py` | 1 | pass — no overselling |
| **Total automated backend tests** | | **226** | **all pass, in CI on every pull request** |

## Layers

### Unit tests
Fast checks of single endpoints with a fake database session that answers
only the SQL it expects: validation, booking rules (limits, windows, member
tickets, horizon, museum-local "today"), authentication, storage backends.
They run without a database: `cd backend && pytest tests`.

### Integration tests
Run the real API in-process against a real PostgreSQL database that is
**dropped and rebuilt from `database/migrations` and `seed.sql` for every
test** — so every test also proves that the migrations and seed load
cleanly. They cover each feature end to end at the API: bookings (create,
list, cancel, capacity, member tickets), membership (apply, approve,
revoke, restore, register), content (search, filters, drafts hidden), staff
management (event publishing workflow, capacity and delete guards, object
and exhibition CRUD, opening hours that close booking dates, visitor
information), event registration, the member portal (recommendations,
interests, own activity), staff bookings and check-in, staff roles.

They only touch a database whose name ends in `_test`, and are skipped when
none is available:
```bash
TEST_DATABASE_URL=postgresql://museum:museum@localhost:5432/museum_test pytest tests
```

### Role-permission matrix
Every row of `role-permission-matrix.md` is exercised for signed-out,
Visitor, Member, Staff and Admin callers; denials are tried before
permitted calls, and every refusal must carry the `{detail, code}` shape.
Extra checks: another account's booking is a 404; a token with an edited
role claim is rejected; demoting an account takes effect on its next
request. This is the evidence for the evaluation criterion *Role-Based
Access Control* ("all role-permission test cases pass; no privileged
endpoint reachable without the required role").

### Browser end-to-end checks
Playwright scripts drive the real UI against the running stack (see
`tests/e2e/README.md`): every route as every role with no API errors; the
booking flow including sign-in mid-flow and cancellation; staff publishing a
session that a visitor then registers for; account creation; phone-width
layout; the member portal; front-desk check-in and admin role changes.
They are the evidence for *Functional Prototype Demonstration* and, for
staff, the automated half of *Content Manageability*.

### Continuous integration
`.github/workflows/ci.yml` runs on every pull request and every push to
`dev`/`main`: backend unit + integration tests against a PostgreSQL 16
service container, front-end lint, unit tests and build. A pull request
can't be merged green if any of them fail.

## Defects found and fixed during testing

| Defect | Found by | Fix |
|---|---|---|
| Migration 008 missing from `dev` — `POST /api/bookings` failed on a fresh database | integration tests on a real database | restored from the backend branch (PR #22) |
| Front end read errors as `{error: {...}}`; every real error showed "Something went wrong" | browser check with mocks off | client reads `{detail, code}`; global handlers give every error that shape |
| Saving a draft event without dates crashed the editor | code review during wiring | dates required for drafts too |
| Visitor accounts opening `/account` saw a "staff only" refusal | role crawl | route opened to visitor and member accounts |
| Header collection search did nothing | browser check | wired to `/collections?q=` |
| Brief crash when choosing a session on the registrations tab | browser check | `useAsync` rewritten so loading is derived from the request key |
| Production image ran `uvicorn --reload`; 5 s keep-alive caused resets under load | load test | multi-worker production command, 75 s keep-alive |
| CI never ran on stacked pull requests | review of CI history | trigger on every pull request |
| CI couldn't import the app (`/app/uploads` missing on the runner) | first CI run | upload directory optional outside the container |

## Running everything

```bash
# backend
cd backend && TEST_DATABASE_URL=postgresql://museum:museum@localhost:5432/museum_test pytest tests
# front end
cd frontend && npm run lint && npm test && npm run build
# browser checks (stack running, fresh seed)
./tests/e2e/run_all.sh
# load
locust -f tests/load/locustfile.py --host http://localhost:8000 --headless -u 100 -r 10 -t 3m
```
