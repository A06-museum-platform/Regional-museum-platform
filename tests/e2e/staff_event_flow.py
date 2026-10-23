"""Evaluation criterion "Content Manageability": staff publish an event
through the UI without help, then a visitor finds it and registers."""
from datetime import date, timedelta

from playwright.sync_api import expect, sync_playwright

import os
BASE = os.environ.get("E2E_BASE_URL", "http://localhost:5173")
OUT = os.environ.get("E2E_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots"))
TITLE = "Lantern-making for young miners"


def sign_in(page, email, password):
    page.goto(f"{BASE}/signin")
    page.fill("input[type=email]", email)
    page.fill("input[type=password]", password)
    page.press("input[type=password]", "Enter")
    page.wait_for_timeout(1200)


with sync_playwright() as p:
    browser = p.chromium.launch()
    errors = []

    def new_page():
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith(BASE) else r.abort())
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("response", lambda r: "/api/" in r.url and r.status >= 500 and errors.append(f"{r.status} {r.url}"))
        return pg

    staff = new_page()
    sign_in(staff, "staff@museum.org", "Staff123!")
    staff.goto(f"{BASE}/staff/events")
    staff.get_by_role("button", name="New session").click()
    day = date.today() + timedelta(days=12)
    staff.fill("#ev-title", TITLE)
    staff.fill("#ev-desc", "Punch-tin lanterns like the ones Cornish miners carried, then test them in the dark room.")
    staff.select_option("#ev-gallery", "monster_mine")
    staff.fill("#ev-start", f"{day.isoformat()}T10:00")
    staff.fill("#ev-end", f"{day.isoformat()}T11:30")
    staff.fill("#ev-capacity", "15")
    staff.fill("#ev-price", "800")
    staff.fill("#ev-age-min", "10")
    staff.fill("#ev-age-max", "14")
    staff.screenshot(path=f"{OUT}/staff_1_new_event.png")
    staff.get_by_role("button", name="Publish").last.click()
    staff.wait_for_timeout(1200)
    expect(staff.get_by_text(TITLE)).to_be_visible()
    staff.screenshot(path=f"{OUT}/staff_2_listed.png", full_page=True)
    print("staff published: yes")

    visitor = new_page()
    visitor.goto(f"{BASE}/events?q=lantern-making")
    visitor.wait_for_timeout(1200)
    visitor.get_by_role("link", name=TITLE).first.click()
    visitor.wait_for_timeout(1000)
    visitor.screenshot(path=f"{OUT}/visitor_1_event_signed_out.png", full_page=True)
    visitor.get_by_role("button", name="Sign in to register").click()
    visitor.fill("input[type=email]", "alice@example.com")
    visitor.fill("input[type=password]", "Visitor123!")
    visitor.press("input[type=password]", "Enter")
    visitor.wait_for_timeout(1500)
    print("back on event after sign in:", "/events/" in visitor.url)
    visitor.select_option("#reg-party", "3")
    visitor.get_by_role("button", name="Register (simulated)").click()
    visitor.wait_for_timeout(1200)
    expect(visitor.get_by_text("You are registered")).to_be_visible()
    visitor.screenshot(path=f"{OUT}/visitor_2_registered.png", full_page=True)
    print("visitor registered: yes")

    staff.reload()
    staff.wait_for_timeout(1200)
    row = staff.locator("tr", has_text=TITLE)
    print("staff sees places:", row.locator("td").nth(2).inner_text().split("\n")[0])
    row.get_by_role("button", name="Cancel session").click()
    staff.get_by_role("dialog").get_by_role("button", name="Cancel session").click()
    staff.wait_for_timeout(1200)
    print("status after cancel:", staff.locator("tr", has_text=TITLE).locator("td").nth(4).inner_text())

    admin = new_page()
    sign_in(admin, "admin@museum.org", "Admin123!")
    admin.goto(f"{BASE}/admin/activity")
    admin.wait_for_timeout(1200)
    admin.screenshot(path=f"{OUT}/admin_activity.png", full_page=True)
    print("activity mentions event:", admin.get_by_text(TITLE).count())
    print("errors:", errors or "none")
    browser.close()
