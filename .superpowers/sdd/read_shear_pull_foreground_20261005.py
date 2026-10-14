"""Short read-only live-window capture with a screenshot; no zero or device commands."""
import contextlib
import io
import json
import runpy
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

captured = io.StringIO()
with contextlib.redirect_stdout(captured):
    try:
        runpy.run_path(str(Path(__file__).with_name('read_shear_live_page_20261005.py')), run_name='__main__')
    except SystemExit as exc:
        capture_exit = exc.code
result = json.loads(captured.getvalue())
result['capture_exit'] = capture_exit
if not result['errors']:
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp('http://127.0.0.1:9225', timeout=2000)
            pages = [p for c in browser.contexts for p in c.pages if p.url == 'http://127.0.0.1:8765/']
            assert len(pages) == 1
            page = pages[0]
            result['screenshot_state'] = page.evaluate('({frame:latestFrame,baseline:demoBaseline,normal:surfaceView.level,shear:surfaceView.shearLevel,paused:demoPaused,visible:document.visibilityState})')
            screenshot = Path('.superpowers/sdd') / f'shear-pull-{sys.argv[1]}-20261005.png'
            assert not screenshot.exists(), 'Do not overwrite previous diagnostic screenshot'
            page.screenshot(path=str(screenshot))
            result['screenshot'] = str(screenshot)
    except Exception as exc:
        result['errors'].append(repr(exc))
print(json.dumps(result, ensure_ascii=False), flush=True)
raise SystemExit(bool(result['errors']))
