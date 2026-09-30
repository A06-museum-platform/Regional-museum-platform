# API Contract — Regional Museum Platform

Status: **frozen at Gate G2**. Owner: Ray. Reviewers: Harbor, Rock.

Transcribed from the "API Contract Reference" box on each of Sun's nine flow
diagrams (`docs/diagrams/`). Sections 1–9 below map 1:1 to Flow 1–Flow 9.
Section 10 extends the same rules to the handful of endpoints the matrix in
`docs/role-permission-matrix.md` requires but that weren't drawn as their own
flow. Nothing here should change without updating this file first.

---

## 0. Conventions (from every flow's Notes panel)

| Rule | Value |
|---|---|
| Prefix | every path starts with `/api` |
| URL paths | `kebab-case` — e.g. `/api/membership-plans`, `/api/membership-applications` |
| JSON fields | `snake_case` — e.g. `display_name`, `thumbnail_url`, `access_token` |
| List response | always `{ items, total, page, size }` |
| List query params | `?page=&size=` |
| Error response | always `{ detail, code }` |
| Time format | ISO 8601 UTC — e.g. `2026-09-11T14:30:00Z` |
| Every flow | at least one success path and one failure path |
| Role-gated endpoints | check the role server-side and return `403` when denied |

Role scopes used below: **Public** (no token), **Authenticated** (any of
Member / Staff / Admin), **Member** (Member / Staff / Admin — "Member" is the
lowest of the three gated roles, Staff and Admin inherit it), **Staff**
(Staff / Admin), **Admin** (Admin only).

---

## 1. Auth — Login (Flow 1)

### `POST /api/auth/login`
**Role**: Public

Request:
```json
{ "email": "user@example.com", "password": "********" }
```
Success `200`:
```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": { "id": 1, "email": "user@example.com", "display_name": "...", "role": "member" }
}
```
Failure:
| Scenario | Status | Body |
|---|---|---|
| Incorrect email or password | 401 | `{ "detail": "Incorrect email or password", "code": "AUTH_INVALID" }` |
| Account has been disabled | 403 | `{ "detail": "Account has been disabled", "code": "ACCOUNT_DISABLED" }` |

Front end redirects by `user.role` after a successful login (member / staff / admin dashboard).

---

## 2. Collections — List / Search / Detail (Flow 2)

### `GET /api/collections`
**Role**: Public
Query: `?q={keyword}&tag={tag}&page={page}&size={size}`
Success `200`:
```json
{ "items": [ { "id": 123, "display_name": "...", "thumbnail_url": "...", "description": "..." } ], "total": 100, "page": 1, "size": 12 }
```
Failure: no matches → still `200` with `items: []` (front end shows "No matching collections found"); malformed `page`/`size` → `400` `{ "detail": "...", "code": "VALIDATION_ERROR" }`.

### `GET /api/collections/{id}`
**Role**: Public
Success `200`: `{ "id": 123, "display_name": "...", "thumbnail_url": "...", "description": "..." }`
Failure: `404` `{ "detail": "Collection not found", "code": "NOT_FOUND" }`

---

## 3. Events — List / Search / Detail (Flow 3)

### `GET /api/events`
**Role**: Public
Query: `?q={keyword}&tag={tag}&page={page}&size={size}`
Success `200`: `{ "items": [ { "id": 123, "display_name": "...", "event_time": "2026-09-11T14:30:00Z", "description": "...", "location": "...", "thumbnail_url": "..." } ], "total": 100, "page": 1, "size": 12 }`
Failure: no matches → `200` with `items: []`; malformed query → `400`.

### `GET /api/events/{id}`
**Role**: Public
Success `200`: same shape as a list item.
Failure: `404` `{ "detail": "Event not found", "code": "NOT_FOUND" }`

---

## 4. Event Registration (Flow 4)

