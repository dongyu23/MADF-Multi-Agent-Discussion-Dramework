from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:5173/personas')
    
    print("Page loaded, waiting for network idle...")
    page.wait_for_load_state('networkidle')
    
    # Login if needed, but it seems we are already logged in or not required to?
    # Wait, the page might redirect to /auth/login.
    print(f"Current URL: {page.url}")
    if 'login' in page.url:
        page.fill('input[type="text"]', 'testuser')
        page.fill('input[type="password"]', 'testuser')
        page.click('button:has-text("登录")')
        page.wait_for_load_state('networkidle')
        print("Logged in.")
        page.goto('http://localhost:5173/personas')
        page.wait_for_load_state('networkidle')
        
    print("Clicking God Mode button...")
    # Click the God Mode button
    page.click('button:has-text("上帝模式")')
    page.wait_for_timeout(1000)
    
    print("Typing prompt...")
    page.fill('textarea', '生成爱因斯坦')
    page.click('button:has-text("发 送")')
    
    print("Waiting for generation...")
    # Wait for the generation to complete or error out
    start_time = time.time()
    while time.time() - start_time < 60:
        content = page.content()
        if "network error" in content or "❌" in content:
            print("ERROR DETECTED: network error")
            page.screenshot(path='/workspace/playwright_error.png')
            break
        if "生成完成" in content or "✅ 所有智能体角色已生成" in content:
            print("SUCCESS DETECTED")
            page.screenshot(path='/workspace/playwright_success.png')
            break
        time.sleep(2)
        print(f"Elapsed: {int(time.time() - start_time)}s")
    
    browser.close()
