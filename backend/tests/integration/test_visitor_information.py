"""Plan your visit: public read, staff update, role checks."""


def test_public_read(client):
    info = client.get("/api/visitor-information").json()
    assert info["museum_name"] and "North Terrace" in info["address"]
    assert any(f["name"] == "Sensory backpacks" for f in info["facilities"])


def test_staff_update_replaces_page(client, login):
    staff = login("staff@museum.org")
    info = client.get("/api/visitor-information").json()
    body = {**info, "parking": "Car park closed for resurfacing until March.",
            "facilities": [{"name": "Hearing loop", "description": "Front desk and theatre."},
                           {"name": "Quiet room", "location": "Level 1", "is_available": False}]}
    body.pop("museum_name")
    body["museum_name"] = "SARHN Regional Heritage Museum"
    saved = client.put("/api/staff/visitor-information", json=body, headers=staff)
    assert saved.status_code == 200, saved.text
    public = client.get("/api/visitor-information").json()
    assert public["parking"].startswith("Car park closed")
    assert [f["name"] for f in public["facilities"]] == ["Hearing loop", "Quiet room"]
    assert public["facilities"][1]["is_available"] is False

    bad = client.put("/api/staff/visitor-information", json={**body, "email": "not-an-email"},
                     headers=staff)
    assert bad.status_code == 422


def test_only_staff_can_update(client, login):
    body = client.get("/api/visitor-information").json()
    assert client.put("/api/staff/visitor-information", json=body).status_code == 401
    assert client.put("/api/staff/visitor-information", json=body,
                      headers=login("ben@example.com")).status_code == 403
