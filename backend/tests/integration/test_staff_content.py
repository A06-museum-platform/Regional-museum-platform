"""Staff content management on a real database: the full event publishing
workflow (evaluation criterion "Content Manageability"), collection and
exhibition editing, opening hours, and the server-side role checks."""

from datetime import datetime, timedelta, timezone


def _future(days: int, hour: int) -> str:
    """An ISO time `days` from now at `hour`:00 Adelaide standard-ish time
    (fixed +10:30 offset is fine for a same-day start/finish check)."""
    day = (datetime.now(timezone(timedelta(hours=10, minutes=30))) + timedelta(days=days)).date()
    return f"{day.isoformat()}T{hour:02d}:00:00+10:30"


def _event_body(**changes) -> dict:
    return {
        "title": "Copper and the colony: a family trail",
        "description": "Follow the copper from the Monster Mine to the telegraph key.",
        "gallery": "monster_mine",
        "starts_at": _future(10, 10),
        "ends_at": _future(10, 12),
        "capacity": 12,
        "price_cents": 1200,
        "member_price_cents": 0,
        "age_min": 10,
        "age_max": 14,
        "status": "draft",
        **changes,
    }


def test_event_publishing_workflow(client, login):
    staff = login("staff@museum.org")

    created = client.post("/api/staff/events", json=_event_body(), headers=staff)
    assert created.status_code == 201, created.text
    event = created.json()
    assert event["status"] == "draft"
    assert event["slug"] == "copper-and-the-colony-a-family-trail"
    assert datetime.fromisoformat(event["starts_at"].replace("Z", "+00:00")) == \
        datetime.fromisoformat(_future(10, 10))

    # A draft is invisible to visitors.
    assert client.get(f"/api/events/{event['slug']}").status_code == 404
    staff_list = client.get("/api/staff/events", params={"status": "draft"}, headers=staff).json()
    assert event["id"] in [e["id"] for e in staff_list["items"]]

    published = client.patch(f"/api/staff/events/{event['id']}", json={"status": "published"},
                             headers=staff)
    assert published.status_code == 200
    public = client.get(f"/api/events/{event['slug']}").json()
    assert public["spots_remaining"] == 12 and public["price_cents"] == 1200

    # A visitor registers; capacity can't go below the places taken.
    alice = login("alice@example.com")
    reg = client.post(f"/api/events/{event['slug']}/registrations",
                      json={"contact_name": "Alice Brown", "contact_email": "alice@example.com",
                            "party_size": 4}, headers=alice)
    assert reg.status_code == 201, reg.text
    too_small = client.patch(f"/api/staff/events/{event['id']}", json={"capacity": 3}, headers=staff)
    assert too_small.status_code == 409
    assert too_small.json()["code"] == "CAPACITY_BELOW_REGISTRATIONS"
    assert client.patch(f"/api/staff/events/{event['id']}", json={"capacity": 20},
                        headers=staff).json()["spots_remaining"] == 16

    # Registered people block deletion; cancelling is the way out.
    blocked = client.delete(f"/api/staff/events/{event['id']}", headers=staff)
    assert blocked.status_code == 409 and blocked.json()["code"] == "EVENT_HAS_REGISTRATIONS"
    regs = client.get(f"/api/staff/events/{event['id']}/registrations", headers=staff).json()
    assert [r["party_size"] for r in regs] == [4]
    cancelled = client.patch(f"/api/staff/events/{event['id']}", json={"status": "cancelled"},
                             headers=staff).json()
    assert cancelled["status"] == "cancelled"

    # Renaming changes the slug; editing times keeps a same-day session.
    renamed = client.patch(f"/api/staff/events/{event['id']}", json={"title": "Copper trail"},
                           headers=staff).json()
    assert renamed["slug"] == "copper-trail"
    overnight = client.patch(f"/api/staff/events/{event['id']}",
                             json={"ends_at": _future(11, 1)}, headers=staff)
    assert overnight.status_code == 400


def test_event_validation(client, login):
    staff = login("staff@museum.org")
    bad_times = client.post("/api/staff/events",
                            json=_event_body(starts_at=_future(5, 12), ends_at=_future(5, 10)),
                            headers=staff)
    assert bad_times.status_code == 422
    member_dearer = client.post("/api/staff/events",
                                json=_event_body(price_cents=500, member_price_cents=800), headers=staff)
    assert member_dearer.status_code == 422
    empty = client.post("/api/staff/events", json=_event_body(), headers=staff).json()
    assert client.delete(f"/api/staff/events/{empty['id']}", headers=staff).status_code == 204


def test_collection_item_crud(client, login):
    staff = login("staff@museum.org")
    draft = client.post("/api/staff/collection-items", json={"title": "Miner's candle holder"},
                        headers=staff)
    assert draft.status_code == 201, draft.text
    item = draft.json()
    assert item["status"] == "draft"
    assert client.get(f"/api/collection-items/{item['slug']}").status_code == 404

    # Publishing needs the fields visitors see.
    incomplete = client.patch(f"/api/staff/collection-items/{item['id']}",
                              json={"status": "published"}, headers=staff)
    assert incomplete.status_code == 400
    published = client.patch(
        f"/api/staff/collection-items/{item['id']}",
        json={"status": "published", "accession_number": "MAC-1860-01", "category": "machinery",
              "gallery": "monster_mine", "description": "Iron spike candle holder used underground.",
              "year_from": 1855, "year_to": 1870, "exhibition_id": 2},
        headers=staff,
    )
    assert published.status_code == 200, published.text
    public = client.get(f"/api/collection-items/{item['slug']}").json()
    assert public["exhibition"]["id"] == 2 and public["category"] == "machinery"

    clash = client.post("/api/staff/collection-items",
                        json={"title": "Another", "accession_number": "mac-1860-01"}, headers=staff)
    assert clash.status_code == 409 and clash.json()["code"] == "ACCESSION_TAKEN"
    bad_years = client.patch(f"/api/staff/collection-items/{item['id']}",
                             json={"year_from": 1900}, headers=staff)
    assert bad_years.status_code == 400

    assert client.delete(f"/api/staff/collection-items/{item['id']}", headers=staff).status_code == 204
    assert client.get(f"/api/collection-items/{item['slug']}").status_code == 404


