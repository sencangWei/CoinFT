# Task 3 — qualitative live smoke test

Status: preflight passed on 2026-09-25; operator-guided poses and live acceptance remain pending.

## Read-only preflight

- `demo_web/shear_demo_profile.json` has `mode: "qualitative"`, `shear.enabled: true`, `rightLabel: "−X"` (U+2212, X), and `leftLabel: "+X"`. Its eight evidence basenames match the eight named sources in `calibration/build_qualitative_demo_profile.py` in order. All 16 shear weights and press-leak coefficients are finite.
- Shear threshold is `99.11124275398228`, above the recorded empty/press projection p95 of about `94.3916597656974` (`threshold = 1.05 × p95` in the profile builder). The generated profile's normal threshold/span are `100/600`; shear span is `128.5109264230957`.
- `demo_web/shear_profile.json` does not exist. In `demo_web/app.js`, the qualitative profile loads only when the strict profile request returns HTTP 404; a present strict profile takes precedence, including when its shear flag is disabled.
- Two read-only `GET /api/state` samples about 0.5 s apart returned `mode=status=live`, `port=COM10`, `rate=200.0`, frames `5678679 → 5678788` (+109), `invalid_recent=0`, and `saturated_recent=0`. Cumulative counters were `invalid_frames=110` and `saturated=3`; those historical counts did not change between samples. No service or device command was sent.

Preflight stop condition was not met. This verifies readiness for the operator-guided smoke sequence only. No visual zero or live pose was captured, so center indentation, ±X screen direction, release behavior, and raw/trend continuity have not yet been accepted. No force calibration or independent validation is claimed.
