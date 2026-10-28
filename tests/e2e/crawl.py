"""Visit every route as each role against the running dev server and report
console errors, failed /api calls and a screenshot per page.

Usage: python crawl.py [outdir]
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import os
BASE = os.environ.get("E2E_BASE_URL", "http://localhost:5173")
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("E2E_OUT", Path(__file__).resolve().parent / "screenshots"))
OUT.mkdir(parents=True, exist_ok=True)

ACCOUNTS = {
    "anon": None,
    "visitor": ("alice@example.com", "Visitor123!"),
    "member": ("ben@example.com", "Member123!"),
    "staff": ("staff@museum.org", "Staff123!"),
    "admin": ("admin@museum.org", "Admin123!"),
}
ROUTES = {
    "anon": ["/", "/collections", "/events", "/exhibitions", "/exhibitions/working-the-monster-mine",
             "/visit", "/membership", "/book", "/signin", "/register"],
    "visitor": ["/membership", "/book", "/account"],
    "member": ["/account", "/membership", "/book"],
    "staff": ["/staff", "/staff/content", "/staff/events", "/staff/hours", "/staff/visit", "/staff/media",
              "/staff/bookings"],
    "admin": ["/admin/members", "/admin/accounts", "/admin/activity"],
}


def main():
    problems = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("PLAYWRIGHT_EXECUTABLE_PATH") or None)
        for role, creds in ACCOUNTS.items():
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            # External images/fonts can't load in this sandbox; skip them quietly.
            ctx.route("**/*", lambda r: r.continue_() if r.request.url.startswith(BASE) else r.abort())
            page = ctx.new_page()
            log = []
            page.on("console", lambda m: m.type == "error" and "Failed to load resource: net::" not in m.text and log.append(f"console: {m.text[:200]}"))
            page.on("pageerror", lambda e: log.append(f"pageerror: {str(e)[:200]}"))
            page.on("response", lambda r: "/api/" in r.url and r.status >= 400
                    and log.append(f"{r.status} {r.request.method} {r.url.replace(BASE, '')}"))
            if creds:
                page.goto(f"{BASE}/signin")
                page.fill("input[type=email]", creds[0])
                page.fill("input[type=password]", creds[1])
                page.press("input[type=password]", "Enter")
                page.wait_for_timeout(1200)
                if "/signin" in page.url:
                    problems.append((role, "/signin", "Login did not complete"))
            for route in ROUTES[role]:
                log.clear()
                page.goto(f"{BASE}{route}")
                page.wait_for_timeout(1500)
                name = f"{role}{route.replace('/', '_') or '_home'}"
                page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
                if route.startswith(("/staff", "/admin")) and "/signin" in page.url:
                    log.append("Protected page unexpectedly redirected to sign-in")
                h1 = page.locator("h1").first.inner_text() if page.locator("h1").count() else "-"
                status = "OK" if not log else "ISSUES"
                print(f"[{status}] {role:8} {route:20} h1={h1[:50]!r}")
                for line in dict.fromkeys(log):
                    print(f"      {line}")
                    problems.append((role, route, line))
            ctx.close()
        browser.close()
    print(f"\n{len(problems)} problems")
    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
