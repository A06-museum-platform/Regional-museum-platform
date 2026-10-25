"""Book tickets through the real UI as Ben, then cancel from the confirmation
page. Mirrors the demo script: /book -> /book/details -> confirmation."""
from playwright.sync_api import expect, sync_playwright

import os
import re
BASE = os.environ.get("E2E_BASE_URL", "http://localhost:5173")
OUT = os.environ.get("E2E_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots"))

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith(BASE) else r.abort())
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("response", lambda r: "/api/" in r.url and r.status >= 400
            and errors.append(f"{r.status} {r.url}"))

    # Step 1 is public: choose before signing in, the draft survives sign-in.
    page.goto(f"{BASE}/book")
    page.locator('[aria-label="Next open days"] button').first.click()
    page.locator('input[type=radio]').first.check()
    page.get_by_label("Add one Adult ticket").click()
    page.get_by_label("Add one Adult ticket").click()
    page.get_by_label("Add one Child ticket").click()
    page.screenshot(path=f"{OUT}/flow_1_choose.png", full_page=True)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_timeout(800)
    print("after continue:", page.url)

    if "/signin" in page.url:
        page.fill("input[type=email]", "ben@example.com")
        page.fill("input[type=password]", "Member123!")
        page.press("input[type=password]", "Enter")
        page.wait_for_timeout(1200)
        print("after sign in:", page.url)

    page.screenshot(path=f"{OUT}/flow_2_details.png", full_page=True)
    page.locator("#bk-mobile").fill("0400 000 002")
    page.locator('input[type=checkbox]').first.check()      # step-free access
    if page.locator("#bk-card-number").count():               # demonstration card form
        page.locator("#bk-card-name").fill("Ben Wilson")
        page.locator("#bk-card-number").fill("4111111111111111")
        page.locator("#bk-card-expiry").fill("0829")
        page.locator("#bk-card-cvc").fill("123")
    page.get_by_role("button", name=re.compile(r"and book$|^Confirm booking$")).click()
    page.wait_for_url("**/book/confirmation/**", timeout=10000)
    page.wait_for_timeout(800)
    reference = page.url.rsplit("/", 1)[-1]
    print("confirmation:", reference)
    page.screenshot(path=f"{OUT}/flow_3_confirmation.png", full_page=True)

    page.goto(f"{BASE}/account")
    page.wait_for_timeout(1000)
    expect(page.get_by_text(reference).first).to_be_visible()
    print("listed on /account: yes")

    page.goto(f"{BASE}/book/confirmation/{reference}")
    page.wait_for_timeout(800)
    page.get_by_role("button", name="Cancel").first.click()
    page.wait_for_timeout(500)
    dialog_confirm = page.get_by_role("dialog").get_by_role("button").last
    if dialog_confirm.count():
        dialog_confirm.click()
    page.wait_for_timeout(1000)
    page.screenshot(path=f"{OUT}/flow_4_cancelled.png", full_page=True)
    print("page mentions cancelled:", page.get_by_text("ancelled").count() > 0)
    print("errors:", errors or "none")
    browser.close()
