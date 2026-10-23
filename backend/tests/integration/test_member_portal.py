"""Member portal: interests, recommendations, own activity, content tags."""


def test_interest_vocabulary_is_public(client):
    tags = client.get("/api/interest-tags").json()
    assert {"mining", "telegraph", "hands_on"} <= {t["slug"] for t in tags}


def test_recommendations_follow_interests(client, login):
    ben = login("ben@example.com")
    assert [t["slug"] for t in client.get("/api/me/interests", headers=ben).json()] == ["mining", "hands_on"]

    recs = client.get("/api/recommendations", headers=ben).json()
    assert recs["personalised"] and recs["total"] > 0
    first = recs["items"][0]
    assert first["matched_tags"] and "mining" in first["reason"].lower() or "hands-on" in first["reason"].lower()
    scores = [r["score"] for r in recs["items"]]
    assert scores == sorted(scores, reverse=True)
    for item in recs["items"]:
        assert item["matched_tags"], item  # nothing unrelated to his interests

    # Changing interests changes what comes back.
    client.put("/api/me/interests", json={"tags": ["maritime"]}, headers=ben)
    maritime = client.get("/api/recommendations", headers=ben).json()
    assert all("Sea, ships and whaling" in r["matched_tags"] for r in maritime["items"])
    events_only = client.get("/api/recommendations", params={"type": "event"}, headers=ben).json()
    assert {r["type"] for r in events_only["items"]} <= {"event"}

    # No interests -> popular fallback, not an empty page.
    client.put("/api/me/interests", json={"tags": []}, headers=ben)
    popular = client.get("/api/recommendations", headers=ben).json()
    assert not popular["personalised"] and popular["total"] > 0
    assert popular["items"][0]["reason"].startswith("Popular")

    bad = client.put("/api/me/interests", json={"tags": ["knitting"]}, headers=ben)
    assert bad.status_code == 422


def test_registered_and_full_sessions_are_not_recommended(client, login):
    ben = login("ben@example.com")
    events = [r for r in client.get("/api/recommendations", params={"type": "event", "size": 50},
                                    headers=ben).json()["items"]]
    target = events[0]
    client.post(f"/api/events/{target['slug']}/registrations",
                json={"contact_name": "Ben", "contact_email": "ben@example.com", "party_size": 1},
                headers=ben)
    after = client.get("/api/recommendations", params={"type": "event", "size": 50}, headers=ben).json()
    assert target["slug"] not in [r["slug"] for r in after["items"]]
    assert "curators-cabinet-specimen-store" not in [r["slug"] for r in after["items"]]  # full


def test_recommendations_are_for_members(client, login):
    assert client.get("/api/recommendations").status_code == 401
    alice = client.get("/api/recommendations", headers=login("alice@example.com"))
    assert alice.status_code == 403 and alice.json()["detail"] == "Member access required"
    # Visitors can still save interests for when they join.
    assert client.put("/api/me/interests", json={"tags": ["telegraph"]},
                      headers=login("alice@example.com")).status_code == 200


def test_member_sees_own_activity(client, login):
    ben = login("ben@example.com")
    from datetime import date, timedelta
    day = date.today() + timedelta(days=9)
    while day.weekday() != 1:
        day += timedelta(days=1)
    booking = client.post("/api/bookings", json={
        "visit_date": day.isoformat(), "arrival_window": {"start": "11:00"},
        "lines": [{"ticket_type_id": 1, "quantity": 1}],
        "visitor": {"first_name": "Ben", "last_name": "Wilson", "email": "ben@example.com"},
        "payment_acknowledged": True}, headers=ben).json()
    mine = client.get("/api/activity/me", headers=ben).json()
    assert mine["items"][0]["action"] == "booking.created"
    assert mine["items"][0]["reference"] == booking["reference"]

    # An admin decision about Alice shows in Alice's activity, not Ben's.
    admin = login("admin@museum.org")
    alice = login("alice@example.com")
    app_id = client.get("/api/memberships/me", headers=alice).json()["id"]
    client.post(f"/api/admin/members/{app_id}/approve", headers=admin)
    alice_log = client.get("/api/activity/me", headers=alice).json()
    assert alice_log["items"][0]["action"] == "member.approved"
    ben_log = client.get("/api/activity/me", headers=ben).json()["items"]
    assert all("Alice" not in e["target"] for e in ben_log)


def test_revoke_reason_is_logged(client, login):
    admin = login("admin@museum.org")
    ben_membership = client.get("/api/memberships/me", headers=login("ben@example.com")).json()
    client.post(f"/api/admin/members/{ben_membership['id']}/revoke",
                json={"reason": "Pass shared with a non-member"}, headers=admin)
    entry = client.get("/api/admin/activity-log", params={"action": "member.revoked"}, headers=admin).json()["items"][0]
    assert entry["reason"] == "Pass shared with a non-member"
    assert entry["actor_name"] == "James Anderson"


def test_staff_tag_content(client, login):
    staff = login("staff@museum.org")
    item = client.post("/api/staff/collection-items",
                       json={"title": "Telegraph insulator", "tags": ["telegraph", "science"]},
                       headers=staff).json()
    assert item["tags"] == ["telegraph", "science"]
    updated = client.patch(f"/api/staff/collection-items/{item['id']}", json={"tags": ["telegraph"]},
                           headers=staff).json()
    assert updated["tags"] == ["telegraph"]
    exhibition = client.patch("/api/staff/exhibitions/1", json={"tags": ["mining"]}, headers=staff).json()
    assert exhibition["tags"] == ["mining"]
    event = client.get("/api/events/morse-code-galvanic-batteries").json()
    assert "telegraph" in event["tags"]
    assert client.post("/api/staff/events", json={"title": "x", "starts_at": "2030-01-01T10:00:00+10:30",
                                                  "ends_at": "2030-01-01T11:00:00+10:30", "capacity": 5,
                                                  "tags": ["nope"]}, headers=staff).status_code == 422
