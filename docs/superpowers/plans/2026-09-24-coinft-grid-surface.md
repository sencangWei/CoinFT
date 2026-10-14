# CoinFT Grid Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dashboard's glowing orb with a live, perspective-grid indentation illustration while preserving every existing trend and channel readout.

**Architecture:** A small, independent Canvas renderer consumes only the existing 12 relative-baseline channel counts. `app.js` forwards fresh live frames and clears the renderer on tare, waiting, error, or fetch failure; no backend or firmware change.

**Tech Stack:** Vanilla HTML/CSS/JavaScript, Canvas 2D, Python `unittest`, Playwright Chromium.

## Global Constraints

- Follow `docs/superpowers/specs/2026-09-24-coinft-grid-surface-design.md`.
- Only `/api/state` `channels` drives the surface: `median(abs(CH1..CH12))`, 0 below 100 counts, 1 at or above 700 counts, linear between.
- Fixed center; label it “响应形变示意”; never imply real contact localization, measured shape, calibrated N, or N·m.
- Preserve the current force/torque charts, display sensitivity, activity index, G1–G6, and 12 raw channel numbers and scales.
- No Stanford assets/code, online dependency, serial, firmware, calibration, or API edits.
- Preserve unrelated user edits. This directory is not a Git repository; omit commit steps unless repository state changes.

---

### Task 1: Independently rendered gridded indentation

**Files:**
- Create: `demo_web/surface.js`
- Modify: `demo_web/index.html` (the `.orb-wrap` child elements and script tags)
- Modify: `demo_web/style.css` (only the orb-specific styles and a surface-canvas override)
- Modify: `demo_web/app.js` (remove only the two references to the deleted `#sensor-orb`, so the current dashboard stays functional before Task 2)
- Test: `tests/test_demo_ui.py`

**Interfaces:**
- Consumes: `channels: number[12]`, the existing `median(values)` logic is duplicated locally because this renderer must be loadable before `app.js`.
- Produces: `surfaceLevel(channels): number` in `[0,1]`; `createSurface(canvas): {target:number, level:number, set(channels):void, clear():void, resize():void}`.

- [ ] **Step 1: Add a failing browser test for scale, semantic label, and Canvas.** Append to `DashboardWarningTests` in `tests/test_demo_ui.py`:

```python
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
                self.assertIn("响应形变示意", page.locator(".surface-label").inner_text())
                values = page.evaluate("""() => [
                    surfaceLevel(Array(12).fill(0)),
                    surfaceLevel(Array(12).fill(99)),
                    surfaceLevel(Array(12).fill(400)),
                    surfaceLevel(Array(12).fill(700)),
                    surfaceLevel([9000, ...Array(11).fill(0)])
                ]""")
                self.assertEqual(values, [0, 0, 0.5, 1, 0])
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
```

- [ ] **Step 2: Verify red.** Run from `D:\semg.claude\coinft`: `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_surface_uses_robust_counts_and_is_labeled_illustration -v`. Expected: FAIL because `#surface-canvas` is absent.

- [ ] **Step 3: Replace only the left-panel orb markup.** In `demo_web/index.html`, replace the current `.orb-wrap` inner children (three `.orbit`, `.sensor-orb`, three `.axis-tag`, `.orb-caption`) with:

```html
<canvas id="surface-canvas" aria-label="CoinFT 十二路电容响应驱动的中央凹陷网格示意；不代表实际接触位置或标定力值">响应形变示意</canvas>
<div class="orb-caption"><span class="surface-label">响应形变示意</span><strong id="activity-value">0<span>%</span></strong><small>画面活动指数 · 非实际力值</small></div>
```

Add `<script src="/surface.js"></script>` immediately before the existing `<script src="/app.js"></script>`.

- [ ] **Step 4: Replace only orb-specific CSS.** Delete `.orbit`, `.orbit-b`, `.orbit-c`, `.sensor-orb`, `.orb-core`, `.core-ring`, `.core-ring.inner`, `.core-center`, `.axis-tag`, `.x-tag`, `.y-tag`, `.z-tag` declarations. Keep `.orb-wrap` and `.orb-caption` declarations. Append:

