"""Record only the live CoinFT page; run after explicit empty confirmation."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[2]
profile = root / "demo_web" / "shear_demo_profile.json"
expected_hash = "1df74f4570f5119f180f9e7830120abe555bd6c37cc33ab3dbc33b8dba5a6020"
assert hashlib.sha256(profile.read_bytes()).hexdigest() == expected_hash
output = root / "recordings" / datetime.now().strftime("demo_%Y%m%d_%H%M%S")
output.mkdir(parents=True, exist_ok=False)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        headless=False,
        args=["--remote-debugging-port=9225", "--window-size=1920,1200",
              "--disable-backgrounding-occluded-windows"],
    )
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        record_video_dir=str(output),
        record_video_size={"width": 1920, "height": 1080},
    )
    try:
        page = context.new_page()
        page.goto("http://127.0.0.1:8765/", wait_until="domcontentloaded", timeout=10000)
        page.wait_for_function("shearProfile.mode === 'qualitative' && latestFrame > 0", timeout=10000)
        assert page.evaluate("shearProfile") == json.loads(profile.read_text(encoding="utf-8"))
        page.locator("#demo-zero").click(timeout=5000)
        page.wait_for_function("demoBaseline !== null && demoZeroFrame < 0 && !demoPaused", timeout=5000)
        page.bring_to_front()
        page.screenshot(path=str(output / "ready.png"))
        video = page.video
        print(json.dumps({"status": "RECORDING", "output_dir": str(output),
                          "video": str(video.path()), "cdp": "http://127.0.0.1:9225",
                          "baseline": page.evaluate("demoBaseline"),
                          "profile_sha256": expected_hash}, ensure_ascii=False), flush=True)
        # Only this recording stops when its own stop marker is created.
        while not (output / "STOP").exists():
            page.wait_for_timeout(250)
    finally:
        context.close()
        browser.close()
    print(json.dumps({"status": "SAVED", "video": str(video.path())}, ensure_ascii=False), flush=True)
