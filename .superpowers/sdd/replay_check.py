from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://127.0.0.1:18765/")
    levels = []
    loaded = False
    released = False
    for _ in range(70):
        page.wait_for_timeout(300)
        target = page.evaluate("surfaceView.target")
        levels.append(target)
        if target > 0.8 and not loaded:
            loaded = True
            page.screenshot(path=".superpowers/sdd/replay-real-loaded.png", full_page=True)
        if loaded and target == 0:
            released = True
            page.screenshot(path=".superpowers/sdd/replay-real-released.png", full_page=True)
            break
    print({"mode": page.locator("#mode-label").inner_text(),
           "min_target": min(levels), "max_target": max(levels),
           "loaded": loaded, "released": released, "page_errors": errors})
    assert loaded and released and not errors
    browser.close()
