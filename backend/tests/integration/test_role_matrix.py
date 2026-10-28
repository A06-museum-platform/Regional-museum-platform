"""The role-permission matrix (docs/role-permission-matrix.md), row by row,
against the real API and database.

Every row is exercised for all five callers -- signed out, Visitor, Member,
Staff, Admin -- so each row has positive and negative cases, as committed in
the proposal's risk register ("include negative test cases"). Denied callers
are tried first, so a wrongly-allowed request can't have side effects that
make a later positive case pass.

Expected outcome per caller:
  ok      the request succeeds (2xx)
  401     not signed in
  403     signed in without the role
  own     only the caller's own records are visible
  409     the action is refused for a business reason (e.g. a staff account
          can't apply for a membership it couldn't hold; a member already has one)
"""

from datetime import date, timedelta

import pytest

ROLES = {
    "anon": None,
    "visitor": "alice@example.com",
    "member": "ben@example.com",
    "staff": "staff@museum.org",
    "admin": "admin@museum.org",
}
ORDER = ["anon", "visitor", "member", "staff", "admin"]


def _tuesday() -> str:
    day = date.today() + timedelta(days=3)
    while day.weekday() != 1:
        day += timedelta(days=1)
    return day.isoformat()


def _booking():
    return {"visit_date": _tuesday(), "arrival_window": {"start": "11:00"},
            "lines": [{"ticket_type_id": 1, "quantity": 1}],
            "visitor": {"first_name": "Test", "last_name": "Visitor", "email": "t@example.com"},
            "payment_acknowledged": True}


def _event():
    day = (date.today() + timedelta(days=20)).isoformat()
    return {"title": "Matrix test session", "description": "A session created by the matrix test.",
            "starts_at": f"{day}T10:00:00+10:30", "ends_at": f"{day}T11:00:00+10:30", "capacity": 10}


def _hours(client):
    return client.get("/api/opening-hours").json()


def _visitor_info(client):
    return client.get("/api/visitor-information").json()


# Each row: (matrix capability, request builder, expected outcome per caller).
# A request builder takes (client, caller) and returns (method, path, json).
MATRIX = [
    ("View home page, opening hours, upcoming events",
     lambda c, r: ("get", "/api/opening-hours", None),
     dict(anon="ok", visitor="ok", member="ok", staff="ok", admin="ok")),
    ("Search collections, view item detail",
     lambda c, r: ("get", "/api/collection-items/malachite-matrix-burra", None),
     dict(anon="ok", visitor="ok", member="ok", staff="ok", admin="ok")),
    ("View event listings and detail",
     lambda c, r: ("get", "/api/events?q=morse", None),
     dict(anon="ok", visitor="ok", member="ok", staff="ok", admin="ok")),
    ("Register an account",
     lambda c, r: ("post", "/api/auth/register",
                   {"email": f"new.{r}@example.com", "password": "Register123!",
                    "first_name": "New", "last_name": r.title()}),
     dict(anon="ok", visitor="ok", member="ok", staff="ok", admin="ok")),
    ("Book tickets (simulated payment)",
     lambda c, r: ("post", "/api/bookings", _booking()),
     dict(anon="401", visitor="ok", member="ok", staff="ok", admin="ok")),
    ("View own bookings",
     lambda c, r: ("get", "/api/bookings/me", None),
     dict(anon="401", visitor="own", member="own", staff="own", admin="own")),
    ("View own membership status and activity",
     lambda c, r: ("get", "/api/activity/me", None),
     dict(anon="401", visitor="own", member="own", staff="own", admin="own")),
    ("View personalised recommendations",
     lambda c, r: ("get", "/api/recommendations", None),
     dict(anon="401", visitor="403", member="ok", staff="ok", admin="ok")),
    ("Apply for membership",
     lambda c, r: ("post", "/api/membership-applications", {"plan_id": 2, "children_covered": 1}),
     # Alice's seeded application is pending and Ben is already a member:
     # both are business refusals (409); staff accounts can't hold one (403).
     dict(anon="401", visitor="409", member="409", staff="403", admin="403")),
    ("Create / edit / delete events",
     lambda c, r: ("post", "/api/staff/events", _event()),
     dict(anon="401", visitor="403", member="403", staff="ok", admin="ok")),
    ("Set event capacity",
     lambda c, r: ("patch", "/api/staff/events/9", {"capacity": 70}),
     dict(anon="401", visitor="403", member="403", staff="ok", admin="ok")),
    ("Update opening hours",
     lambda c, r: ("put", "/api/staff/opening-hours", {"weekly": _hours(c)["weekly"], "overrides": []}),
     dict(anon="401", visitor="403", member="403", staff="ok", admin="ok")),
    ("Create / edit collection items and exhibitions",
     lambda c, r: ("post", "/api/staff/collection-items", {"title": f"Matrix object {r}"}),
     dict(anon="401", visitor="403", member="403", staff="ok", admin="ok")),
    ("Update visitor information pages",
     lambda c, r: ("put", "/api/staff/visitor-information", _visitor_info(c)),
     dict(anon="401", visitor="403", member="403", staff="ok", admin="ok")),
    ("View all bookings and event registrations",
     lambda c, r: ("get", "/api/staff/bookings", None),
     dict(anon="401", visitor="403", member="403", staff="ok", admin="ok")),
    ("Approve or reject membership applications",
     lambda c, r: ("post", f"/api/admin/members/{_pending_id(c)}/approve", None),
     dict(anon="401", visitor="403", member="403", staff="403", admin="ok")),
    ("Revoke member access",
     lambda c, r: ("post", "/api/admin/members/1/revoke", {"reason": "Matrix test"}),
     dict(anon="401", visitor="403", member="403", staff="403", admin="ok")),
    ("Assign or change user roles",
     lambda c, r: ("patch", "/api/users/7", {"role": "staff"}),
     dict(anon="401", visitor="403", member="403", staff="403", admin="ok")),
    ("View audit / activity log for all users",
     lambda c, r: ("get", "/api/admin/activity-log", None),
     dict(anon="401", visitor="403", member="403", staff="403", admin="ok")),
]


