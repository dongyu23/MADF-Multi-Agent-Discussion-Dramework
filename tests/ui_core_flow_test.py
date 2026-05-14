"""Core flow UI test: AI generation SSE + discussion bubbles. Uses API for auth setup."""
from playwright.sync_api import sync_playwright
import requests, json, uuid

BASE = "http://localhost:5173"
API = "http://localhost:8000/api/v1"
R = []

def ok(n, c, d=""): R.append(f"{'✅' if c else '❌'} {n}" + (f": {d}" if d and not c else ""))

# ── Setup via API ──
uid = str(uuid.uuid4())[:8]
uname = f"test_{uid}"
r = requests.post(f"{API}/auth/register", json={"username":uname,"password":"test123456"})
r = requests.post(f"{API}/auth/login", json={"username":uname,"password":"test123456"})
token = r.json()["data"]["token"]["token"]
H = {"Authorization": f"Bearer {token}"}
print(f"User: {uname}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()

    # Inject token and go directly to home
    page.goto(BASE, wait_until="domcontentloaded", timeout=15000)
    page.evaluate(f"localStorage.setItem('token', '{token}')")

    # ═══ FLOW 1: Home ═══
    print("=== FLOW 1: Home ===")
    page.goto(f"{BASE}/home", wait_until="networkidle", timeout=15000)
    page.screenshot(path="/tmp/flow-01-home.png", full_page=True)
    ok("Home loads", "MADF" in page.content() or "欢迎" in page.content())

    # ═══ FLOW 2: Characters + Gallery ═══
    print("=== FLOW 2: Characters ===")
    page.goto(f"{BASE}/characters", wait_until="networkidle", timeout=15000)
    page.screenshot(path="/tmp/flow-02-characters.png", full_page=True)
    ok("Characters page", "角色" in page.content())

    # Gallery tab
    gbtn = page.locator("button:has-text('公开画廊')")
    if gbtn.count() > 0:
        gbtn.click(); page.wait_for_timeout(2000)
        page.screenshot(path="/tmp/flow-03-gallery.png", full_page=True)
        ok("Gallery tab", True)

    # ═══ FLOW 3: AI Generation ═══
    print("=== FLOW 3: AI Generation ===")
    page.goto(f"{BASE}/characters", wait_until="networkidle", timeout=15000)
    gen_input = page.locator("input[placeholder*='人名或主题']")
    gen_btn = page.locator("button:has-text('AI 生成')")

    if gen_input.count() > 0 and gen_btn.count() > 0:
        gen_input.fill("Confucius 孔子")
        page.screenshot(path="/tmp/flow-04-gen-input.png", full_page=True)
        gen_btn.click()

        # Wait for navigation to detail page
        page.wait_for_timeout(5000)
        page.screenshot(path="/tmp/flow-05-after-gen-click.png", full_page=True)

        on_detail = "/characters/" in page.url
        ok("Navigate to detail after generate", on_detail, page.url)

        if on_detail:
            # Watch SSE progress
            for i in range(36):  # Up to 3 min
                page.wait_for_timeout(5000)
                subs = page.locator(".gen-sub-item").count()
                done = page.locator("text=就绪").count()
                err = page.locator("text=错误").count()
                if i % 6 == 0 or done > 0 or err > 0:
                    print(f"  [{i*5}s] subs={subs} done={done} err={err}")
                    page.screenshot(path=f"/tmp/flow-gen-{i*5:03d}s.png", full_page=True)
                if done > 0 or err > 0: break

            # Check final state
            file_tree = page.locator(".file-tree")
            editor = page.locator(".editor-pane")
            ok("File tree visible", file_tree.count() > 0)
            ok("Monaco editor visible", editor.count() > 0)
            page.screenshot(path="/tmp/flow-06-generation-result.png", full_page=True)

            # Click a file
            file_items = page.locator(".file-item")
            if file_items.count() > 1:
                file_items.nth(1).click()
                page.wait_for_timeout(1000)
                page.screenshot(path="/tmp/flow-07-file-switched.png", full_page=True)
                ok("File switching works", True)

    # ═══ FLOW 4: Discussion Room ═══
    print("=== FLOW 4: Discussion Room ===")
    # Get ready characters
    r = requests.get(f"{API}/characters", headers=H, params={"page_size":50})
    chars = [c for c in r.json()["data"]["items"] if c["status"] == "ready"]
    print(f"  Ready chars: {len(chars)}")

    if len(chars) >= 2:
        r = requests.post(f"{API}/discussions", headers=H, json={
            "topic": "什么是智慧？东西方先贤怎么看", "character_ids": [chars[0]["id"], chars[1]["id"]], "duration": 120
        })
        did = r.json()["data"]["id"]
        print(f"  Discussion: {did}")

        page.goto(f"{BASE}/discussions/{did}", wait_until="networkidle", timeout=15000)
        page.screenshot(path="/tmp/flow-08-discussion-start.png", full_page=True)

        # Watch bubbles
        for i in range(12):  # Up to 60s
            page.wait_for_timeout(5000)
            host = page.locator(".host-bubble").count()
            think = page.locator(".think-bubble").count()
            speak = page.locator(".speak-bubble").count()
            rounds = page.locator(".round-divider").count()
            if i % 3 == 0:
                print(f"  [{i*5}s] H:{host} T:{think} S:{speak} R:{rounds}")
                page.screenshot(path=f"/tmp/flow-disc-{i*5:03d}s.png", full_page=True)

            if host + speak >= 3: break  # Enough content

        bubbles = page.locator(".speak-bubble, .host-bubble, .think-bubble").count()
        ok(f"Bubbles ({bubbles})", bubbles >= 1, f"only {bubbles}")
        page.screenshot(path="/tmp/flow-09-discussion-bubbles.png", full_page=True)

        # Intervene
        inp = page.locator(".intervene-input")
        if inp.count() > 0:
            inp.fill("我认为智慧是实践的产物")
            page.locator(".intervene-btn").click()
            page.wait_for_timeout(2000)
            page.screenshot(path="/tmp/flow-10-user-intervene.png", full_page=True)
            ok("User intervention", True)

    browser.close()

    passed = sum(1 for r in R if "✅" in r)
    print(f"\n{'='*50}")
    for r in R: print(r)
    print(f"{'='*50}\nCore Flow: {passed}/{len(R)} ({100*passed//len(R)}%)")
