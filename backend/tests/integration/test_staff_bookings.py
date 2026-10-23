"""Staff bookings and check-in, the today summary, and staff account roles."""


def test_staff_list_and_check_in_today(client, login):
    staff = login("staff@museum.org")
    today = client.get("/api/staff/today", headers=staff).json()
    assert today["bookings"]["bookings"] == 3 and today["bookings"]["checked_in"] == 1
    assert today["objects"] == 13 and today["pending_applications"] == 2

    listing = client.get("/api/staff/bookings", params={"date": today["date"]}, headers=staff).json()
    refs = {b["reference"]: b for b in listing["items"]}
    assert set(refs) == {"SARHN-10006", "SARHN-10007", "SARHN-10008"}
    assert refs["SARHN-10008"]["checked_in"] and not refs["SARHN-10006"]["checked_in"]

    done = client.post("/api/staff/bookings/SARHN-10006/check-in", headers=staff)
    assert done.status_code == 200 and done.json()["checked_in"]
    again = client.post("/api/staff/bookings/SARHN-10006/check-in", headers=staff)
    assert again.status_code == 409 and again.json()["code"] == "ALREADY_CHECKED_IN"
    future = client.post("/api/staff/bookings/SARHN-10004/check-in", headers=staff)
    assert future.status_code == 409 and future.json()["code"] == "NOT_TODAY"
    cancelled = client.post("/api/staff/bookings/SARHN-10005/check-in", headers=staff)
    assert cancelled.status_code == 409

    summary = client.get("/api/staff/bookings/summary", headers=staff).json()
    assert summary["checked_in"] == 2
    found = client.get("/api/staff/bookings", params={"q": "noah"}, headers=staff).json()
    assert [b["reference"] for b in found["items"]] == ["SARHN-10007"]


def test_staff_cancel_for_visitor(client, login):
    staff = login("staff@museum.org")
    resp = client.post("/api/staff/bookings/SARHN-10004/cancel", headers=staff)
    assert resp.status_code == 200 and resp.json()["status"] == "cancelled"


def test_staff_booking_routes_are_staff_only(client, login):
    ben = login("ben@example.com")
    for method, path in [("get", "/api/staff/bookings"), ("get", "/api/staff/today"),
                         ("get", "/api/staff/bookings/summary"),
                         ("post", "/api/staff/bookings/SARHN-10006/check-in")]:
        assert getattr(client, method)(path).status_code == 401
        assert getattr(client, method)(path, headers=ben).status_code == 403


def test_admin_manages_staff_roles(client, login):
    admin = login("admin@museum.org")
    team = client.get("/api/users", params={"role": "staff,admin"}, headers=admin).json()
    assert {u["email"] for u in team["items"]} == {"staff@museum.org", "admin@museum.org"}

    priya = client.get("/api/users", params={"q": "priya"}, headers=admin).json()["items"][0]
    assert priya["role"] == "member"
    promoted = client.patch(f"/api/users/{priya['id']}", json={"role": "staff"}, headers=admin).json()
    assert promoted["role"] == "staff"
    # Priya can now use the workspace.
    token = client.post("/api/auth/login", json={"email": priya["email"], "password": "Visitor123!"}).json()
    assert client.get("/api/staff/events", headers={"Authorization": f"Bearer {token['access_token']}"}).status_code == 200

    # Taking the staff role away leaves her an active member, not just a visitor.
    back = client.patch(f"/api/users/{priya['id']}", json={"role": "visitor"}, headers=admin).json()
    assert back["role"] == "member"

    me = client.get("/api/auth/me", headers=admin).json()
    assert client.patch(f"/api/users/{me['id']}", json={"role": "staff"}, headers=admin).status_code == 409
    log = client.get("/api/admin/activity-log", params={"action": "role.changed"}, headers=admin).json()
    assert log["total"] == 2
    assert client.get("/api/users", headers=login("staff@museum.org")).status_code == 403
