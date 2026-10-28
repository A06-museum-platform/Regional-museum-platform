"""Concurrency check for booking capacity: N people try to book the same
arrival window at the same moment. The window holds 60 places, so with
2 tickets each exactly 30 bookings may succeed and the rest must be refused
with INSUFFICIENT_TICKETS -- never an overbooked window, never a 500.

Run against a freshly seeded stack:
  python tests/load/race_last_places.py [http://localhost:8000] [attempts]
"""

import asyncio
import sys
from collections import Counter
from datetime import date, timedelta

import httpx

HOST = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
ATTEMPTS = int(sys.argv[2]) if len(sys.argv) > 2 else 40


async def main() -> int:
    day = date.today() + timedelta(days=12)
    while day.weekday() != 2:  # a Wednesday, nothing seeded on it
        day += timedelta(days=1)
    async with httpx.AsyncClient(base_url=HOST, timeout=30) as client:
        token = (await client.post("/api/auth/login",
                                   json={"email": "ben@example.com", "password": "Member123!"})).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        window = (await client.get("/api/bookings/availability", params={"date": day.isoformat()})).json()["windows"][0]
        body = {"visit_date": day.isoformat(), "arrival_window": {"start": window["start"]},
                "lines": [{"ticket_type_id": 1, "quantity": 2}],
                "visitor": {"first_name": "Race", "last_name": "Test", "email": "race@example.com"},
                "payment_acknowledged": True}

        async def attempt():
            resp = await client.post("/api/bookings", json=body, headers=headers)
            return resp.status_code, (resp.json().get("code") if resp.status_code != 201 else "created")

        results = Counter(await asyncio.gather(*(attempt() for _ in range(ATTEMPTS))))
        after = (await client.get("/api/bookings/availability", params={"date": day.isoformat()})).json()
        left = next(w["places_left"] for w in after["windows"] if w["start"] == window["start"])

    created = results[(201, "created")]
    print(f"{day} {window['start']}: {ATTEMPTS} simultaneous attempts of 2 tickets")
    for (status, code), n in sorted(results.items()):
        print(f"  {status} {code}: {n}")
    print(f"  places left afterwards: {left} (of {window['places_left']})")
    expected = min(ATTEMPTS, window["places_left"] // 2)
    ok = created == expected and left == window["places_left"] - 2 * created and \
        all(status in (201, 400) for status, _ in results)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
