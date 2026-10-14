### Task 3: Live qualitative smoke test and safe handoff

**Files:** Update `PROJECT_LOG.md`; save non-overwriting evidence under `calibration/` or `.superpowers/sdd/` as needed.

**Interfaces:** Consumes Task 1's generated `demo_web/shear_demo_profile.json` and Task 2's browser UI. Does not alter firmware, backend, strict fitted profile, or historical evidence.

- [ ] **Step 1: Preflight.** Read the generated JSON: require `mode:"qualitative"`, `shear.enabled:true`, `rightLabel:"-X"`, `leftLabel:"+X"`, eight exact source basenames, finite coefficients, threshold above recorded empty/press p95. Confirm no strict profile exists or takes precedence. Query `/api/state` twice ~0.5 s apart; require `live`, increasing frames, positive rate, zero recent invalid/saturation. If not, stop.

- [ ] **Step 2: Operator-guided smoke test, one pose at a time.** Ask the operator to leave CoinFT empty, click “演示归零”, wait for ready status, and verify grid flat. After explicit confirmation, guide center press → release → −X push → release → +X push → release; never auto-advance. Record one browser screenshot or short video and raw state evidence per pose. Confirm center press indents without persistent shear, −X shifts screen-right, +X screen-left, and each release returns flat. Verify trends, G1–G6, 12 raw numbers still update without baseline subtraction.

- [ ] **Step 3: Stop safely on failure; document actual result.** If either sign is wrong, empty sticks, baseline is not reproducible, or USB/serial stalls, move the generated qualitative profile to a uniquely named archive inside `calibration/` after resolving/checking both paths, leaving no enabled demo profile; the app falls back to press-only. Do not edit numeric coefficients to force a pass. Add a dated `PROJECT_LOG.md` entry distinguishing synthetic tests, one-pose offline evidence and actual live outcome; explicitly state no independent validation or N/N·m calibration. If smoke passes, leave profile enabled but label it qualitative and require visual zero on every page open.

## Plan self-review targets

- Spec coverage: measured one-pose relative template, independent qualitative file, visual-only zero, no raw/trend changes, stale/tare reset, explicit warning, smoke stop rule.
- Non-Git environment: no commit/worktree commands; all archive operations must be recoverable and bounded to named calibration files.
- No partial claims: passing unit/browser tests or opposite offline medians alone never proves the live physical direction.
