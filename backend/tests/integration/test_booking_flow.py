"""General-admission booking end to end on a real database: availability,
create, the member's own list, cancel, and who may see what."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def _next_weekday(weekday: int = 0, min_days: int = 2) -> str:
    """The next date (museum-local) on the given weekday (0 = Monday) at
    least min_days away. Seed opening hours: Mon-Fri 09:00-17:00."""
    today = datetime.now(ZoneInfo("Australia/Adelaide")).date()
    day = today + timedelta(days=min_days)
    while day.weekday() != weekday:
        day += timedelta(days=1)
    return day.isoformat()


def _booking_body(visit_date: str, start: str = "11:00", adults: int = 2, **extra) -> dict:
    return {
        "visit_date": visit_date,
        "arrival_window": {"start": start},
        "lines": [{"ticket_type_id": 1, "quantity": adults}],
        "visitor": {"first_name": "Ben", "last_name": "Wilson", "email": "ben@example.com"},
        "payment_acknowledged": True,
        **extra,
    }


def _places(client, visit_date: str) -> dict:
    windows = client.get("/api/bookings/availability", params={"date": visit_date}).json()["windows"]
    return {w["start"]: w["places_left"] for w in windows}


def test_book_list_and_cancel_round_trip(client, login):
    ben = login("ben@example.com")
    visit = _next_weekday()
    assert _places(client, visit)["11:00"] == 60

    created = client.post("/api/bookings", json=_booking_body(visit, adults=3), headers=ben)
    assert created.status_code == 201, created.text
    booking = created.json()
    assert booking["reference"].startswith("SARHN-")
    assert booking["status"] == "reserved"
    assert booking["total_cents"] == 3 * 1500
    assert _places(client, visit)["11:00"] == 57

    mine = client.get("/api/bookings/me", headers=ben).json()
    assert mine["total"] == 1
    assert mine["items"][0]["reference"] == booking["reference"]
    assert mine["items"][0]["lines"][0]["quantity"] == 3

    cancelled = client.post(f"/api/bookings/{booking['reference']}/cancel", headers=ben)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert _places(client, visit)["11:00"] == 60  # places go back on offer

    again = client.post(f"/api/bookings/{booking['reference']}/cancel", headers=ben)
    assert again.status_code == 409
    assert again.json()["code"] == "CONFLICT"


def test_member_ticket_needs_active_membership(client, login):
    visit = _next_weekday()
    member_line = {"lines": [{"ticket_type_id": 4, "quantity": 1}]}

    # Ben holds an active Individual membership in the seed data.
    ben = login("ben@example.com")
    ok = client.post("/api/bookings", json={**_booking_body(visit), **member_line}, headers=ben)
    assert ok.status_code == 201, ok.text
    assert ok.json()["total_cents"] == 0

    alice = login("alice@example.com")
    refused = client.post("/api/bookings", json={**_booking_body(visit), **member_line}, headers=alice)
    assert refused.status_code == 403
    assert refused.json()["code"] == "FORBIDDEN"


def test_other_accounts_cannot_see_or_cancel(client, login):
    ben = login("ben@example.com")
    ref = client.post("/api/bookings", json=_booking_body(_next_weekday()), headers=ben).json()["reference"]

    alice = login("alice@example.com")
    assert client.get(f"/api/bookings/{ref}", headers=alice).status_code == 404
    assert client.post(f"/api/bookings/{ref}/cancel", headers=alice).status_code == 404
    assert client.get("/api/bookings/me", headers=alice).json()["total"] == 0

    staff = login("staff@museum.org")
    assert client.get(f"/api/bookings/{ref}", headers=staff).status_code == 200


def test_booking_rules(client, login):
    ben = login("ben@example.com")
    visit = _next_weekday()

    too_many = client.post("/api/bookings", json=_booking_body(visit, adults=11), headers=ben)
    assert too_many.status_code == 409
    assert too_many.json()["code"] == "BOOKING_LIMIT_EXCEEDED"

    no_ack = client.post("/api/bookings", json=_booking_body(visit, payment_acknowledged=False),
                         headers=ben)
    assert no_ack.status_code == 400

    wrong_window = client.post("/api/bookings", json=_booking_body(visit, start="10:00"), headers=ben)
    assert wrong_window.status_code == 400

    sunday = client.post("/api/bookings", json=_booking_body(_next_weekday(6)), headers=ben)
    assert sunday.status_code == 400  # closed on Sundays

    assert client.post("/api/bookings", json=_booking_body(visit)).status_code == 401


def test_window_capacity_is_enforced(client, login):
    ben = login("ben@example.com")
    visit = _next_weekday()
    for _ in range(6):
        assert client.post("/api/bookings", json=_booking_body(visit, adults=10),
                           headers=ben).status_code == 201
    full = client.post("/api/bookings", json=_booking_body(visit, adults=1), headers=ben)
    assert full.status_code == 400
    assert full.json()["code"] == "INSUFFICIENT_TICKETS"


def test_validation_errors_use_the_contract_shape(client):
    resp = client.post("/api/auth/register", json={"email": "not-an-email", "password": "x"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert isinstance(body["detail"], str)
    assert "email" in body["fields"]

    missing = client.get("/api/no-such-route")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Not Found", "code": "NOT_FOUND"}


def test_dates_are_iso(client):
    # Guard for the helper itself: never books a past date.
    assert date.fromisoformat(_next_weekday()) > date.today() - timedelta(days=1)
