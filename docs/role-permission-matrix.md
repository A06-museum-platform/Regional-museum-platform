# Role–permission matrix

This document is a **design artifact produced before implementation**, as
committed in the project proposal risk register. Every row below must have a
corresponding positive and negative test case in
`backend/tests/permissions/test_role_matrix.py`.

Legend: Y = permitted, — = denied (HTTP 403), O = own records only

| Capability | Visitor | Member | Staff | Admin |
|---|:--:|:--:|:--:|:--:|
| View home page, opening hours, upcoming events | Y | Y | Y | Y |
| Search collections, view item detail | Y | Y | Y | Y |
| View event listings and detail | Y | Y | Y | Y |
| Register an account | Y | — | — | — |
| Book tickets (simulated payment) | Y | Y | Y | Y |
| View own bookings | — | O | O | O |
| View own membership status and activity | — | O | O | O |
| View personalised recommendations | — | Y | Y | Y |
| Apply for membership | Y | — | — | — |
| Create / edit / delete events | — | — | Y | Y |
| Set event capacity | — | — | Y | Y |
| Update opening hours | — | — | Y | Y |
| Create / edit collection items and exhibitions | — | — | Y | Y |
| Update visitor information pages | — | — | Y | Y |
| View all bookings and event registrations | — | — | Y | Y |
| Approve or reject membership applications | — | — | — | Y |
| Revoke member access | — | — | — | Y |
| Assign or change user roles | — | — | — | Y |
| View audit / activity log for all users | — | — | — | Y |

## Enforcement

Authorisation is enforced server-side in `backend/app/core/permissions.py`
and applied as a FastAPI dependency at the **router level**, not per handler:

```python
router = APIRouter(
    prefix="/staff",
    dependencies=[Depends(require_role("staff", "admin"))],
)
```

Hiding a button in the React UI is a usability decision, never a security one.
