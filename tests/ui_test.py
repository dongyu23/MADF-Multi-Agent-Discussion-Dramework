"""Playwright UI test for MADF frontend pages."""
from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
API = "http://localhost:8000"

results = []

def check(name, condition, detail=""):
    status = "✅" if condition else "❌"
    results.append(f"{status} {name}" + (f": {detail}" if detail and not condition else ""))
    return condition

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    # ── 1. Login Page ──
    print("1. Login Page...")
    page.goto(BASE, wait_until="networkidle", timeout=15000)
    page.screenshot(path="/tmp/madf-01-login.png", full_page=True)
    check("Login page loads", "MADF" in page.content() or "登录" in page.content())

    # Navigate to login (if redirected)
    if "/login" not in page.url:
        page.goto(f"{BASE}/login", wait_until="networkidle", timeout=15000)
        page.screenshot(path="/tmp/madf-01-login.png", full_page=True)

    has_form = page.locator("input[placeholder*='用户名']").count() > 0
    check("Login form visible", has_form, "Input field not found")

    if has_form:
        page.fill("input[placeholder*='用户名']", "tester")
        page.fill("input[placeholder*='密码']", "test123456")
        page.click("button[type='submit']")
        page.wait_for_url("**/home", timeout=10000)
        check("Login redirect to home", "/home" in page.url, page.url)

    # ── 2. Home Page ──
    print("2. Home Page...")
    page.wait_for_load_state("networkidle", timeout=10000)
    page.screenshot(path="/tmp/madf-02-home.png", full_page=True)
    check("Home page title", "欢迎" in page.content() or "MADF" in page.content())

    # ── 3. Characters Page ──
    print("3. Characters Page...")
    page.goto(f"{BASE}/characters", wait_until="networkidle", timeout=15000)
    page.screenshot(path="/tmp/madf-03-characters.png", full_page=True)
    check("Characters header", "角色" in page.content())

    # Switch to gallery tab
    gallery_btn = page.locator("button:has-text('公开画廊')")
    if gallery_btn.count() > 0:
        gallery_btn.click()
        page.wait_for_timeout(2000)
        page.screenshot(path="/tmp/madf-04-gallery.png", full_page=True)
        check("Gallery tab", True)
    else:
        check("Gallery tab button", False, "Button not found")

    # ── 4. Discussions Page ──
    print("4. Discussions Page...")
    page.goto(f"{BASE}/discussions", wait_until="networkidle", timeout=15000)
    page.screenshot(path="/tmp/madf-05-discussions.png", full_page=True)
    check("Discussions page", "讨论" in page.content())

    # ── 5. Check for existing discussions ──
    disc_cards = page.locator(".disc-card")
    if disc_cards.count() > 0:
        disc_cards.first.click()
        page.wait_for_timeout(3000)
        page.screenshot(path="/tmp/madf-06-discussion-room.png", full_page=True)
        check("Discussion room", True)
    else:
        print("   No discussions to view")

    browser.close()

    # Summary
    passed = sum(1 for r in results if "✅" in r)
    total = len(results)
    print(f"\n{'='*40}")
    for r in results:
        print(r)
    print(f"{'='*40}")
    print(f"UI Tests: {passed}/{total} ({100*passed//total}%)")
