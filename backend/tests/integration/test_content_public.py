"""What visitors see: collections, exhibitions, events and opening hours,
read from the seeded database (database/seed/seed.sql)."""


def test_collection_search_and_filters(client):
    all_items = client.get("/api/collection-items", params={"page_size": 100}).json()
    # 13 seeded objects, one of them a draft that visitors never see.
    assert all_items["total"] == 12
    assert all(item["status"] == "published" for item in all_items["items"])
    first = all_items["items"][0]
    for field in ("slug", "title", "accession_number", "category", "gallery", "image_url",
                  "period_text", "is_family_friendly"):
        assert field in first

    telegraph = client.get("/api/collection-items", params={"gallery": "telegraph"}).json()
    assert telegraph["total"] > 0
    assert {i["gallery"] for i in telegraph["items"]} == {"telegraph"}

    minerals = client.get("/api/collection-items", params={"category": "mineral"}).json()
    assert {i["category"] for i in minerals["items"]} == {"mineral"}

    family = client.get("/api/collection-items", params={"family_friendly": "true"}).json()
    assert all(i["is_family_friendly"] for i in family["items"])

    search = client.get("/api/collection-items", params={"q": "malachite"}).json()
    assert "malachite-matrix-burra" in [i["slug"] for i in search["items"]]
    assert all("malachite" in (i["title"] + i["description"]).lower() for i in search["items"])

    early = client.get("/api/collection-items", params={"year_to": 1850}).json()
    assert all(i["year_from"] is None or i["year_from"] <= 1850 for i in early["items"])

    paged = client.get("/api/collection-items", params={"page_size": 5, "page": 2}).json()
    assert paged["page"] == 2 and paged["page_size"] == 5 and len(paged["items"]) == 5

    assert client.get("/api/collection-items", params={"gallery": "nowhere"}).status_code == 422


def test_collection_detail(client):
    item = client.get("/api/collection-items/malachite-matrix-burra").json()
    assert item["title"] == "Malachite matrix, Burra"
    assert item["exhibition"]["slug"] == "colonial-mining-overland-telegraph"
    missing = client.get("/api/collection-items/no-such-object")
    assert missing.status_code == 404 and missing.json()["code"] == "NOT_FOUND"


def test_exhibitions(client):
    listing = client.get("/api/exhibitions").json()
    slugs = [x["slug"] for x in listing["items"]]
    assert "working-the-monster-mine" in slugs
    assert all(x["status"] == "published" for x in listing["items"])
    assert all(x["phase"] in ("current", "upcoming") for x in listing["items"])

    detail = client.get("/api/exhibitions/colonial-mining-overland-telegraph").json()
    assert detail["item_count"] == len(detail["items"]) > 0
    assert client.get("/api/exhibitions/no-such").status_code == 404


def test_events_listing_detail_and_filters(client):
    listing = client.get("/api/events", params={"page_size": 50}).json()
    statuses = {e["status"] for e in listing["items"]}
    assert "draft" not in statuses
    assert listing["total"] == 10  # 11 seeded, one draft
    event = listing["items"][0]
    for field in ("slug", "starts_at", "ends_at", "capacity", "spots_remaining", "is_sold_out",
                  "price_cents", "member_price_cents", "display_name", "event_time"):
        assert field in event

    upcoming = client.get("/api/events", params={"from": "2000-01-01T00:00:00Z", "page_size": 50}).json()
    assert upcoming["total"] == 10
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    future = client.get("/api/events", params={"from": now, "page_size": 50}).json()
    assert 0 < future["total"] < 10
    assert all(not e["is_past"] for e in future["items"])

    families = client.get("/api/events", params={"audience": "families", "page_size": 50}).json()
    assert all((e["age_min"] or 0) <= 14 and (e["age_max"] or 99) >= 10 for e in families["items"])

    # Contract names still work: size, numeric id.
    contract = client.get("/api/events", params={"size": 2}).json()
    assert contract["size"] == 2 and len(contract["items"]) == 2
    by_id = client.get(f"/api/events/{event['id']}").json()
    by_slug = client.get(f"/api/events/{event['slug']}").json()
    assert by_id == by_slug

    full = next(e for e in listing["items"] if e["slug"].startswith("curators-cabinet"))
    assert full["is_sold_out"] and full["spots_remaining"] == 0


def test_draft_event_is_hidden(client):
    assert client.get("/api/events/summer-twilight-telegraph").status_code == 404


def test_opening_hours(client):
    hours = client.get("/api/opening-hours").json()
    assert [d["day_of_week"] for d in hours["weekly"]] == list(range(7))
    sunday = hours["weekly"][0]
    assert sunday["is_closed"] and sunday["opens_at"] is None
    monday = hours["weekly"][1]
    assert monday["opens_at"] == "09:00" and monday["closes_at"] == "17:00"
    assert hours["overrides"] == []