def test_exhibition_crud_and_delete_guard(client, login):
    staff = login("staff@museum.org")
    made = client.post("/api/staff/exhibitions",
                       json={"title": "Lighthouses of the Fleurieu", "summary": "Keepers and lamps.",
                             "gallery": "encounter_bay", "start_date": "", "end_date": "",
                             "status": "published"}, headers=staff)
    assert made.status_code == 201, made.text
    exhibition = made.json()
    assert exhibition["phase"] == "current" and exhibition["end_date"] is None
    assert client.get(f"/api/exhibitions/{exhibition['slug']}").status_code == 200

    unpublished = client.patch(f"/api/staff/exhibitions/{exhibition['id']}", json={"status": "draft"},
                               headers=staff).json()
    assert unpublished["status"] == "draft"
    assert client.get(f"/api/exhibitions/{exhibition['slug']}").status_code == 404
    assert client.delete(f"/api/staff/exhibitions/{exhibition['id']}", headers=staff).status_code == 204

    # Seeded exhibition 1 has objects attached.
    guarded = client.delete("/api/staff/exhibitions/1", headers=staff)
    assert guarded.status_code == 409 and guarded.json()["code"] == "EXHIBITION_HAS_ITEMS"


def test_opening_hours_update_closes_booking_dates(client, login):
    staff = login("staff@museum.org")
    hours = client.get("/api/opening-hours").json()
    weekly = hours["weekly"]
    weekly[5] = {**weekly[5], "closes_at": "20:00", "note": "Late opening"}  # Friday
    holiday = (datetime.now(timezone.utc) + timedelta(days=8)).date()
    while holiday.weekday() >= 5:  # a weekday the museum would normally open
        holiday += timedelta(days=1)
    body = {"weekly": weekly, "overrides": [
        {"specific_date": holiday.isoformat(), "is_closed": True, "note": "Staff training day"}]}

    saved = client.put("/api/staff/opening-hours", json=body, headers=staff)
    assert saved.status_code == 200, saved.text
    public = client.get("/api/opening-hours").json()
    assert public["weekly"][5]["closes_at"] == "20:00" and public["weekly"][5]["note"] == "Late opening"
    assert public["overrides"][0]["note"] == "Staff training day"

    availability = client.get("/api/bookings/availability", params={"date": holiday.isoformat()}).json()
    assert availability["is_closed"] and availability["note"] == "Staff training day"

    broken = {**body, "weekly": [{**weekly[1], "opens_at": "17:00", "closes_at": "09:00"}, *weekly[2:],
                                 weekly[0]]}
    resp = client.put("/api/staff/opening-hours", json=broken, headers=staff)
    assert resp.status_code == 422 and resp.json()["code"] == "INVALID_HOURS"


def test_staff_endpoints_refuse_other_roles(client, login):
    """Server-side role checks: anonymous -> 401, visitor/member -> 403."""
    paths = [
        ("get", "/api/staff/events", None),
        ("post", "/api/staff/events", _event_body()),
        ("patch", "/api/staff/events/1", {"capacity": 99}),
        ("delete", "/api/staff/events/10", None),
        ("get", "/api/staff/events/1/registrations", None),
        ("get", "/api/staff/collection-items", None),
        ("post", "/api/staff/collection-items", {"title": "x"}),
        ("patch", "/api/staff/collection-items/1", {"title": "x"}),
        ("delete", "/api/staff/collection-items/1", None),
        ("get", "/api/staff/exhibitions", None),
        ("post", "/api/staff/exhibitions", {"title": "x"}),
        ("patch", "/api/staff/exhibitions/1", {"title": "x"}),
        ("delete", "/api/staff/exhibitions/5", None),
        ("put", "/api/staff/opening-hours", {"weekly": [], "overrides": []}),
    ]
    alice, ben = login("alice@example.com"), login("ben@example.com")
    for method, path, body in paths:
        kwargs = {"json": body} if body is not None else {}
        assert getattr(client, method)(path, **kwargs).status_code == 401, path
        assert getattr(client, method)(path, headers=alice, **kwargs).status_code == 403, path
        assert getattr(client, method)(path, headers=ben, **kwargs).status_code == 403, path
    # Admins inherit staff permissions.
    admin = login("admin@museum.org")
    assert client.get("/api/staff/events", headers=admin).status_code == 200


def test_staff_actions_are_logged_for_admins(client, login):
    staff = login("staff@museum.org")
    created = client.post("/api/staff/events", json=_event_body(status="published"), headers=staff).json()
    admin = login("admin@museum.org")
    log = client.get("/api/admin/activity-log", headers=admin).json()
    latest = log["items"][0]
    assert latest["action"] == "event.published"
    assert latest["target"] == created["title"]
    assert latest["actor_name"] == "Emma Taylor" and latest["actor_role"] == "staff"
    filtered = client.get("/api/admin/activity-log", params={"action": "event.published"}, headers=admin)
    assert all(e["action"] == "event.published" for e in filtered.json()["items"])
    # Staff can't read the audit log.
    assert client.get("/api/admin/activity-log", headers=staff).status_code == 403
