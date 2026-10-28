# Role–permission matrix

This matrix was produced **before implementation**, as committed in the
project proposal's risk register, and confirmed against the client's
answers (staff create and edit events and update opening hours;
administrators revoke member access; role-based access control).

Every row is tested for **all five callers** — signed out, Visitor, Member,
Staff, Admin — in `backend/tests/integration/test_role_matrix.py`, against
the real API and a freshly seeded database. A row passes only if every
permitted caller succeeds *and* every other caller is refused with the
contract's `{detail, code}` error.

Legend: **Y** permitted · **—** refused (401 signed out, 403 wrong role) ·
**O** own records only · **B** refused for a business reason (409)

"Visitor" is a signed-in account without a membership. Someone browsing
without an account is "signed out".

| # | Capability | Signed out | Visitor | Member | Staff | Admin | Endpoint tested |
|---|---|:--:|:--:|:--:|:--:|:--:|---|
| 1 | View home page, opening hours, upcoming events | Y | Y | Y | Y | Y | `GET /api/opening-hours` |
| 2 | Search collections, view item detail | Y | Y | Y | Y | Y | `GET /api/collection-items/{slug}` |
| 3 | View event listings and detail | Y | Y | Y | Y | Y | `GET /api/events?q=` |
| 4 | Register an account | Y | Y¹ | Y¹ | Y¹ | Y¹ | `POST /api/auth/register` |
| 5 | Book tickets (simulated payment) | —² | Y | Y | Y | Y | `POST /api/bookings` |
| 6 | View own bookings | — | O | O | O | O | `GET /api/bookings/me` |
| 7 | View own membership status and activity | — | O | O | O | O | `GET /api/activity/me`, `GET /api/memberships/me` |
| 8 | View personalised recommendations | — | — | Y | Y | Y | `GET /api/recommendations` |
| 9 | Apply for membership | — | Y³ | B | — | — | `POST /api/membership-applications` |
| 10 | Create / edit / delete events | — | — | — | Y | Y | `POST/PATCH/DELETE /api/staff/events` |
| 11 | Set event capacity | — | — | — | Y | Y | `PATCH /api/staff/events/{id}` |
| 12 | Update opening hours | — | — | — | Y | Y | `PUT /api/staff/opening-hours` |
| 13 | Create / edit collection items and exhibitions | — | — | — | Y | Y | `/api/staff/collection-items`, `/api/staff/exhibitions` |
| 14 | Update visitor information pages | — | — | — | Y | Y | `PUT /api/staff/visitor-information` |
| 15 | View all bookings and event registrations | — | — | — | Y | Y | `GET /api/staff/bookings`, `GET /api/staff/events/{id}/registrations` |
| 16 | Approve or reject membership applications | — | — | — | — | Y | `POST /api/admin/members/{id}/approve` |
| 17 | Revoke member access | — | — | — | — | Y | `POST /api/admin/members/{id}/revoke` |
| 18 | Assign or change user roles | — | — | — | — | Y | `PATCH /api/users/{id}` |
| 19 | View audit / activity log for all users | — | — | — | — | Y | `GET /api/admin/activity-log` |

1. Anyone may create a further account with a different email; the
   interface only offers it to signed-out visitors.
2. Choosing a date and tickets is public; confirming the booking needs an
   account so the pass and its cancellation belong to someone.
3. One application at a time. In the seed data Alice already has a pending
   application, so the test sees the business refusal (409); a visitor
   without one gets 200 (`test_membership_flow.py`). Staff and
   administrator accounts can't hold a membership (403).

Further checks in the same file:

- another account's booking reads as **404**, not 403, so a reference can't
  be confirmed to exist; staff and admins can open any booking;
- a token whose role claim was edited is rejected (**401**) — the
  signature no longer matches;
- roles are read from the database on **every request**, so demoting an
  account takes effect immediately, not when its token expires.

## Enforcement

Authorisation is enforced server-side in `backend/app/api/deps.py`
(`get_current_user`, `require_staff`, `require_admin`) and applied as a
FastAPI dependency at the **router level**, so no handler in a staff or
admin router can forget it:

```python
router = APIRouter(
    prefix="/api/staff/events",
    dependencies=[Depends(require_staff)],
)
```

The role comes from the `user_role` table, never from the token. Hiding a
button in the React UI (`RoleGuard`, the staff sidebar) is a usability
decision, never a security one.
