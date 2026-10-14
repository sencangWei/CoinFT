"""Isolated screenshot and projected-orientation evidence, never live hardware."""
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from coinft_demo import make_handler
from tests.test_demo_ui import FakeSource
from tests.test_surface_drag import PROFILE, SurfaceDragTests, area, material_geometry, material_quality
from playwright.sync_api import sync_playwright


class Source(FakeSource):
    def snapshot(self):
        state = super().snapshot()
        state.update(mode="replay", status="replay", port="SIMULATED", invalid_recent=0)
        return state


server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Source()))
threading.Thread(target=server.serve_forever, daemon=True).start()
evidence = Path(__file__).resolve().parent
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(reduced_motion="reduce", viewport={"width": 1440, "height": 1000})
        page.add_init_script("""(() => {
            const original = window.setInterval;
            window.setInterval = (callback, delay) => {
                const id = original(callback, delay);
                if (callback.name === 'poll') window.testPollTimer = id;
                return id;
            };
        })()""")
        page.route("**/shear_profile.json", lambda route: route.fulfill(status=404))
        page.route("**/shear_demo_profile.json", lambda route: route.fulfill(status=404))
        page.goto(f"http://127.0.0.1:{server.server_port}/")
        page.wait_for_function("typeof surfaceView !== 'undefined'")
        page.evaluate("""() => {
            clearInterval(testPollTimer);
            const label = document.createElement('div');
            label.textContent = '模拟验收，非实时设备 · SYNTHETIC LOCAL DRAG';
            label.style = 'position:fixed;top:0;left:0;z-index:9999;background:#843;color:white;padding:10px';
            document.body.append(label);
        }""")
        for name, p, s in (("right", 0, 1), ("left", 0, -1), ("normal", 1, 0),
                           ("combined", 1, 1), ("clear", 0, 0)):
            channels = [s * 100] * 4 + [-s * 100] * 4 + [p * 700] * 4
            page.evaluate("args => surfaceView.set(args.channels, args.profile)",
                          {"channels": channels, "profile": PROFILE})
            page.screenshot(path=str(evidence / f"local-drag-{name}.png"), full_page=True)
        browser.close()
finally:
    server.shutdown()
    server.server_close()

SurfaceDragTests.setUpClass()
try:
    case = SurfaceDragTests()
    case.setUp()
    result = []
    for p in (0, 1):
        for s in (-1, 0, 1):
            cells = case.draw(p, s)["cells"]
            signed = [area(*(cell[k] for k in corners)) for cell in cells
                      for corners in ((0, 1, 2), (0, 2, 3))]
            result.append({"p": p, "s": s, "reversed": sum(a < 0 for a in signed),
                           "min_area": min(signed), "max_area": max(signed)})
            planar_areas, crossings = material_quality(material_geometry(cells, p, s))
            result[-1].update(material_min_area=min(planar_areas), material_crossings=crossings)
    print(json.dumps({"isolated_port": server.server_port, "geometry": result}, indent=2))
    case.tearDown()
finally:
    SurfaceDragTests.tearDownClass()
