"""Membership with the demonstration card checkout, end to end:
a new visitor registers, picks Family, pays with made-up card details,
the application is pending; the administrator approves it and the visitor
becomes a member. Needs the seeded admin account (or set E2E_ADMIN_*)."""
import os
import time

from playwright.sync_api import expect, sync_playwright

BASE = os.environ.get("E2E_BASE_URL", "http://localhost:5173")
OUT = os.environ.get("E2E_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots"))
ADMIN = (os.environ.get("E2E_ADMIN_EMAIL", "admin@museum.org"), os.environ.get("E2E_ADMIN_PASSWORD", "Admin123!"))
EMAIL = f"family.{int(time.time())}@example.com"


def sign_in(page, email, password):
    page.goto(f"{BASE}/signin")
    page.fill("input[type=email]", email)
    page.fill("input[type=password]", password)
    page.press("input[type=password]", "Enter")
    page.wait_for_timeout(1200)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH") or None)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(BASE) else r.abort())
    sent = []
    page.on("request", lambda r: r.post_data and sent.append(r.post_data))

    page.goto(f"{BASE}/register")
    page.get_by_label("First name").fill("Nina")
    page.get_by_label("Last name").fill("Family")
    page.get_by_label("Email").fill(EMAIL)
    for field in page.locator("input[type=password]").all():
        field.fill("Family123!")
    page.get_by_role("button", name="Create account").click()
    page.wait_for_timeout(1500)

    page.goto(f"{BASE}/membership")
    page.wait_for_timeout(1000)
    page.get_by_role("button", name="Continue to payment").click()
    page.wait_for_url("**/membership/checkout**")
    page.get_by_role("button", name="and apply").click()              # empty form -> errors
    expect(page.get_by_text("things still need attention")).to_be_visible()
    page.locator("#mship-name").fill("Nina Family")
    page.locator("#mship-number").fill("4242424242424242")
    page.locator("#mship-expiry").fill("1230")
    page.locator("#mship-cvc").fill("999")
    page.screenshot(path=f"{OUT}/membership_checkout.png", full_page=True)
    page.get_by_role("button", name="and apply").click()
    expect(page.get_by_text("Payment received")).to_be_visible()
    expect(page.get_by_text("•••• 4242")).to_be_visible()
    assert not any("4242" in body or "cvc" in body.lower() or "Nina Family" in body for body in sent), \
        "card details must never be sent"
    print("paid and applied:", EMAIL)

    page.get_by_role("button", name="Sign out").click()
    sign_in(page, *ADMIN)
    page.goto(f"{BASE}/admin/members")
    page.wait_for_timeout(1200)
    row = page.locator("tr", has_text=EMAIL)
    expect(row).to_be_visible()
    row.get_by_role("button", name="Approve").click()
    page.wait_for_timeout(1000)
    print("approved by admin")

    page.get_by_role("button", name="Sign out").click()
    sign_in(page, EMAIL, "Family123!")
    page.goto(f"{BASE}/account")
    page.wait_for_timeout(1200)
    expect(page.get_by_text("Active").first).to_be_visible()
    print("member is active")
    browser.close()
