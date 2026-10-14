"""Open the verified local demo; only its browser-local zero button is used."""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[2]
expected = json.loads((root / 'demo_web/shear_demo_profile.json').read_text(encoding='utf-8'))
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False, args=['--start-maximized'])
    page = browser.new_page(no_viewport=True)
    errors = []
    posts = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: posts.append(request.url) if request.method == 'POST' else None)
    page.goto('http://127.0.0.1:8765/', wait_until='domcontentloaded')
    page.wait_for_function("typeof shearProfile !== 'undefined' && shearProfile.mode === 'qualitative' && !document.getElementById('demo-zero').disabled", timeout=10000)
    assert page.evaluate('shearProfile') == expected
    page.locator('#demo-zero').click()
    page.wait_for_function('demoBaseline !== null && demoZeroSamples.length === 0', timeout=10000)
    before = page.evaluate('latestFrame')
    page.wait_for_function('(f) => latestFrame > f', arg=before, timeout=3000)
    state = page.evaluate("({baseline:demoBaseline, frames:latestFrame, normal:surfaceView.target, shear:surfaceView.shearTarget, paused:demoPaused, button:document.getElementById('demo-zero').textContent})")
    assert not errors and not posts
    assert state['normal'] == 0 and state['shear'] == 0 and not state['paused']
    page.screenshot(path=str(root / '.superpowers/sdd/shear-demo-live-empty-20261005.png'), full_page=True)
    print(json.dumps({'ready': True, 'state': state, 'page_errors': errors, 'posts': posts}, ensure_ascii=False), flush=True)
    try:
        while browser.is_connected() and not page.is_closed():
            page.wait_for_timeout(1000)
    finally:
        browser.close()
