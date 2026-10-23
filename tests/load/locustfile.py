"""Load test for the client's concurrency targets (questionnaire Q1-2;
proposal evaluation criterion "Concurrent User Capacity"):

  * typical load: 100 concurrent users -> stable response
  * peak load:    500 concurrent users -> degrades gracefully, stays available

A "user" is a person with the site open: they load a page, read it for a
few seconds (wait_time) and move on, like a real visitor. The traffic mix
follows the audience in the brief -- mostly the public browsing, some
signed-in members, a little staff work:

  Browser (75%)  home page, collections search and items, events, exhibitions,
                 plan your visit, checking booking availability
  Member  (20%)  signs in once, opens their account (membership, bookings,
                 recommendations, activity), browses, occasionally books
  Staff    (5%)  signs in once, front desk: today's bookings, events list

Run against a freshly seeded database (database/seed/seed.sql):

  locust -f tests/load/locustfile.py --host http://localhost:8000 \
      --headless -u 100 -r 10 -t 3m --csv tests/load/results/typical_100
  locust -f tests/load/locustfile.py --host http://localhost:8000 \
      --headless -u 500 -r 25 -t 4m --csv tests/load/results/peak_500

See docs/load-testing.md for the method, pass criteria and results.
"""

import itertools
import random
from datetime import date, timedelta

from locust import between, events, task
from locust.contrib.fasthttp import FastHttpUser as HttpUser  # low-overhead client: the generator shares the CPU

SEARCH_TERMS = ["copper", "telegraph", "whaling", "mine", "morse", "kaurna", "railway", "ledger", ""]
GALLERIES = ["", "main_hall", "telegraph", "monster_mine", "encounter_bay"]

# Seeded accounts (Visitor123! unless noted). Many simulated members share
# these logins, which is fine: each keeps its own token.
MEMBERS = [("ben@example.com", "Member123!"), ("priya.sharma@example.com", "Visitor123!"),
           ("mei.chen@example.com", "Visitor123!"), ("alice@example.com", "Visitor123!"),
           ("noah.williams@example.com", "Visitor123!"), ("sofia.rossi@example.com", "Visitor123!")]
STAFF = [("staff@museum.org", "Staff123!"), ("admin@museum.org", "Admin123!")]
_member_cycle = itertools.cycle(MEMBERS)
_staff_cycle = itertools.cycle(STAFF)

COLLECTION_SLUGS: list[str] = []
EVENT_SLUGS: list[str] = []
EXHIBITION_SLUGS: list[str] = []


@events.test_start.add_listener
def _discover(environment, **_kwargs):
    """Read real slugs once, so detail pages hit existing records."""
    import requests

    host = environment.host
    COLLECTION_SLUGS[:] = [i["slug"] for i in requests.get(
        f"{host}/api/collection-items", params={"page_size": 100}, timeout=10).json()["items"]]
    EVENT_SLUGS[:] = [i["slug"] for i in requests.get(
        f"{host}/api/events", params={"page_size": 100}, timeout=10).json()["items"]]
    EXHIBITION_SLUGS[:] = [i["slug"] for i in requests.get(
        f"{host}/api/exhibitions", timeout=10).json()["items"]]


def _now_iso() -> str:
    """Start of today as the front end sends it (an ISO timestamp)."""
    return f"{date.today().isoformat()}T00:00:00+10:30"


def _params(**params) -> dict:
    """Drop empty values, as the front end's request() helper does."""
    return {k: v for k, v in params.items() if v not in ("", None)}


def _open_day(min_days=1, max_days=30) -> str:
    """A weekday the seeded museum is open (Mon-Sat)."""
    day = date.today() + timedelta(days=random.randint(min_days, max_days))
    while day.weekday() == 6:
        day += timedelta(days=1)
    return day.isoformat()


