# CoinFT Signal Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This directory is not a Git repository, so commit steps are unavailable.

**Goal:** Preserve the existing Fx–Mz trend charts and make the right-hand response cards and 12-channel bars readable without implying new six-axis calibration.

**Architecture:** Keep `coinft_demo.py` and its `/api/state` contract unchanged. Derive six non-directional group intensities from the 12 channel deltas in `demo_web/app.js`; render these only in the right-hand cards. Keep all six historical `data.axes` values and their two canvas charts untouched. Use browser tests against the existing fake HTTP source.

**Tech Stack:** Python `unittest`, Playwright Chromium, vanilla JavaScript/CSS, Windows PowerShell.

## Global Constraints

- Do not change the two existing trend charts' layout, labels, data source, or gain-slider behavior.
- G1–G6 pair CH1–2, CH3–4, CH5–6, CH7–8, CH9–10, CH11–12, each as the mean of the two absolute baseline-relative counts.
- Display group intensities with a five-poll (~0.25 s) rolling median and a fixed 0–1000-count linear bar.
- Display all 12 baseline-relative counts numerically without smoothing and with fixed linear ±1000-count bars; retain the full numeric value beyond the bar's range and mark overflow.
- Keep serial protocol, tuning, firmware, backend tare and invalid-frame handling unchanged.

---

### Task 1: Six response cards while preserving historical charts

**Files:** Modify `demo_web/app.js`, `demo_web/index.html`; test `tests/test_demo_ui.py`.

**Interfaces:** Read `data.axes: number[6]`, `data.channels: number[12]` from `/api/state`. Produce G1–G6 card values only; send `data.axes` unchanged to `histories`, `drawChart`, and orb activity.

- [x] Write a Playwright test with a fake snapshot containing six distinct axis values and channel deltas `[100,300, 200,400, 300,500, 400,600, 500,700, 600,800]`. Assert right-hand labels G1–G6, first group reads `200`, second `300`, and existing force/torque chart labels and axis histories still consume `data.axes`. Run `python -m unittest discover -s tests -p test_demo_ui.py -v` and confirm the new test fails because G1 is absent.
- [x] Add `groupResponses(channels)` returning six `(abs(channels[2*i])+abs(channels[2*i+1]))/2` values and `median(values)` using a sorted copy. Maintain six arrays of at most five poll values; reset them in `clearDisplay()` and tare. Render their medians as G1–G6 in right cards, with `min(value / 1000, 1) * 100` percent bar width from the left edge. Do not change `response()`, `histories`, or either `drawChart` call.
- [x] Update only the right-hand panel heading/unit/row labels and the existing notice outside the charts to distinguish G1–G6 from the historical uncalibrated Fx–Mz projection. Keep the gain slider and left panels intact.
- [x] Run the targeted test and the full suite, expecting exit code 0. Confirm `page.evaluate('histories[0].at(-1)')` equals the fake `data.axes[0]`, not a group value.

### Task 2: Linear 12-channel bars and visible overflow

**Files:** Modify `demo_web/app.js`, `demo_web/style.css`, `DEMO_README.md`; test `tests/test_demo_ui.py`.

**Interfaces:** Input `data.channels: number[12]`; output each card's full rounded count, capped bar position/width, and an `over-range` CSS class when `abs(value) > 1000`.

- [x] Add a Playwright test feeding channel values `500`, `1000`, `1500`, `-500`, and `-1500`. Assert the +500 bar uses half the positive half-rail, +1000 and +1500 share the capped rail length, -500 mirrors +500, +1500/-1500 text remains untruncated, and only the two ±1500 cards have `over-range`. Run the targeted test and confirm it fails against the current `tanh(value / 90 * gain)` mapping.
- [x] Replace only the channel-bar mapping with `signed = Math.max(-1, Math.min(1, value / 1000))`, `left = 50 + Math.min(0, signed) * 50`, `width = Math.abs(signed) * 50`; toggle `over-range` when `Math.abs(value) > 1000` and style that class visibly. Keep the numeric `Math.round(value)` output and exclude the gain slider from channel mapping.
- [x] Document the linear ±1000-count view, group mapping, unchanged historical trend meaning, and overflow in `DEMO_README.md`. Run targeted and full suites, `python -m py_compile coinft_demo.py`, and a Playwright screenshot at 1440 px. Inspect the screenshot for clipping and label clarity.
- [x] Update `PROJECT_LOG.md` with test evidence and the remaining hardware data-integrity caveat. Do not claim six-axis accuracy or permanent background-service startup.
