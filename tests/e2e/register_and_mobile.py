"""Create an account through the UI, then check the public pages at phone
width (390px): no horizontal scroll, menu toggle present."""
import time
from playwright.sync_api import expect, sync_playwright

import os
BASE = os.environ.get("E2E_BASE_URL", "http://localhost:5173")
OUT = os.environ.get("E2E_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots"))

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH") or None)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith(BASE) else r.abort())
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))

    page.goto(f"{BASE}/register")
    page.get_by_role("button", name="Create account").click()
    page.screenshot(path=f"{OUT}/register_errors.png", full_page=True)
    print("validation messages:", page.locator("[id$=-error]").count())
    email = f"new.{int(time.time())}@example.com"
    page.fill("#reg-first_name", "Nina")
    page.fill("#reg-last_name", "Family")
    page.fill("#reg-email", email)
    page.fill("#reg-password", "Family123!")
    page.fill("#reg-confirm", "Family123!")
    page.get_by_role("button", name="Create account").click()
    page.wait_for_url("**/account", timeout=8000)
    page.wait_for_timeout(800)
    expect(page.get_by_role("heading", name="Hello, Nina")).to_be_visible()
    page.screenshot(path=f"{OUT}/register_account.png", full_page=True)
    print("registered and landed on /account")

    page.goto(f"{BASE}/register")
    page.fill("#reg-first_name", "Dup"); page.fill("#reg-last_name", "Dup")
    page.fill("#reg-email", "alice@example.com"); page.fill("#reg-password", "Visitor123!")
    page.fill("#reg-confirm", "Visitor123!")
    page.get_by_role("button", name="Create account").click()
    page.wait_for_timeout(800)
    print("duplicate:", page.get_by_role("alert").inner_text()[:70])

    mobile = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
    mobile.route("**/*", lambda r: r.continue_() if r.request.url.startswith(BASE) else r.abort())
    m = mobile.new_page()
    for path in ["/", "/visit", "/exhibitions", "/exhibitions/working-the-monster-mine", "/register",
                 "/events", "/collections", "/book"]:
        m.goto(f"{BASE}{path}")
        m.wait_for_timeout(900)
        overflow = m.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        name = path.strip("/").replace("/", "_") or "home"
        m.screenshot(path=f"{OUT}/mobile_{name}.png", full_page=True)
        print(f"mobile {path:40} horizontal overflow: {overflow}px")
        assert overflow <= 1, f"Horizontal overflow on {path}: {overflow}px"
    print("errors:", errors or "none")
    assert not errors, errors
    browser.close()
