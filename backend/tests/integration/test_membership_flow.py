"""Membership end to end on a real database: a visitor applies, an
administrator approves, and the account becomes a member who can book
Member tickets; revoking disables the account until it is restored."""


def test_apply_approve_revoke(client, login):
    # Seed: Alice already has a pending Individual application.
    alice = login("alice@example.com")
    application = client.get("/api/memberships/me", headers=alice).json()
    assert application["status"] == "pending"
    assert client.get("/api/auth/me", headers=alice).json()["role"] == "visitor"

    # A second application while one is pending is refused.
    again = client.post("/api/membership-applications", json={"plan_id": 1}, headers=alice)
    assert again.status_code == 409

    admin = login("admin@museum.org")
    pending = client.get("/api/admin/members", params={"status": "pending"}, headers=admin).json()
    assert application["id"] in [m["id"] for m in pending["items"]]

    approved = client.post(f"/api/admin/members/{application['id']}/approve", headers=admin)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "active"

    mine = client.get("/api/memberships/me", headers=alice).json()
    assert mine["status"] == "active"
    assert client.get("/api/auth/me", headers=alice).json()["role"] == "member"
    types = client.get("/api/ticket-types", headers=alice).json()["items"]
    assert any(t["members_only"] for t in types)

    # Revoking member access disables the account: its token stops working
    # and signing in is refused until an administrator restores it.
    revoked = client.post(f"/api/admin/members/{application['id']}/revoke",
                          json={"reason": "Demo revoke"}, headers=admin)
    assert revoked.status_code == 200, revoked.text
    assert client.get("/api/auth/me", headers=alice).status_code == 401
    relogin = client.post("/api/auth/login",
                          json={"email": "alice@example.com", "password": "Visitor123!"})
    assert relogin.status_code == 403
    assert relogin.json()["code"] == "ACCOUNT_DISABLED"

    restored = client.post(f"/api/admin/members/{application['id']}/restore", headers=admin)
    assert restored.status_code == 200, restored.text
    alice = login("alice@example.com")
    assert client.get("/api/memberships/me", headers=alice).json()["status"] == "active"

def test_staff_cannot_approve(client, login):
    alice = login("alice@example.com")
    app_id = client.get("/api/memberships/me", headers=alice).json()["id"]
    staff = login("staff@museum.org")
    assert client.post(f"/api/admin/members/{app_id}/approve", headers=staff).status_code == 403
    assert client.post(f"/api/admin/members/{app_id}/approve", headers=alice).status_code == 403


def test_staff_accounts_cannot_hold_membership(client, login):
    staff = login("staff@museum.org")
    resp = client.post("/api/membership-applications", json={"plan_id": 1}, headers=staff)
    assert resp.status_code == 403


def test_new_account_can_register_and_apply(client):
    reg = client.post("/api/auth/register", json={
        "email": "new.family@example.com", "password": "Family123!",
        "first_name": "Nina", "last_name": "Family"})
    assert reg.status_code == 201, reg.text
    token = client.post("/api/auth/login", json={
        "email": "new.family@example.com", "password": "Family123!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/memberships/me", headers=headers).status_code == 404
    applied = client.post("/api/membership-applications",
                          json={"plan_id": 2, "children_covered": 2}, headers=headers)
    assert applied.status_code == 200, applied.text
    assert applied.json()["status"] == "pending"