```css
#surface-canvas{position:absolute;inset:0;width:100%;height:100%;margin:0}
.surface-label{color:#dceea3!important;letter-spacing:.14em!important}
```

Use `apply_patch` with exact original substrings; do not reformat the minified stylesheet or alter charts/channel CSS.

- [ ] **Step 5: Create the full Canvas module `demo_web/surface.js`.**

```javascript
function surfaceLevel(channels) {
  if (!Array.isArray(channels) || channels.length !== 12 ||
      channels.some(value => !Number.isFinite(value))) return 0;
  const values = channels.map(Math.abs).sort((a, b) => a - b);
  const median = (values[5] + values[6]) / 2;
  return Math.max(0, Math.min(1, (median - 100) / 600));
}

function createSurface(canvas) {
  const surface = { target: 0, level: 0, set, clear, resize };
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  let frame = 0;

  function resize() {
    const bounds = canvas.getBoundingClientRect();
    if (!bounds.width || !bounds.height) return;
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.round(bounds.width * ratio);
    canvas.height = Math.round(bounds.height * ratio);
    draw();
  }

  function draw() {
    const bounds = canvas.getBoundingClientRect();
    const w = bounds.width, h = bounds.height;
    if (!w || !h) return;
    const ctx = canvas.getContext("2d");
    ctx.setTransform(canvas.width / w, 0, 0, canvas.height / h, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const steps = 18;
    function point(i, j) {
      const u = i / steps * 2 - 1;
      const v = j / steps * 2 - 1;
      const bump = Math.exp(-(u * u + v * v) / 0.18);
      return [w * (0.5 + (u - v) * 0.34),
              h * (0.34 + (u + v) * 0.105 + bump * surface.level * 0.17), bump];
    }
    for (let j = 0; j < steps; j++) {
      for (let i = 0; i < steps; i++) {
        const a = point(i, j), b = point(i + 1, j);
        const c = point(i + 1, j + 1), d = point(i, j + 1);
        const intensity = (a[2] + b[2] + c[2] + d[2]) * surface.level / 4;
        ctx.beginPath();
        ctx.moveTo(a[0], a[1]);
        ctx.lineTo(b[0], b[1]);
        ctx.lineTo(c[0], c[1]);
        ctx.lineTo(d[0], d[1]);
        ctx.closePath();
        ctx.fillStyle = `rgba(57,211,194,${0.04 + intensity * 0.55})`;
        ctx.fill();
        ctx.strokeStyle = intensity > 0.08 ? `rgba(99,238,211,${0.45 + intensity * 0.4})` : "#a6c6629c";
        ctx.lineWidth = 0.8;
        ctx.stroke();
      }
    }
  }

  function animate() {
    frame = 0;
    surface.level += (surface.target - surface.level) * 0.2;
    if (Math.abs(surface.target - surface.level) < 0.003) surface.level = surface.target;
    draw();
    if (surface.level !== surface.target) frame = requestAnimationFrame(animate);
  }

  function set(channels) {
    surface.target = surfaceLevel(channels);
    if (reduced.matches) {
      cancelAnimationFrame(frame);
      frame = 0;
      surface.level = surface.target;
      draw();
    } else if (!frame) frame = requestAnimationFrame(animate);
  }

  function clear() {
    cancelAnimationFrame(frame);
    frame = 0;
    surface.target = 0;
    surface.level = 0;
    draw();
  }

  resize();
  return surface;
}
```

- [ ] **Step 6: Verify green.** Run the same focused unittest. Expected: PASS. Visually inspect a flat grid before linking live data; the caption must remain readable.

- [ ] **Step 7: Keep the intermediate dashboard functional.** Remove only the two `document.getElementById("sensor-orb")...` style assignments at the end of `paintBars` in `demo_web/app.js`, then run `D:\conda\python.exe -m unittest discover -s tests -v`. Expected: all existing and Task-1 tests PASS; the new Canvas is wired to live data in Task 2.

