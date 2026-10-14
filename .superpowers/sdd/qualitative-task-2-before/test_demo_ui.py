"""Browser checks for the CoinFT dashboard's data-quality warning."""

import json
import math
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

from coinft_demo import make_handler


class FakeSource:
    def snapshot(self):
        return {
            "mode": "live", "status": "live", "message": "数据流正常", "port": "COM10",
            "axes": [0.0] * 6, "channels": [0.0] * 12, "raw": [10000] * 12,
            "rate": 200.0, "frames": 100, "resyncs": 0, "saturated_recent": 0,
            "invalid_frames": 3, "invalid_recent": 3, "tare_progress": 100,
        }


class DashboardWarningTests(unittest.TestCase):
    def test_older_frame_cannot_lower_surface_high_water(self):
        class ChangingSource(FakeSource):
            frames = 200
            channels = [700.0] * 12

            def snapshot(self):
                state = super().snapshot()
                state.update(frames=self.frames, channels=self.channels,
                             invalid_recent=0)
                return state

        source = ChangingSource()
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(source))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(reduced_motion="reduce")
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.wait_for_function("surfaceView.target === 1 && latestFrame === 200")
                source.frames = 199
                page.wait_for_function("surfaceView.target === 0")
                self.assertEqual(page.evaluate("latestFrame"), 200)
                source.frames = 200
                page.wait_for_timeout(150)
                self.assertEqual(page.evaluate("surfaceView.target"), 0)
                source.frames = 201
                page.wait_for_function("surfaceView.target === 1 && latestFrame === 201")
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_failed_tare_post_releases_gate_and_button(self):
        class ChangingSource(FakeSource):
            frames = 200

            def snapshot(self):
                state = super().snapshot()
                state.update(frames=self.frames, channels=[700.0] * 12,
                             invalid_recent=0)
                return state

        source = ChangingSource()
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(source))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(reduced_motion="reduce")
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.wait_for_function("surfaceView.target === 1 && latestFrame === 200")
                page.route("**/api/tare", lambda route: route.fulfill(status=503))
                page.locator("#tare").click()
                page.wait_for_function("tarePending === false && !document.getElementById('tare').disabled",
                                       timeout=1000)
                source.frames = 201
                page.wait_for_function("surfaceView.target === 1 && latestFrame === 201")
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_fast_taring_cycle_hidden_by_poll_recovers_after_ack(self):
        class FastTareSource(FakeSource):
            frames = 200

            def snapshot(self):
                state = super().snapshot()
                state.update(frames=self.frames, channels=[700.0] * 12,
                             invalid_recent=0)
                return state

            def request_tare(self):
                self.frames += 1

        source = FastTareSource()
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(source))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(reduced_motion="reduce")
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.wait_for_function("surfaceView.target === 1 && latestFrame === 200")
                page.evaluate("""() => {
                    window.realFetch = window.fetch;
                    window.heldPoll = null;
                    window.fetch = (input, options) => input === '/api/state' ?
                        new Promise(resolve => { heldPoll = resolve; }) :
                        realFetch(input, options);
                }""")
                page.wait_for_function("fetching && typeof heldPoll === 'function'")
                page.locator("#tare").click()
                page.evaluate("""() => {
                    heldPoll(new Response(JSON.stringify({
                        mode: 'live', status: 'live', message: 'pre-tare', port: 'COM10',
                        axes: Array(6).fill(0), channels: Array(12).fill(700),
                        rate: 200, frames: 201, invalid_recent: 0,
                        saturated_recent: 0, invalid_frames: 0,
                        tare_progress: 100, resyncs: 0
                    }), {status: 200, headers: {'Content-Type': 'application/json'}}));
                    window.fetch = window.realFetch;
                }""")
                page.wait_for_function("surfaceView.target === 1 && latestFrame === 201",
                                       timeout=1000)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_signed_surface_profile_and_safe_states(self):
        class ChangingSource(FakeSource):
            channels = [0.0] * 12
            frames = 100
            status = "live"
            invalid_recent = 0
            saturated_recent = 0

            def snapshot(self):
                state = super().snapshot()
                state.update(channels=self.channels, frames=self.frames,
                             status=self.status, invalid_recent=self.invalid_recent,
                             saturated_recent=self.saturated_recent)
                return state

            def request_tare(self):
                self.status = "taring"

        profile = {
            "version": 1, "assemblyId": "synthetic-test-only",
            "normal": {"threshold": 100, "span": 600},
            "shear": {"enabled": True, "weights": [0.125] * 4 + [-0.125] * 4,
                      "pressLeak": [0.1] * 4 + [-0.1] * 4,
                      "threshold": 20, "span": 80},
            "rightLabel": "test screen right", "leftLabel": "test screen left",
            "evidence": ["synthetic_train.json", "synthetic_holdout.json"],
        }
        source = ChangingSource()
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(source))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(reduced_motion="reduce")
                page.route("**/shear_profile.json", lambda route: route.fulfill(
                    status=200, content_type="application/json", body=json.dumps(profile)))
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.wait_for_function("typeof shearLevel === 'function'")
                self.assertEqual(page.evaluate("""() => [
                    normalLevel([...Array(8).fill(900), ...Array(4).fill(0)], shearProfile),
                    shearLevel(Array(12).fill(0), shearProfile),
                    shearLevel([70,70,70,70,-70,-70,-70,-70,700,700,700,700], shearProfile)
                ]"""), [0, 0, 0])
                source.channels = [70] * 4 + [-70] * 4 + [700] * 4
                source.frames += 1
                page.wait_for_function("surfaceView.target === 1 && surfaceView.shearTarget === 0")
                self.assertEqual(page.evaluate("surfaceView.shearLevel"), 0)
                source.channels = [100] * 4 + [-100] * 4 + [0] * 4
                source.frames += 1
                page.wait_for_function("surfaceView.shearTarget > 0 && surfaceView.shearLevel === surfaceView.shearTarget")
                right = page.evaluate("""() => {
                    const canvas = document.getElementById('surface-canvas');
                    const {data, width, height} = canvas.getContext('2d').getImageData(
                        0, 0, canvas.width, canvas.height);
                    let weighted = 0, count = 0;
                    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
                        const alpha = data[(y * width + x) * 4 + 3];
                        weighted += x * alpha; count += alpha;
                    }
                    return weighted / count;
                }""")
                source.channels = [-100] * 4 + [100] * 4 + [0] * 4
                source.frames += 1
                page.wait_for_function("surfaceView.shearTarget < 0 && surfaceView.shearLevel === surfaceView.shearTarget")
                left = page.evaluate("""() => {
                    const canvas = document.getElementById('surface-canvas');
                    const {data, width, height} = canvas.getContext('2d').getImageData(
                        0, 0, canvas.width, canvas.height);
                    let weighted = 0, count = 0;
                    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
                        const alpha = data[(y * width + x) * 4 + 3];
                        weighted += x * alpha; count += alpha;
                    }
                    return weighted / count;
                }""")
                self.assertGreater(right - left, 5)
                source.channels = [170] * 4 + [-170] * 4 + [700] * 4
                source.frames += 1
                page.wait_for_function("surfaceView.target === 1 && surfaceView.shearTarget > 0")
                page.wait_for_function("surfaceView.target === 0 && surfaceView.shearTarget === 0",
                                       timeout=2000)
                source.frames += 1
                page.wait_for_function("surfaceView.target === 1 && surfaceView.shearTarget > 0")
                source.invalid_recent = 1
                source.frames += 1
                page.wait_for_function("surfaceView.target === 0 && surfaceView.shearTarget === 0")
                source.invalid_recent = 0
                source.saturated_recent = 1
                source.frames += 1
                page.wait_for_function("surfaceView.target === 0 && surfaceView.shearTarget === 0")
                source.saturated_recent = 0
                source.frames += 1
                page.wait_for_function("surfaceView.target === 1 && surfaceView.shearTarget > 0")
                page.locator("#tare").click()
                page.wait_for_function("surfaceView.target === 0 && surfaceView.shearTarget === 0")
                self.assertEqual(page.evaluate("[surfaceView.level, surfaceView.shearLevel]"), [0, 0])
                page.wait_for_function("document.querySelector('#status-label').textContent.includes('空载归零')")
                source.status = "live"
                source.frames += 1
                page.wait_for_function("surfaceView.target === 1 && surfaceView.shearTarget > 0")
                page.route("**/api/state", lambda route: route.fulfill(status=503))
                page.get_by_text("页面与采集服务断开").wait_for()
                self.assertEqual(page.evaluate("[surfaceView.target, surfaceView.level, surfaceView.shearTarget, surfaceView.shearLevel]"), [0, 0, 0, 0])
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_missing_profile_disables_shear_and_labels_it(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(FakeSource()))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(reduced_motion="reduce")
                page.route("**/shear_profile.json", lambda route: route.fulfill(status=404))
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.evaluate("surfaceView.set([200,200,200,200,-200,-200,-200,-200,0,0,0,0])")
                self.assertEqual(page.evaluate("surfaceView.shearTarget"), 0)
                self.assertIn("剪切方向未验证", page.locator(".surface-label").inner_text())
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_score_helpers_reject_wrong_profile_version(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(FakeSource()))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                levels = page.evaluate("""() => {
                    const profile = {
                        version: 2, normal: {threshold: 100, span: 600},
                        shear: {enabled: true, weights: [1,1,1,1,-1,-1,-1,-1],
                                pressLeak: Array(8).fill(0), threshold: 20, span: 80}
                    };
                    return [normalLevel(Array(12).fill(700), profile),
                            shearLevel([100,100,100,100,-100,-100,-100,-100,
                                        0,0,0,0], profile)];
                }""")
                self.assertEqual(levels, [0, 0])
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_invalid_profile_uses_press_only_fallback(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(FakeSource()))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(reduced_motion="reduce")
                invalid = {
                    "version": 1, "assemblyId": "synthetic-test-only",
                    "normal": {"threshold": 1, "span": 1},
                    "shear": {"enabled": True, "weights": [1] * 7,
                              "pressLeak": [0] * 8, "threshold": 1, "span": 1},
                    "rightLabel": "right", "leftLabel": "left",
                    "evidence": ["synthetic.json"],
                }
                page.route("**/shear_profile.json", lambda route: route.fulfill(
                    status=200, content_type="application/json", body=json.dumps(invalid)))
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.wait_for_function("shearProfile.shear.enabled === false")
                page.evaluate("surfaceView.set([200,200,200,200,-200,-200,-200,-200,400,400,400,400], shearProfile)")
                self.assertEqual(page.evaluate("[surfaceView.target, surfaceView.shearTarget]"), [0.5, 0])
                self.assertIn("剪切方向未验证", page.locator(".surface-label").inner_text())
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_stalled_state_request_clears_surface_and_recovers(self):
        class ChangingSource(FakeSource):
            frames = 100

            def snapshot(self):
                state = super().snapshot()
                state.update(channels=[700.0] * 12, frames=self.frames,
                             invalid_recent=0)
                return state

        source = ChangingSource()
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(source))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(reduced_motion="reduce")
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.wait_for_function("surfaceView.target === 1 && surfaceView.level === 1")
                page.evaluate("""() => {
                    window.originalStateFetch = window.fetch;
                    window.fetch = (input, options) => input === '/api/state' ?
                        new Promise(() => {}) : window.originalStateFetch(input, options);
                }""")
                page.wait_for_function("fetching && surfaceView.target === 1")
                page.wait_for_function("surfaceView.target === 0 && surfaceView.level === 0",
                                       timeout=700)
                self.assertEqual(page.locator("#status-label").inner_text(), "数据正常")
                page.get_by_text("页面与采集服务断开").wait_for(timeout=3000)
                self.assertEqual(page.evaluate("[surfaceView.target, surfaceView.level]"), [0, 0])
                self.assertEqual(page.locator(".channel-card strong").first.inner_text(), "—")
                page.evaluate("() => { window.fetch = window.originalStateFetch; }")
                source.frames += 1
                page.wait_for_function(
                    "surfaceView.target === 1 && surfaceView.level === 1 && "
                    "document.querySelector('#status-label').textContent === '数据正常'")
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_tare_discards_inflight_live_response_until_taring_cycle(self):
        class ChangingSource(FakeSource):
            frames = 100
            status = "live"

            def snapshot(self):
                state = super().snapshot()
                state.update(channels=[400.0] * 12, frames=self.frames,
                             status=self.status, invalid_recent=0)
                return state

            def request_tare(self):
                self.status = "taring"

        source = ChangingSource()
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(source))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(reduced_motion="reduce")
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.wait_for_function("surfaceView.target === 0.5")
                page.evaluate("""() => {
                    window.realFetch = window.fetch;
                    window.holdPolls = true;
                    window.heldPoll = null;
                    window.fetch = (input, options) => {
                        if (input !== '/api/state') return realFetch(input, options);
                        return new Promise(resolve => {
                            if (!heldPoll) heldPoll = resolve;
                        });
                    };
                }""")
                page.wait_for_function("fetching && typeof heldPoll === 'function'")
                page.locator("#tare").click()
                self.assertEqual(page.evaluate("[surfaceView.target, surfaceView.level]"), [0, 0])
                page.evaluate("""() => heldPoll(new Response(JSON.stringify({
                    mode: 'live', status: 'live', message: 'old frame', port: 'COM10',
                    axes: Array(6).fill(0), channels: Array(12).fill(700),
                    rate: 200, frames: 101, invalid_recent: 0, saturated_recent: 0,
                    invalid_frames: 0, tare_progress: 100, resyncs: 0
                }), {status: 200, headers: {'Content-Type': 'application/json'}}))""")
                page.wait_for_timeout(100)
                self.assertEqual(page.evaluate("[surfaceView.target, surfaceView.level]"), [0, 0])
                self.assertEqual(page.evaluate("latestFrame"), 100)
                page.evaluate("window.fetch = window.realFetch")
                page.wait_for_function("document.querySelector('#status-label').textContent.includes('空载归零')")
                source.status = "live"
                page.wait_for_timeout(150)
                self.assertEqual(page.evaluate("[surfaceView.target, surfaceView.level]"), [0, 0])
                source.frames = 102
                page.wait_for_function("surfaceView.target === 0.5")
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_switching_to_reduced_motion_finishes_current_animation(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(FakeSource()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(reduced_motion="no-preference")
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.evaluate("""() => {
                    window.motionSurface = createSurface(document.getElementById('surface-canvas'));
                    motionSurface.set(Array(12).fill(700));
                }""")
                page.wait_for_function("motionSurface.level > 0 && motionSurface.level < 1")
                page.evaluate("""() => {
                    window.motionChanged = false;
                    matchMedia('(prefers-reduced-motion: reduce)').addEventListener(
                        'change', () => { window.motionChanged = true; }, { once: true });
                }""")
                page.emulate_media(reduced_motion="reduce")
                page.wait_for_function("window.motionChanged")
                self.assertEqual(page.evaluate("motionSurface.level"), 1)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_surface_animates_on_live_press_and_release(self):
        class ChangingSource(FakeSource):
            channels = [0.0] * 12
            frames = 100

            def snapshot(self):
                state = super().snapshot()
                state.update(channels=self.channels, frames=self.frames,
                             invalid_recent=0)
                return state

        source = ChangingSource()
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(source))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        evidence = Path(__file__).resolve().parents[1] / ".superpowers" / "sdd"
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 900},
                                        reduced_motion="no-preference")
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.wait_for_function("surfaceView.target === 0 && surfaceView.level === 0")
                self.assertFalse(page.evaluate(
                    "matchMedia('(prefers-reduced-motion: reduce)').matches"))

                source.channels = [700.0] * 12
                source.frames += 1
                page.wait_for_function(
                    "surfaceView.target === 1 && surfaceView.level > 0 && surfaceView.level < 1")
                page.wait_for_function("surfaceView.level > 0.99")
                self.assertEqual(page.locator("#status-label").inner_text(), "数据正常")
                page.locator("#surface-canvas").screenshot(
                    path=str(evidence / "task-3-normal-motion-grid-loaded.png"))

                source.channels = [0.0] * 12
                source.frames += 1
                page.wait_for_function(
                    "surfaceView.target === 0 && surfaceView.level > 0 && surfaceView.level < 1")
                page.wait_for_function("surfaceView.level === 0")
                self.assertEqual(page.locator("#status-label").inner_text(), "数据正常")
                self.assertEqual(page.locator(".channel-card strong").first.inner_text(), "+0")
                page.locator("#surface-canvas").screenshot(
                    path=str(evidence / "task-3-normal-motion-grid-released.png"))
                page.screenshot(path=str(evidence / "task-3-normal-motion-released.png"),
                                full_page=True)
                self.assertEqual(errors, [])
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_surface_visual_states_at_desktop_and_mobile_sizes(self):
        class ChangingSource(FakeSource):
            channels = [0.0] * 12
            frames = 100
            status = "live"

            def snapshot(self):
                state = super().snapshot()
                state.update(channels=self.channels, frames=self.frames,
                             status=self.status, invalid_recent=0)
                return state

            def request_tare(self):
                self.status = "taring"

        source = ChangingSource()
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(source))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        evidence = Path(__file__).resolve().parents[1] / ".superpowers" / "sdd"
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                for name, width, height in (("desktop", 1440, 900),
                                            ("mobile", 390, 844)):
                    source.channels = [0.0] * 12
                    source.frames += 1
                    source.status = "live"
                    page = browser.new_page(viewport={"width": width, "height": height},
                                            reduced_motion="reduce")
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(f"http://127.0.0.1:{server.server_port}/")
                    page.wait_for_function("surfaceView.target === 0 && surfaceView.level === 0")
                    self.assertEqual(page.locator("#force-chart, #torque-chart").count(), 2)
                    self.assertEqual(page.locator(".axis-row").count(), 6)
                    self.assertEqual(page.locator(".channel-card").count(), 12)
                    self.assertTrue(page.locator("#surface-canvas").is_visible())
                    self.assertTrue(page.locator(".orb-caption").is_visible())
                    self.assertFalse(page.evaluate(
                        "document.documentElement.scrollWidth > innerWidth"))
                    page.screenshot(path=str(evidence / f"task-3-{name}-unloaded.png"),
                                    full_page=True)
                    page.locator("#surface-canvas").screenshot(
                        path=str(evidence / f"task-3-{name}-grid-unloaded.png"))
                    source.channels = [700.0] * 12
                    source.frames += 1
                    page.wait_for_function("surfaceView.target === 1 && surfaceView.level === 1")
                    self.assertEqual(page.locator(".channel-card strong").first.inner_text(),
                                     "+700")
                    self.assertFalse(page.evaluate(
                        "document.documentElement.scrollWidth > innerWidth"))
                    canvas_width = page.evaluate(
                        "document.getElementById('surface-canvas').width")
                    page.set_viewport_size({"width": width - 20, "height": height})
                    page.wait_for_function(
                        "old => document.getElementById('surface-canvas').width !== old",
                        arg=canvas_width)
                    page.set_viewport_size({"width": width, "height": height})
                    page.wait_for_function(
                        "old => document.getElementById('surface-canvas').width === old",
                        arg=canvas_width)
                    self.assertEqual(page.evaluate("surfaceView.level"), 1)
                    page.screenshot(path=str(evidence / f"task-3-{name}-loaded.png"),
                                    full_page=True)
                    page.locator("#surface-canvas").screenshot(
                        path=str(evidence / f"task-3-{name}-grid-loaded.png"))
                    page.locator("#tare").click()
                    page.wait_for_function(
                        "document.querySelector('#status-label').textContent.includes('空载归零') && "
                        "surfaceView.target === 0 && surfaceView.level === 0")
                    self.assertEqual(page.locator(".channel-card strong").first.inner_text(),
                                     "—")
                    self.assertFalse(page.evaluate(
                        "document.documentElement.scrollWidth > innerWidth"))
                    page.screenshot(path=str(evidence / f"task-3-{name}-cleared.png"),
                                    full_page=True)
                    page.locator("#surface-canvas").screenshot(
                        path=str(evidence / f"task-3-{name}-grid-cleared.png"))
                    self.assertEqual(errors, [])
                    page.close()
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_surface_fits_mobile_and_reduced_motion(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(FakeSource()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 390, "height": 844},
                                        reduced_motion="reduce")
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.evaluate("surfaceView.set(Array(12).fill(700))")
                self.assertEqual(page.evaluate("surfaceView.level"), 1)
                self.assertFalse(page.evaluate(
                    "document.documentElement.scrollWidth > innerWidth"))
                self.assertEqual(errors, [])
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_surface_follows_new_frame_and_clears_on_disconnect(self):
        class ChangingSource(FakeSource):
            channels = [0.0] * 12
            frames = 100

            def snapshot(self):
                state = super().snapshot()
                state.update(channels=self.channels, frames=self.frames, invalid_recent=0)
                return state

        source = ChangingSource()
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(source))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.wait_for_function("surfaceView.target === 0")
                source.channels = [400.0] * 12
                source.frames += 1
                page.wait_for_function("surfaceView.target === 0.5")
                self.assertEqual(page.locator(".channel-card strong").first.inner_text(), "+400")
                source.channels = [0.0] * 12
                source.frames += 1
                page.wait_for_function("surfaceView.target === 0")
                source.channels = [700.0] * 12
                source.frames += 1
                page.wait_for_function("surfaceView.target === 1")
                page.route("**/api/state", lambda route: route.fulfill(status=503))
                page.get_by_text("页面与采集服务断开").wait_for()
                self.assertEqual(page.evaluate("[surfaceView.target, surfaceView.level]"), [0, 0])
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_surface_uses_robust_counts_and_is_labeled_illustration(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(FakeSource()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                self.assertEqual(page.locator("#surface-canvas").count(), 1)
                self.assertIn("正压／剪切响应示意", page.locator(".surface-label").inner_text())
                values = page.evaluate("""() => [
                    surfaceLevel(Array(12).fill(0)),
                    surfaceLevel(Array(12).fill(99)),
                    surfaceLevel(Array(12).fill(400)),
                    surfaceLevel(Array(12).fill(700)),
                    surfaceLevel([9000, ...Array(11).fill(0)]),
                    surfaceLevel(Array(12).fill(-400)),
                    surfaceLevel([-100, 100, -200, 200, -300, 300,
                                  -500, 500, -700, 700, -900, 900])
                ]""")
                self.assertEqual(values, [0, 0, 0.5, 1, 0, 0.5, 0.5])
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_flat_surface_grid_does_not_touch_canvas_edges(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(FakeSource()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                edge_ink = page.evaluate("""() => {
                    const canvas = document.getElementById("surface-canvas");
                    createSurface(canvas);
                    const ctx = canvas.getContext("2d");
                    const left = ctx.getImageData(0, 0, 1, canvas.height).data;
                    const right = ctx.getImageData(canvas.width - 1, 0, 1, canvas.height).data;
                    return [left, right].map(column =>
                        Array.from(column).filter((_, i) => i % 4 === 3 && column[i] > 0).length);
                }""")
                self.assertEqual(edge_ink, [0, 0])
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_force_chart_uses_three_times_wider_display_scale_only(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(FakeSource()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                force, torque, activity = page.evaluate("""() => [
                    chartResponse(0.12, 0),
                    chartResponse(0.0004, 3),
                    response(0.12, 0)
                ]""")
                gain = page.evaluate("gain")
                self.assertAlmostEqual(force, math.tanh(gain / 3))
                self.assertAlmostEqual(torque, math.tanh(gain))
                self.assertAlmostEqual(activity, math.tanh(gain))
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_invalid_frames_are_visible_as_an_error(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(FakeSource()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.wait_for_timeout(200)
                self.assertEqual(page.locator("#status-label").inner_text(), "原始帧异常")
                self.assertIn("异常帧 3", page.locator("#foot-status").inner_text())
                self.assertIn("累计异常 3", page.locator("#foot-status").inner_text())
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_disconnected_service_clears_stale_readings(self):
        class NonzeroSource(FakeSource):
            def snapshot(self):
                state = super().snapshot()
                state.update(axes=[0.1] * 6, channels=[100.0] * 12,
                             invalid_recent=0)
                return state

        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(NonzeroSource()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.locator(".axis-value").first.wait_for(state="visible")
                page.wait_for_function("document.querySelector('.axis-value').textContent !== '+0.00'")
                page.route("**/api/state", lambda route: route.fulfill(status=503))
                page.get_by_text("页面与采集服务断开").wait_for()
                self.assertEqual(page.locator(".axis-value").first.inner_text(), "—")
                self.assertEqual(page.locator(".channel-card strong").first.inner_text(), "—")
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_response_groups_do_not_replace_historical_trends(self):
        class GroupSource(FakeSource):
            def snapshot(self):
                state = super().snapshot()
                state.update(axes=[0.1, 0.2, 0.3, 0.001, 0.002, 0.003],
                             channels=[100, 300, 200, 400, 300, 500,
                                       400, 600, 500, 700, 600, 800],
                             invalid_recent=0)
                return state

        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(GroupSource()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.wait_for_function("document.querySelector('.axis-value').textContent.includes('200')")
                self.assertEqual(page.locator(".axis-label").all_inner_texts(),
                                 ["G1\nCH1–2", "G2\nCH3–4", "G3\nCH5–6",
                                  "G4\nCH7–8", "G5\nCH9–10", "G6\nCH11–12"])
                self.assertEqual(page.locator(".axis-value").all_inner_texts(),
                                 ["200", "300", "400", "500", "600", "700"])
                self.assertIn("Fx · Fy · Fz", page.locator(".trend-title").first.inner_text())
                self.assertEqual(page.evaluate("histories[0].at(-1)"), 0.1)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_one_group_spike_does_not_change_five_poll_median(self):
        class SpikeSource(FakeSource):
            def __init__(self):
                self.calls = 0

            def snapshot(self):
                self.calls += 1
                state = super().snapshot()
                value = 30000 if self.calls == 6 else 100
                state.update(frames=100 + self.calls,
                             channels=[value] * 12, invalid_recent=0)
                return state

        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(SpikeSource()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.wait_for_function("document.querySelector('#rate-label').textContent.includes('106 帧')")
                self.assertEqual(page.locator(".axis-value").first.inner_text(), "100")
                browser.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_channel_bars_are_linear_and_show_overflow(self):
        class ScaleSource(FakeSource):
            def snapshot(self):
                state = super().snapshot()
                state.update(channels=[500, 1000, 1500, -500, -1500] + [0] * 7,
                             invalid_recent=0)
                return state

        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(ScaleSource()))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{server.server_port}/")
                page.wait_for_function("document.querySelector('.channel-card strong').textContent === '+500'")
                cards = page.locator(".channel-card")
                self.assertEqual(cards.nth(0).locator(".mini-fill").get_attribute("style"),
                                 "left: 50%; width: 25%;")
                self.assertEqual(cards.nth(1).locator(".mini-fill").get_attribute("style"),
                                 "left: 50%; width: 50%;")
                self.assertEqual(cards.nth(2).locator(".mini-fill").get_attribute("style"),
                                 "left: 50%; width: 50%;")
                self.assertEqual(cards.nth(3).locator(".mini-fill").get_attribute("style"),
                                 "left: 25%; width: 25%;")
                self.assertEqual(cards.nth(4).locator(".mini-fill").get_attribute("style"),
                                 "left: 0%; width: 50%;")
                self.assertEqual(cards.nth(2).locator("strong").inner_text(), "+1500")
                self.assertEqual(cards.nth(4).locator("strong").inner_text(), "-1500")
                self.assertEqual([cards.nth(i).get_attribute("class").endswith("over-range")
                                  for i in range(5)], [False, False, True, False, True])
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
