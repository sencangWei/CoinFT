"""Visible live smoke-test window; never sends device tare or serial commands."""
import json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).parent
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
snapshot_js = """({at:performance.now(),frame:latestFrame,baseline:demoBaseline,
target:surfaceView.target,shearTarget:surfaceView.shearTarget,
level:surfaceView.level,shearLevel:surfaceView.shearLevel,
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
    page.wait_for_function("shearProfile.mode === 'qualitative' && !document.getElementById('demo-zero').disabled", timeout=8000)
    before = page.request.get('http://127.0.0.1:8765/api/state').json()
    page.locator('#demo-zero').click()
    outcome = 'ready'
    try:
        page.wait_for_function('demoBaseline !== null', timeout=5000)
    except Exception:
        outcome = 'not_ready'
    samples = []
    for _ in range(50):
        samples.append(page.evaluate(snapshot_js))
        page.wait_for_timeout(100)
    screenshot = root / ('live_zero_' + stamp + '.png')
    page.screenshot(path=str(screenshot), full_page=True)
    evidence = root / ('live_zero_' + stamp + '.json')
    after = page.request.get('http://127.0.0.1:8765/api/state').json()
    with evidence.open('x', encoding='utf-8') as file:
        json.dump({'outcome': outcome, 'samples': samples, 'errors': errors,
                   'screenshot': str(screenshot), 'before':before, 'after':after}, file, ensure_ascii=False, indent=2)
    print(json.dumps({'outcome': outcome, 'last': samples[-1], 'errors': errors,
                      'screenshot': str(screenshot), 'evidence': str(evidence),
                      'baselineKept':all(sample['baseline'] is not None for sample in samples),
                      'maxNormal':max(sample['target'] for sample in samples),
                      'maxShear':max(abs(sample['shearTarget']) for sample in samples),
                      'frameAdvance':after['frames']-before['frames']},
                     ensure_ascii=True), flush=True)
    print('LIVE_WINDOW_READY: awaiting probe/zero/close commands', flush=True)
    while True:
        try:
            command = input().strip()
        except EOFError:
            break
        if command == 'close':
            break
        if command == 'zero':
            page.locator('#demo-zero').click()
            page.wait_for_timeout(1500)
        if command in ('probe', 'zero'):
            print(json.dumps(page.evaluate(snapshot_js), ensure_ascii=True), flush=True)
    browser.close()
