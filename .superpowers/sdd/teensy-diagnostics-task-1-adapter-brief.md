# Task1 supplement — diagnostic-only non-waiting CDC2 transmit

User approved this scope on2026-09-28. This closes the Task1 SDK blocker; not a forwarding bug fix. Read this first and original task1 brief for unchanged counter/protocol requirements. You are not alone: root edits docs/ledger only, preserve all others' edits. No live COM, upload, service action, package installs or Git operations. Use apply_patch for source edits.

## Ownership

- C:/Users/winer/Desktop/CoinFT_Teensy_Interface/platformio.ini (diagnostic env only).
- Create firmware-project scripts/diag_usb_nonblocking.py (pure guarded SDK transform) and scripts/diag_usb_build.py (diagnostic-only PIO middleware).
- Create coinft/tests/test_teensy_diagnostic_usb_adapter.py and any native fixture required under tests/teensy_diag_fixture/ for actual SDK transmit functions.
- Existing task1 tests may change only for necessary compatibility; firmware cpp remains frozen unless a concrete adapter integration requirement arises.
- Append evidence to .superpowers/sdd/teensy-diagnostics-task-1-report.md. Root owns design/plan/log/review package.

## Binding implementation

Use a project-local PIO pre-script only in teensy40_diag. AddBuildMiddleware replaces only the actual cores/teensy4/usb_serial2.c source node with an adapted copy under that environment's build directory. Never write to installed SDK or compile a second duplicate of the core. Leave original env and usb_serial.c entirely unchanged. Preserve upstream copyright/license in generated copy. Include path to original core must remain valid. No silent fallback on unknown SDK.

Pure transform consumes source bytes and rejects wrong SHA256 or missing/ambiguous function anchors before producing output. Expected installed upstream SHA256: 575F5852165647E39F059548AE244A4B426A8BE31BFEF57CC4A9044FA8A37A3B. Framework1.162.0/Teensy1.62. Change only usb_serial2_write and usb_serial2_write_buffer_free; retain other source exactly. Legacy raw SDK usb_serial.c unchanged. Middleware may generate its copy as a normal build step, never manually edit SDK/build artifacts.

Diagnostic write is bounded all-or-nothing: configured, current head ready without error, and size fits current contiguous free space => copy exact bytes, keep existing DMA/cache/timer semantics, return size; otherwise return0 immediately. The heartbeat maximum is148 bytes in<=192 buffer. No yield, clock wait, polling loop or printf/flush in adapted write/capacity paths. Guard current tx_head, not aggregate other-head capacity. When current head has zero tx_available, one transfer status check detects busy0x80/errors0x68 before claiming TX_SIZE. Protect current head/buffer against CDC2 timer autoflush using tx_noautoflush, restore its prior value on every exit. Do not disable interrupts around diagnostic memcpy or change original ISR forwarding. Empty write returns0 without buffer modification. Exact full-buffer submission must advance/wrap head correctly; partial buffer retains original one-shot flush behavior. Skips must recover as soon as head becomes ready; no latched timeout.

Interfaces can remain internal/simple: one pure transform function callable by tests and build hook; no general-purpose patch framework. Do not remove unused original timeout declarations solely for cleanup. If actual SDK integration is uncertain, report NEEDS_CONTEXT with evidence rather than weaken no-wait requirement.

## TDD and validation

1. Read installed SDK source. Add a native harness that compiles the actual SDK write/capacity function text with only USB transfer/cache/timer/time external boundaries replaced. Baseline unadapted busy-head function should run to its existing timeout under fake clock; assertion that yield count==0 must fail. Do not duplicate algorithm in fixture or rely only on string inspection.
2. Implement guarded transform/middleware minimally. Exercise actual transformed functions: busy head with other free buffers skips immediately; no configuration; error status; insufficient current contiguous capacity accepts no partial prefix; ready write byte equality/return/timer; exact-full head advance/wrap; no yield/no printf; autoflush prior0/1 restored on success/failure; subsequent busy-to-ready recovery. Guard mismatch fails rather than outputs unpatched source. Assert untouched bytes outside the two function replacements and original SDK hashes.
3. Run focused native firmware and adapter tests. Build diagnostic only with --disable-auto-clean, verify verbose build evidence includes the generated SDK substitute. Rehash original backed-up/on-disk HEX+ELF and global SDK usb_serial2.c/usb_serial.c before/after. No original env rebuild.

Commands from coinft:

```powershell
& D:\conda\python.exe -m unittest discover -s tests -p test_teensy_diagnostic_usb_adapter.py -v
& D:\conda\python.exe -m unittest discover -s tests -p test_teensy_diagnostic_firmware.py -v
& C:\Users\winer\.platformio\penv\Scripts\pio.exe run --disable-auto-clean -d C:\Users\winer\Desktop\CoinFT_Teensy_Interface -e teensy40_diag -v
```

The first RED must predate production adapter changes; no live serial in tests. Report command/count/output and actual wait/skip evidence, target build source substitution evidence, changed files/hashes, limitations. Freeze after completion; broad review and hardware upload belong to root.
