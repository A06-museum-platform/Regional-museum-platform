"""Event registration (Flow 4) on a real database."""


def _upcoming_with_room(client):
    from datetime import datetime, timezone
    events = client.get("/api/events", params={"from": datetime.now(timezone.utc).isoformat(),
                                               "page_size": 50}).json()["items"]
    return next(e for e in events if e["spots_remaining"] >= 6 and e["status"] == "published")


def _body(size=2):
    return {"contact_name": "Ben Wilson", "contact_email": "ben@example.com", "party_size": size}


def test_register_list_cancel(client, login):
    ben = login("ben@example.com")
    event = _upcoming_with_room(client)

    reg = client.post(f"/api/events/{event['slug']}/registrations", json=_body(3), headers=ben)
    assert reg.status_code == 201, reg.text
    registration = reg.json()
    assert registration["status"] == "confirmed" and registration["reference"].startswith("SARHN-EV-")
    after = client.get(f"/api/events/{event['slug']}").json()
    assert after["spots_remaining"] == event["spots_remaining"] - 3

    again = client.post(f"/api/events/{event['slug']}/registrations", json=_body(), headers=ben)
    assert again.status_code == 409 and again.json()["code"] == "ALREADY_REGISTERED"

    mine = client.get("/api/event-registrations/me", headers=ben).json()
    assert registration["reference"] in [r["reference"] for r in mine["items"]]

    cancelled = client.post(f"/api/event-registrations/{registration['reference']}/cancel", headers=ben)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    assert client.get(f"/api/events/{event['slug']}").json()["spots_remaining"] == event["spots_remaining"]

    # After cancelling, registering again is allowed.
    assert client.post(f"/api/events/{event['slug']}/registrations", json=_body(1),
                       headers=ben).status_code == 201


def test_full_and_closed_events(client, login):
    ben = login("ben@example.com")
    full = client.post("/api/events/curators-cabinet-specimen-store/registrations", json=_body(1),
                       headers=ben)
    if full.status_code == 404:  # slug guard: find the seeded full session by flag
        events = client.get("/api/events", params={"page_size": 50}).json()["items"]
        slug = next(e["slug"] for e in events if e["is_sold_out"] and not e["is_past"])
        full = client.post(f"/api/events/{slug}/registrations", json=_body(1), headers=ben)
    assert full.status_code == 409 and full.json()["code"] == "EVENT_FULL"

    events = client.get("/api/events", params={"page_size": 50}).json()["items"]
    past = next(e for e in events if e["is_past"])
    closed = client.post(f"/api/events/{past['slug']}/registrations", json=_body(1), headers=ben)
    assert closed.status_code == 409 and closed.json()["code"] == "REGISTRATION_CLOSED"


def test_party_larger_than_places_left(client, login):
    ben = login("ben@example.com")
    events = client.get("/api/events", params={"page_size": 50}).json()["items"]
    tight = next(e for e in events if not e["is_past"] and 0 < e["spots_remaining"] < 10)
    resp = client.post(f"/api/events/{tight['slug']}/registrations",
                       json=_body(tight["spots_remaining"] + 1), headers=ben)
    assert resp.status_code == 409 and resp.json()["code"] == "EVENT_FULL"


def test_registration_needs_sign_in(client):
    event = _upcoming_with_room(client)
    resp = client.post(f"/api/events/{event['slug']}/registrations", json=_body())
    assert resp.status_code == 401
