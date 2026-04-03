from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Try to open the personas page directly (it might redirect if not logged in)
    page.goto('http://localhost:5173/personas')
    page.wait_for_load_state('networkidle')
    
    if "login" in page.url:
        print("Redirected to login, authenticating...")
        page.fill('input[placeholder="用户名"]', 'admin')
        page.fill('input[placeholder="密码"]', 'admin')
        page.click('button:has-text("登 录")')
        page.wait_for_url('**/dashboard')
        page.goto('http://localhost:5173/personas')
        page.wait_for_load_state('networkidle')

    print("Checking PersonaView.vue for God Mode button...")
    god_btn = page.locator('button', has_text='调用上帝模式')
    
    if god_btn.count() > 0:
        print("God Mode button found! Clicking...")
        god_btn.click()
        page.wait_for_timeout(1000)
        
        modal_title = page.locator('.ant-modal-title').first
        if modal_title.count() > 0 and "上帝模式" in modal_title.inner_text():
            print("God Mode modal opened successfully.")
            
            # Send a message
            print("Sending a message to God Mode agent...")
            text_area = page.locator('.chat-textarea').first
            if text_area.count() > 0:
                 text_area.fill("帮我创建一个后端架构师智能体")
                 page.locator('.send-btn').first.click()
                 print("Message sent.")
                 page.wait_for_timeout(3000)
            else:
                 print("Could not find chat textarea.")
        else:
            print("Modal did not open or title mismatch.")
    else:
        print("Could not find the God Mode button.")
        
    browser.close()
