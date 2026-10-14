import json
from pathlib import Path
from playwright.sync_api import sync_playwright

state = Path(__file__).resolve().parents[1] / 'brainstorm/372-1790409834/state/server-info'
info = json.loads(state.read_text(encoding='utf-8'))
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge')
    page = browser.new_page(viewport={'width': 1500, 'height': 1000}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(info['url'], wait_until='domcontentloaded')
    page.wait_for_timeout(800)
    page.screenshot(path=str(Path(__file__).with_name('shear_drag_preview_20260926.png')), full_page=True)
    assert page.locator('canvas').count() == 3
    page.get_by_role('button', name='向左剪切（+X）', exact=True).click()
    page.wait_for_timeout(1200)
    left = page.locator('#readout').inner_text()
    assert '-0.85' in left, left
    page.get_by_role('button', name='空载回平', exact=True).click()
    page.wait_for_timeout(1200)
    released = page.locator('#readout').inner_text()
    assert released == '模拟剪切 0.00 / 正压 0.00', released
    assert not errors, errors
    print(json.dumps({'canvases': 3, 'left': left, 'released': released, 'page_errors': errors}, ensure_ascii=True))
    browser.close()
