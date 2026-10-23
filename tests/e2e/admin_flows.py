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
    staff = new(); sign_in(staff, "staff@museum.org", "Staff123!")
    staff.screenshot(path=f"{OUT}/staff_dashboard.png", full_page=True)
    staff.goto(f"{BASE}/staff/bookings"); staff.wait_for_timeout(1500)
    row = staff.locator("tr", has_text="SARHN-10006")
    row.get_by_role("button", name="Check in").click(); staff.wait_for_timeout(1000)
    print("checked in pill:", row.get_by_text("Checked in").count() == 1)
    staff.screenshot(path=f"{OUT}/staff_bookings.png", full_page=True)
    staff.fill("#bk-q", "SARHN-10004"); staff.wait_for_timeout(1200)
    print("search finds future booking:", staff.locator("tr", has_text="SARHN-10004").count() == 1)
    staff.get_by_role("tab", name="Event registrations").click()
    staff.select_option("#reg-event", index=2); staff.wait_for_timeout(1200)
    print("registration rows:", staff.locator("tbody tr").count())
    staff.screenshot(path=f"{OUT}/staff_registrations.png", full_page=True)
    admin = new(); sign_in(admin, "admin@museum.org", "Admin123!")
    admin.goto(f"{BASE}/admin/accounts"); admin.wait_for_timeout(1200)
    admin.fill("#staff-search", "tom"); admin.wait_for_timeout(1200)
    admin.get_by_role("button", name="Make staff").first.click()
    admin.get_by_role("dialog").get_by_role("button", name="Make staff").click(); admin.wait_for_timeout(1200)
    print("Tom now on team:", admin.locator("tr", has_text="tom.nguyen@example.com").count() == 1)
    admin.screenshot(path=f"{OUT}/admin_accounts.png", full_page=True)
    tom = new(); sign_in(tom, "tom.nguyen@example.com", "Visitor123!")
    print("Tom lands on:", tom.url.replace(BASE, ""))
    print("errors:", errors or "none"); b.close()
