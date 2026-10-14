### Spec Compliance

- ✅ Spec compliant within the Task1 source/build-integration gate. I1 is resolved in the frozen v2 package; no new implementation findings.
- ✅ `C:/Users/winer/Desktop/CoinFT_Teensy_Interface/scripts/diag_usb_nonblocking.py:24`, `:40`, `:61`: rejection, successful partial write, and capacity paths restore the prior autoflush flag, apply a compiler barrier, then rearm when a partial buffer remains. A timer expiry consumed while protected therefore receives a later retry. The success path no longer first arms its timer while protection is held.
- ✅ `scripts/diag_usb_nonblocking.py:32`: exact-full submission remains protected, advances/wraps the head, and stops its timer. No partial buffer remains to rearm. Empty/unconfigured paths still return without modifying buffer state. Prior flag 1 remains 1, respecting the existing caller's suppression; the normal diagnostic caller has prior 0.
- ✅ `scripts/diag_usb_nonblocking.py:43`: a callback between flag restoration and the rearm check either drains the buffer before the check or permits a harmless timer on an already-empty buffer. The repair neither copies into a submitted buffer nor introduces waiting, polling, yield, synchronous flush, logging, or an interrupt mask around memcpy.
- ✅ `teensy_coinft_serial_interface.cpp:59`, `:92`, `:123`, `:170`, `:215`: NUM_COINFTS, tuning, baud, boot delays, commands, UART consumption/framing, flag timing, timer interval and raw write order remain preserved. Counters and CFD1 output stay macro-gated; snapshot restores PRIMASK; diagnostics are main-loop-only and never consumed as sensor commands (`:3`, `:16`, `:20`).
- ✅ `platformio.ini:10`, `scripts/diag_usb_build.py:7`, `:17`, `:26`, `scripts/diag_usb_nonblocking.py:69`: only the diagnostic environment substitutes the current CDC2 source, guarded by exact SDK identity and unique anchors. The generated-core diff changes only the two allowed functions and retains license/unrelated source.

### Strengths

- `tests/test_teensy_diagnostic_usb_adapter.py:18`: the fixture now compiles the actual unchanged flush callback alongside the transformed functions, closing the previous coverage gap.
- `tests/teensy_diag_fixture/test_usb_adapter.cpp:17`, `:59`: expiry clears the simulated one-shot before dispatch; all three new cases verify actual submission and exact bytes without another successful append. Capacity/rejection cases exercise a pending 1948-byte buffer with insufficient space for the next line.
- `tests/teensy_diag_fixture/test_firmware.cpp:12`, `:34`: unchanged native firmware checks retain exact setup/protocol, failure-return, rollover and maximum-record coverage. The repair is limited to the adapter and its tests.

### Issues

#### Critical (Must Fix)

- None.

#### Important (Should Fix)

- None. Previous I1 is closed by the release-before-rearm ordering and actual-callback expiry regressions cited above.

#### Minor (Nice to Have)

- None identified in this task gate.

### Assessment

**Task quality:** Approved.

**Reasoning:** The fix addresses the timer-liveness failure on each affected exit while retaining bounded current-head writes, caller flag restoration, and diagnostic-only SDK isolation. The three reported RED cases correspond to meaningful assertions in the reviewed code; the reported eight-test GREEN and warning-free ARM build are consistent with the implementation.

**Cannot verify from this diff; root checks still required:**

- Original on-disk/backup HEX and ELF identity, untouched installed usb_serial.c/usb_serial2.c hashes, and the nine protected non-task invariants: retain or recheck the recorded pre/post hashes. Initial auto-clean deletion/restoration is historical and must not be represented as uninterrupted preservation.
- Executed RED-before-edit chronology, final eight-test adapter GREEN, nine-test firmware evidence, final warning-free target build with --disable-auto-clean, and single substituted archive member: retain execution logs or perform root's planned fresh validation. This review did not independently rerun them.
- Physical dual-CDC enumeration, real interrupt latency, eventual host delivery/backpressure behavior and sensor-stream behavior: establish only through separately authorized hardware acceptance. Native submission assertions establish submitted bytes, not PC delivery; the backup is not proof of the currently flashed image.
- Task2 observer behavior and the eventual broad integration review are outside this gate.

**Review checks:** Reviewed frozen v2 package and the appended I1 repair report; recovered only the tool-truncated fixture/test section. No production files were reopened or edited, no tests/builds were rerun, and no hardware/service actions occurred. Prior focused SDK timer-dispatch evidence remains applicable because that code is unchanged. Only this review artifact was written.
