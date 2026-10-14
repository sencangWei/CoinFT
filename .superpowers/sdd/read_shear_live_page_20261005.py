"""Read-only, short actual-page diagnostics; never fit, zero, POST or open serial."""
import json
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

expected = json.loads(Path('demo_web/shear_demo_profile.json').read_text(encoding='utf-8'))
result = {'pose': sys.argv[1], 'samples': [], 'errors': [], 'scope': 'diagnosis only, not a fitting or acceptance capture'}
try:
    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp('http://127.0.0.1:9225', timeout=2000)
        pages = [p for c in browser.contexts for p in c.pages if p.url == 'http://127.0.0.1:8765/']
        assert len(pages) == 1
        page = pages[0]
        until = time.monotonic() + 1.25
        while time.monotonic() < until:
            sample = page.evaluate('''async () => {
              const before = {frame:latestFrame, baseline:demoBaseline&&[...demoBaseline],
                channels:[...lastChannels], paused:demoPaused, normal:surfaceView.target,
                shear:surfaceView.shearTarget, renderedShear:surfaceView.shearLevel,
                zeroFrame:demoZeroFrame, profile:shearProfile};
              const backend = await (await fetch('/api/state', {
                cache:'no-store', signal:AbortSignal.timeout(1000)})).json();
              return {host:Date.now(), before, backend,
                after:{frame:latestFrame, baseline:demoBaseline&&[...demoBaseline],
                  paused:demoPaused, normal:surfaceView.target, shear:surfaceView.shearTarget},
                pageScore:before.baseline?shearScore(before.channels.map((x,i)=>x-before.baseline[i]),before.profile):null,
                backendScore:before.baseline?shearScore(backend.channels.map((x,i)=>x-before.baseline[i]),before.profile):null,
                status:document.getElementById('status-label').textContent};
            }''')
            sample['profile_matches_installed'] = sample['before']['profile'] == expected
            result['samples'].append(sample)
            time.sleep(0.1)
except Exception as exc:
    result['errors'].append(repr(exc))
print(json.dumps(result, ensure_ascii=False), flush=True)
raise SystemExit(bool(result['errors']))
