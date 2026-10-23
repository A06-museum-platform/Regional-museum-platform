from playwright.sync_api import expect, sync_playwright
import os
BASE = os.environ.get("E2E_BASE_URL", "http://localhost:5173"); OUT = os.environ.get("E2E_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots"))

def sign_in(page, email, pw):
    page.goto(f"{BASE}/signin"); page.fill("input[type=email]", email)
    page.fill("input[type=password]", pw); page.press("input[type=password]", "Enter"); page.wait_for_timeout(1200)

with sync_playwright() as p:
    b = p.chromium.launch(); errors = []
    def new():
        c = b.new_context(viewport={"width": 1280, "height": 900})
        c.route("**/*", lambda r: r.continue_() if r.request.url.startswith(BASE) else r.abort())
        pg = c.new_page(); pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("response", lambda r: "/api/" in r.url and r.status >= 500 and errors.append(f"{r.status} {r.url}"))
        return pg
    ben = new(); sign_in(ben, "ben@example.com", "Member123!")
    # register for a recommended workshop
    ben.goto(f"{BASE}/account"); ben.wait_for_timeout(1500)
    print("recommendation cards:", ben.locator("text=Matches your interest").count())
    first_event = ben.locator("a", has_text="Workshop").first
    first_event.click(); ben.wait_for_timeout(1000)
    ben.get_by_role("button", name="Register (simulated)").click(); ben.wait_for_timeout(1000)
    expect(ben.get_by_text("You are registered")).to_be_visible()
    ben.goto(f"{BASE}/account"); ben.wait_for_timeout(1500)
    ben.screenshot(path=f"{OUT}/member_portal.png", full_page=True)
    print("activity mentions registration:", ben.get_by_text("Registered for an event").count() > 0)
    # change interests
    ben.get_by_role("button", name="Change interests").click()
    ben.get_by_role("button", name="Sea, ships and whaling").click()
    ben.get_by_role("button", name="Save interests").click(); ben.wait_for_timeout(1200)
    print("maritime matches:", ben.locator("text=sea, ships and whaling").count())
    # cancel registration
    regs = ben.locator("section", has=ben.get_by_role("heading", name="Workshops and events"))
    regs.get_by_role("button", name="Cancel").first.click()
    ben.get_by_role("dialog").get_by_role("button", name="Cancel registration").click(); ben.wait_for_timeout(1200)
    print("cancelled pill:", regs.get_by_text("Cancelled").count() > 0)
    alice = new(); sign_in(alice, "alice@example.com", "Visitor123!")
    alice.goto(f"{BASE}/account"); alice.wait_for_timeout(1200)
    print("visitor sees member-benefit note:", alice.get_by_text("Recommendations are a member benefit").count() > 0)
    alice.screenshot(path=f"{OUT}/visitor_portal.png", full_page=True)
    staff = new(); sign_in(staff, "staff@museum.org", "Staff123!")
    staff.goto(f"{BASE}/staff/events"); staff.wait_for_timeout(1200)
    staff.locator("tr", has_text="Morse code").get_by_role("button", name="Edit").click(); staff.wait_for_timeout(800)
    print("editor tag chips pressed:", staff.locator("[aria-pressed=true]").count())
    staff.screenshot(path=f"{OUT}/staff_editor_tags.png", full_page=True)
    print("errors:", errors or "none"); b.close()