### Task 2: Wire live lifecycle without changing existing readouts

**Files:**
- Modify: `demo_web/app.js`
- Test: `tests/test_demo_ui.py`

**Interfaces:**
- Consumes: `createSurface(canvas)` and its `set`, `clear`, `resize` from Task 1.
- Produces: top-level `surfaceView` for browser diagnostics; a fresh live frame updates its `target`; stale/nonlive states clear it.

- [ ] **Step 1: Add a failing lifecycle browser test.** Append to `DashboardWarningTests`:

```python
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
```

- [ ] **Step 2: Verify red.** Run `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_surface_follows_new_frame_and_clears_on_disconnect -v` from `D:\semg.claude\coinft`. Expected: FAIL because `surfaceView` is undefined.

- [ ] **Step 3: Make the minimal `app.js` integration.** Add after `torqueCanvas`:

```javascript
const surfaceView = createSurface(document.getElementById("surface-canvas"));
```

The two `#sensor-orb` assignments were already removed in Task 1. Add `surfaceView.clear();` at the beginning of `clearDisplay()`. In the fresh-live-frame block of `poll()`, after `lastChannels = data.channels;`, add `surfaceView.set(data.channels);`. In the tare click handler, call `surfaceView.clear();` before the POST; after the existing history/window clears, preserve all other behavior. Extend the existing resize listener as follows:

```javascript
window.addEventListener("resize", () => {
  surfaceView.resize();
  drawChart(forceCanvas, 0);
  drawChart(torqueCanvas, 3);
});
```

- [ ] **Step 4: Verify green and regressions.** Run `D:\conda\python.exe -m unittest discover -s tests -v` from `D:\semg.claude\coinft`. Expected: all existing and new tests PASS. Verify `force-chart`, `torque-chart`, G1–G6, gain slider, activity index, and 12 channel readings retain their previous behavior.

### Task 3: Browser visual and motion acceptance

**Files:**
- Test: `tests/test_demo_ui.py`
- Modify only if a test exposes a defect: `demo_web/surface.js`, `demo_web/style.css`, or `demo_web/app.js`
- Update: `PROJECT_LOG.md` after verification

**Interfaces:**
- Consumes: `surfaceView` and the visible dashboard from Tasks 1–2.
- Produces: screenshot and browser-console evidence for desktop/mobile and reduced-motion operation.

- [ ] **Step 1: Add a responsive and reduced-motion browser test.** Append to `DashboardWarningTests`:

```python
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
```

- [ ] **Step 2: Run focused test red/green.** Run `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_surface_fits_mobile_and_reduced_motion -v`. Expected: PASS if Tasks 1–2 already meet the spec; if FAIL, adjust only the demonstrated CSS/Canvas defect and rerun.

- [ ] **Step 3: Inspect visual states.** In Playwright Chromium at 1440×900 and 390×844, capture 0-count and 700-count Canvas/page screenshots, then compare: visible planar yellow-green grid when unloaded, central cyan-green indentation when loaded, readable caption, no clipping, no overlap or horizontal scroll. Use existing local test server or the installed `--replay` mode; never alter live hardware just to take screenshots.

- [ ] **Step 4: Final verification and handoff.** Run `D:\conda\python.exe -m unittest discover -s tests -v`; expected: all PASS, no browser `pageerror`. Update `PROJECT_LOG.md` with exact implementation, tests, screenshots and any unverified live-hardware behavior. Do not claim live serial acceptance without observing a real live session.

## Self-review

- Spec coverage: Task 1 covers perspective surface, threshold mapping, fixed center, semantic label, CSS and no dependencies; Task 2 covers fresh frames and nonlive/tare/disconnect reset without changing other readouts; Task 3 covers mobile, reduced motion, visual QA, regression evidence and honest live-hardware status.
- The reference video is a visual cue only. The rendered indentation is not physical shape reconstruction.
- Task interfaces use the same `surfaceLevel`, `createSurface`, and `surfaceView` names throughout.