class Browser(HttpUser):
    """A member of the public with the site open."""

    weight = 15
    wait_time = between(3, 8)

    @task(4)
    def home_page(self):
        # The home page makes these four requests in parallel.
        self.client.get("/api/opening-hours", name="home: opening hours")
        self.client.get("/api/events", params={"from": _now_iso(), "page_size": 4},
                        name="home: upcoming events")
        self.client.get("/api/exhibitions", params={"page_size": 3}, name="home: exhibitions")
        self.client.get("/api/collection-items", params={"highlight": "true", "page_size": 4},
                        name="home: highlights")

    @task(4)
    def search_collections(self):
        self.client.get("/api/collection-items",
                        params=_params(q=random.choice(SEARCH_TERMS), gallery=random.choice(GALLERIES),
                                       page_size=12), name="collections: search")

    @task(3)
    def collection_item(self):
        if COLLECTION_SLUGS:
            self.client.get(f"/api/collection-items/{random.choice(COLLECTION_SLUGS)}",
                            name="collections: item")

    @task(3)
    def events(self):
        self.client.get("/api/events", params={"from": _now_iso(), "page_size": 10},
                        name="events: list")
        if EVENT_SLUGS:
            self.client.get(f"/api/events/{random.choice(EVENT_SLUGS)}", name="events: detail")

    @task(2)
    def exhibitions(self):
        self.client.get("/api/exhibitions", name="exhibitions: list")
        if EXHIBITION_SLUGS:
            self.client.get(f"/api/exhibitions/{random.choice(EXHIBITION_SLUGS)}",
                            name="exhibitions: detail")

    @task(2)
    def plan_visit(self):
        self.client.get("/api/visitor-information", name="visit: information")
        self.client.get("/api/ticket-types", name="visit: ticket prices")

    @task(2)
    def booking_step_one(self):
        self.client.get("/api/bookings/availability", params={"date": _open_day()},
                        name="book: availability")


class Member(HttpUser):
    """A signed-in member checking their account and booking."""

    weight = 4
    wait_time = between(3, 8)

    def on_start(self):
        email, password = next(_member_cycle)
        resp = self.client.post("/api/auth/login", json={"email": email, "password": password},
                                name="auth: login")
        self.headers = ({"Authorization": f"Bearer {resp.json()['access_token']}"}
                        if resp.status_code == 200 else {})

    @task(3)
    def account_page(self):
        for path, name in [("/api/auth/me", "account: me"), ("/api/memberships/me", "account: membership"),
                           ("/api/bookings/me", "account: bookings"),
                           ("/api/event-registrations/me", "account: registrations"),
                           ("/api/activity/me", "account: activity")]:
            with self.client.get(path, headers=self.headers, name=name, catch_response=True) as resp:
                if resp.status_code in (200, 404):  # 404 = no membership yet, a valid answer
                    resp.success()
        with self.client.get("/api/recommendations", headers=self.headers, name="account: recommendations",
                             catch_response=True) as resp:
            if resp.status_code in (200, 403):  # 403 = visitor account, expected
                resp.success()

    @task(3)
    def browse(self):
        self.client.get("/api/collection-items", params=_params(q=random.choice(SEARCH_TERMS)),
                        name="collections: search")
        self.client.get("/api/events", params={"from": _now_iso()}, name="events: list")

    @task(1)
    def book_a_visit(self):
        day = _open_day(3, 50)
        resp = self.client.get("/api/bookings/availability", params={"date": day},
                               name="book: availability")
        if resp.status_code != 200:
            return  # already counted as a failure by Locust
        windows = [w for w in resp.json().get("windows", []) if w["places_left"] >= 2]
        if not windows:
            return
        body = {"visit_date": day, "arrival_window": {"start": random.choice(windows)["start"]},
                "lines": [{"ticket_type_id": 1, "quantity": 1}, {"ticket_type_id": 3, "quantity": 1}],
                "visitor": {"first_name": "Load", "last_name": "Test", "email": "load@example.com"},
                "payment_acknowledged": True}
        with self.client.post("/api/bookings", json=body, headers=self.headers, name="book: confirm",
                              catch_response=True) as resp:
            # Losing the last places to another user is correct behaviour, not an error.
            if resp.status_code == 201 or (resp.status_code == 400
                                           and resp.json().get("code") == "INSUFFICIENT_TICKETS"):
                resp.success()


class Staff(HttpUser):
    """Front-desk staff working through the day."""

    weight = 1
    wait_time = between(5, 12)

    def on_start(self):
        email, password = next(_staff_cycle)
        resp = self.client.post("/api/auth/login", json={"email": email, "password": password},
                                name="auth: login")
        self.headers = ({"Authorization": f"Bearer {resp.json()['access_token']}"}
                        if resp.status_code == 200 else {})

    @task(3)
    def front_desk(self):
        self.client.get("/api/staff/today", headers=self.headers, name="staff: today")
        self.client.get("/api/staff/bookings", params={"date": date.today().isoformat()},
                        headers=self.headers, name="staff: bookings")

    @task(1)
    def manage_events(self):
        self.client.get("/api/staff/events", headers=self.headers, name="staff: events")