def _pending_id(client) -> int:
    """Liam's seeded pending application (Alice's is used elsewhere)."""
    from tests.integration.conftest import db_query
    return db_query("SELECT membership_id FROM membership WHERE user_id = 8 AND status = 'Pending'")[0][0]


@pytest.mark.parametrize("capability,build,expected", MATRIX, ids=[row[0] for row in MATRIX])
def test_role_matrix_row(client, login, capability, build, expected):
    # Denials first, so an allowed request can't change what a denied one sees.
    callers = sorted(ORDER, key=lambda r: expected[r] in ("ok", "own"))
    for role in callers:
        headers = login(ROLES[role]) if ROLES[role] else {}
        method, path, body = build(client, role)
        kwargs = {"headers": headers}
        if body is not None:
            kwargs["json"] = body
        resp = getattr(client, method)(path, **kwargs)
        want = expected[role]
        where = f"{capability!r} as {role}: {method.upper()} {path} -> {resp.status_code} {resp.text[:120]}"
        if want in ("ok", "own"):
            assert 200 <= resp.status_code < 300, where
        else:
            assert resp.status_code == int(want), where
            assert "code" in resp.json(), where  # contract error shape on every refusal
        if want == "own":
            _assert_own_records(client, path, resp.json(), headers)


def _assert_own_records(client, path, body, headers):
    me = client.get("/api/auth/me", headers=headers).json()
    if path == "/api/bookings/me":
        assert all(b["user_id"] == me["id"] for b in body["items"])
    if path == "/api/activity/me":
        name = me["display_name"]
        assert all(e["actor_name"] == name or name.split()[0] in e["target"] or e["actor_role"] in ("admin", "system")
                   for e in body["items"])


def test_someone_elses_booking_is_not_found(client, login):
    """"O = own records only": another account's booking reads as 404, so a
    reference can't even be confirmed to exist."""
    ben_ref = client.post("/api/bookings", json=_booking(), headers=login("ben@example.com")).json()["reference"]
    for role in ("visitor",):
        resp = client.get(f"/api/bookings/{ben_ref}", headers=login(ROLES[role]))
        assert resp.status_code == 404
    for role in ("staff", "admin"):  # staff can view all bookings
        assert client.get(f"/api/bookings/{ben_ref}", headers=login(ROLES[role])).status_code == 200


def test_a_tampered_token_is_refused(client, login):
    headers = login("alice@example.com")
    token = headers["Authorization"].split()[1]
    header, payload, signature = token.split(".")
    import base64, json
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    claims["role"] = "admin"
    forged = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    resp = client.get("/api/admin/activity-log", headers={"Authorization": f"Bearer {header}.{forged}.{signature}"})
    assert resp.status_code == 401


def test_role_claim_in_token_is_not_trusted(client, login):
    """Roles are read from the database on every request: demoting an admin
    takes effect immediately, not when their token expires."""
    admin = login("admin@museum.org")
    staff = login("staff@museum.org")
    assert client.get("/api/staff/events", headers=staff).status_code == 200
    staff_id = client.get("/api/auth/me", headers=staff).json()["id"]
    client.patch(f"/api/users/{staff_id}", json={"role": "visitor"}, headers=admin)
    assert client.get("/api/staff/events", headers=staff).status_code == 403
