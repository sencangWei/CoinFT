"""Show production live page without automatic tare or page zero."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

evidence_dir = Path(__file__).parent
snapshot_js = """({frame:latestFrame,baseline:demoBaseline,
normalTarget:surfaceView.target,shearTarget:surfaceView.shearTarget,
normalLevel:surfaceView.level,shearLevel:surfaceView.shearLevel,
label:document.querySelector('.surface-label').textContent,
status:document.getElementById('status-label').textContent})"""

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=False,
                                args=['--window-size=1440,960'])
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8765/', wait_until='domcontentloaded')
    page.bring_to_front()
    page.wait_for_function("shearProfile.mode === 'qualitative'", timeout=8000)
    page.wait_for_timeout(800)
    print(json.dumps({'snapshot': page.evaluate(snapshot_js), 'errors': errors,
                      'automatic_zero': False}, ensure_ascii=True), flush=True)
    print('LIVE_DRAG_WINDOW_READY: probe/shot/zero/reload/close', flush=True)
    while True:
        try:
            command = input().strip()
        except EOFError:
            break
        if command == 'close':
            break
        if command == 'reload':
            page.reload(wait_until='domcontentloaded')
            page.wait_for_timeout(800)
        if command == 'zero':
            # Caller must obtain operator confirmation of unloaded state first.
            page.locator('#demo-zero').click()
            page.wait_for_timeout(1600)
        if command == 'shot':
            target = evidence_dir / 'local-drag-live-page.png'
            page.screenshot(path=str(target), full_page=True)
            print(json.dumps({'screenshot': str(target)}, ensure_ascii=True), flush=True)
        if command in ('probe', 'shot', 'zero', 'reload'):
            print(json.dumps({'snapshot': page.evaluate(snapshot_js), 'errors': errors},
                             ensure_ascii=True), flush=True)
    browser.close()