### `POST /api/events/{id}/register`
**Role**: Member (Member / Staff / Admin — front end redirects to login first if the user isn't signed in)

Request:
```json
{ "quantity": 1 }
```
Success `200`:
```json
{ "id": 1, "event_id": 123, "event_name": "...", "event_time": "2026-09-11T14:30:00Z", "quantity": 1, "status": "registered" }
```
Failure:
| Scenario | Status | code |
|---|---|---|
| Invalid quantity / event doesn't exist | 400 | `VALIDATION_ERROR` |
| Event is full | 409 | `EVENT_FULL` — `{ "detail": "Event is full", "code": "EVENT_FULL" }` |

Registering updates the event's confirmed-registration count in the same transaction that creates the registration row.

---

## 5. Ticket Booking (Flow 5)

### `POST /api/events/{id}/bookings`
**Role**: Member (Member / Staff / Admin — same login gate as registration)

Request:
```json
{ "quantity": 2 }
```
Success `200`:
```json
{
  "id": 1, "event_id": 123, "quantity": 2, "status": "confirmed",
  "booking_time": "2026-09-11T14:30:00Z",
  "event": { "id": 123, "event_name": "...", "event_time": "2026-09-11T14:30:00Z", "location": "..." }
}
```
Failure:
| Scenario | Status | code |
|---|---|---|
| Not enough tickets available | 400 | `INSUFFICIENT_TICKETS` — `{ "detail": "Not enough tickets available", "code": "INSUFFICIENT_TICKETS" }` |
| Booking limit reached | 409 | `BOOKING_LIMIT_EXCEEDED` — `{ "detail": "Booking limit reached", "code": "BOOKING_LIMIT_EXCEEDED" }` |

---

## 6. Membership (Flow 6)

### `GET /api/membership-plans`
**Role**: Public
Query: `?page={page}&size={size}`
Success `200`: `{ "items": [ { "id": 1, "display_name": "Student Plan", "price": 0, "duration_months": 12 } ], "total": 10, "page": 1, "size": 12 }`

### `POST /api/membership-applications`
**Role**: Member (per Flow 6's note the applicant must already be signed in — the "Visitor" column in the diagram is for *browsing* plans, applying itself is gated)

Request: `{ "plan_id": 1 }`
Success `200`: `{ "id": 1, "plan_id": 1, "status": "pending", "applied_at": "2026-09-11T14:30:00Z", "plan": { "id": 1, "display_name": "Student Plan" } }`
Failure:
| Scenario | Status | code |
|---|---|---|
| Invalid `plan_id` | 400 | `INVALID_REQUEST` — `{ "detail": "Invalid plan_id", "code": "INVALID_REQUEST" }` |
| Plan not found | 404 | `NOT_FOUND` — `{ "detail": "Membership plan not found", "code": "NOT_FOUND" }` |
| Already has an active membership | 409 | `MEMBERSHIP_ACTIVE` — `{ "detail": "User already has an active membership", "code": "MEMBERSHIP_ACTIVE" }` |

---

## 7. Recommendations (Flow 7)

### `GET /api/recommendations`
**Role**: Member
Query: `?page={page}&size={size}`
Success `200`: `{ "items": [...], "total": 6, "page": 1, "size": 12 }` — interest-based, matched against the member's tagged interests.
Failure: not a member → `403` `{ "detail": "Member access required", "code": "FORBIDDEN" }`

---

## 8. Staff Content Management (Flow 8)

Same create/update pattern for **exhibitions, collections and events** — Flow 8 draws it once for exhibitions; the other two resources follow identically.

### `POST /api/exhibitions` (create)
**Role**: Staff
Request: `{ "title": "...", "description": "...", "status": "draft" | "published" }`
Success `200`: `{ "id": 123, "title": "...", "description": "...", "status": "published", "created_at": "2026-09-11T10:00:00Z", "created_by": 5 }`

### `PUT /api/exhibitions/{id}` (update)
**Role**: Staff
Request: `{ "title": "...", "description": "...", "status": "draft" | "published" }`
Success `200`: same shape, plus `updated_at`.

### `DELETE /api/exhibitions/{id}`
**Role**: Staff
Success `204`, no body — not drawn in Flow 8 but required for CRUD completeness / the role matrix's "create / edit / delete" wording.

Failure (all three, and their `/api/collections` and `/api/events` equivalents):
| Scenario | Status | code |
|---|---|---|
| Invalid data | 400 | `VALIDATION_ERROR` |
| Not signed in / wrong role | 403 | `FORBIDDEN` |
| Not found (PUT/DELETE) | 404 | `NOT_FOUND` |
| Unexpected server error | 500 | `INTERNAL_ERROR` |

---

## 9. Admin — User & Access Management (Flow 9)

### `GET /api/users`
**Role**: Admin
Query: `?page={page}&size={size}`
Success `200`: `{ "items": [...], "total": 100, "page": 1, "size": 20 }`
Failure: `403` `{ "detail": "Admin access required", "code": "FORBIDDEN" }`

### `PATCH /api/users/{id}`
**Role**: Admin
Request (any subset): `{ "role": "staff", "is_active": false, "access_status": "disabled" }`
Success `200`: `{ "id": 12, "email": "user@example.com", "display_name": "John Doe", "role": "staff", "is_active": true, "access_status": "active" }`
Failure:
| Scenario | Status | code |
|---|---|---|
| Invalid input data | 422 | `VALIDATION_ERROR` — `{ "detail": "Invalid input data", "code": "VALIDATION_ERROR" }` |
| User not found | 404 | `USER_NOT_FOUND` — `{ "detail": "User not found", "code": "USER_NOT_FOUND" }` |
| Not an admin | 403 | `FORBIDDEN` — `{ "detail": "Admin access required", "code": "FORBIDDEN" }` |

---

## 10. Extended to match the four-role matrix (not their own flow diagram, same conventions)

`docs/role-permission-matrix.md` requires a few capabilities no flow was drawn for. Same rules apply (`/api` prefix, snake_case, `{items,total,page,size}`, `{detail,code}`):

| Method | Path | Role | Notes |
|---|---|---|---|
| POST | `/api/auth/register` | Public | `{ email, password, first_name, last_name }` → `201` user object; `409 CONFLICT` if email taken |
| POST | `/api/auth/logout` | Authenticated | `204`, no body |
| GET | `/api/auth/me` | Authenticated | same `user` shape as login |
| GET | `/api/opening-hours` | Public | `200` weekly array |
| PUT | `/api/opening-hours` | Staff | `200`; `403` if not staff |
| GET | `/api/visitor-information` | Public | `200` facilities/accessibility text |
| PUT | `/api/visitor-information` | Staff | `200`; `403` if not staff |
| GET | `/api/events/{id}/bookings` | Staff | list bookings for one event, `403` if not staff |
| GET | `/api/membership-applications` | Admin | `?status=pending&page=&size=`; `403` if not admin |
| POST | `/api/membership-applications/{id}/approve` \| `/reject` | Admin | `200` updated application; `404`/`409` |
| GET | `/api/activity-log` | Admin | own-activity variant is `/api/activity/me` (Authenticated) |

**Out of scope for this release: `POST /api/auth/refresh`.** Login returns
only a short-lived `access_token` (lifetime set by
`ACCESS_TOKEN_EXPIRE_MINUTES`), with no `refresh_token`. When it expires,
`GET /api/auth/me` returns `401` and the front end sends the user back to
sign in. Adding refresh later means issuing a `refresh_token` from
`/api/auth/login` and then adding this endpoint.

---

## 11. Follow-ups before parallel development starts

These are real gaps between this contract and what's already in the repo — they don't block freezing this document, but they block integration:

1. **`frontend/src/api/collections.js` and `events.js` already ship real code against a *different* shape**: `/collection-items` (not `/collections`), slug-based detail lookup (not numeric `id`), `page_size` (not `size`), and an `{ error: { code, message, reference, fields } }` envelope (not `{ detail, code }`). This contract follows the flow diagrams, so those two files — and their mocks — need to be updated to match before integration, not the other way around.
2. **`backend/app/api/member/activity.py`'s `register_for_event`** and **`backend/app/api/member/bookings.py`** already exist as stubs but use a generic `/events/{id}/register` and standalone `/bookings` with `slot_id` — neither matches Flow 4/5's `/api/events/{id}/register` and `/api/events/{id}/bookings` shape. Needs rework.
3. **Error envelope isn't implemented anywhere yet.** Current backend routes raise `HTTPException` and get FastAPI's default `{"detail": "..."}` with no `code`. A global exception handler needs to attach `code` to match this contract.
4. **`app/schemas/common.py` (`PaginatedResponse`)** doesn't exist yet; when it's written it needs `size`, not `page_size`, to match this contract.
