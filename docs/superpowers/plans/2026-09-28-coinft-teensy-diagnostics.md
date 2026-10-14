# CoinFT Teensy Diagnostics Implementation Plan

> For agentic workers: use subagent-driven-development task-by-task. No Git repository; before snapshots and no-index review packages replace commits/worktrees. Two independent deliverables executed sequentially with reviews.

**Goal:** Observe CoinFT UART consumption and Teensy USB forwarding while keeping the original raw stream untouched.

**Architecture:** Optional diagnostics compiled only for USB_DUAL_SERIAL; main-loop 2Hz bounded heartbeat on SerialUSB1. An isolated read-only Python observer captures lines on the identified second port. No automatic recovery or device commands.

**Tech Stack:** Arduino Teensy4.0, installed PlatformIO/Teensy SDK, native g++, Python unittest/pyserial.

## Global Constraints

- Keep NUM_COINFTS=1, Serial2 at 1,000,000 baud, exact existing TUNING[12][3], boot delays, i/s/t behavior, 1ms IntervalTimer, sensor framing reads and data USB writes.
- Do not refactor forwarding, alter CoinFT firmware or change original visuals/profiles/force parameters.
- No diagnostic bytes on raw Serial. Diagnostic port never receives commands that affect the sensor. Heartbeat skips unopened/full port; no waiting or flush call.
- No live COM access, upload or service restart in worker/test tasks. Root owns hardware deployment; previous start/stop tool restriction must not be bypassed.
- Preserve original teensy40 environment/binary artifacts; diagnostic env teensy40_diag only. No edits to firmware_imu/platformio.ini or startup batch before new port identity and raw protocol are verified.
- Local firmware.hex predates current source and is not certified equal to the currently flashed image. Backup is not an exact-device rollback guarantee.
- All PlatformIO commands must use --disable-auto-clean: default config-checksum cleaning deleted old build outputs on first diagnostic build; original HEX/ELF restored and verified from backup.
- User-approved supplement: only teensy40_diag substitutes build-local CDC2 transmit functions; no global SDK or usb_serial.c edits. Exact upstream source hash guard fails closed on SDK drift. Busy/error/insufficient capacity skips the whole diagnostic line without yield/timeout/flush/error logging, preserving prior autoflush flag.

## Task 1: Conditional firmware instrumentation and native tests

Full binding steps/interfaces, counter schema, tests, build commands and ownership: .superpowers/sdd/teensy-diagnostics-task-1-brief.md.

- [x] Native test harness before production edits; compile actual firmware with fake external Arduino transport/timer/clock, observe intended missing-heartbeat RED.
- [x] Add diagnostic-only counters and heartbeat, append distinct build environment; run focused GREEN and original-mode regression harness.
- [x] Build teensy40_diag only; prove original binary hashes and exact tuning unchanged; freeze source and report.
- [x] Apply approved SDK non-waiting supplement using .superpowers/sdd/teensy-diagnostics-task-1-adapter-brief.md; observe intended RED against actual unadapted SDK function, GREEN against transformed functions, target build and unchanged SDK/original binary hashes.
- [x] Task review; resolve Critical/Important findings with covering tests and re-review.

## Task 2: Read-only heartbeat observer and tests

Files: create coinft/capture_teensy_diagnostics.py and tests/test_teensy_diagnostics_capture.py; no existing server/frontend edits.

Interface: parse_heartbeat(line: bytes)->dict rejects malformed/wrong-version/out-of-range fields. FIELD_NAMES correspond in order to the exact firmware CSV schema in Task1 brief. capture(port: str, seconds: float)->list[dict] opens an explicitly supplied port only, with short read timeout and DTR enabled; reads only, never writes/flushes/commands. main prints bounded JSON, fails when no valid heartbeat, supports --port (required), --seconds (default10, positive <=60) only. Host observed timestamps are not sensor timestamps. Every record includes sequence, uptime and absolute cumulative counters; tool never computes cross-reset deltas.

- [x] RED tests for parser known valid record, missing fields/wrong version/negative/non-numeric/>uint32, fake serial capture with bad lines and clock bounded completion, and no-write behavior; no real COM opens.
- [x] Minimal implementation. Valid record example:

```python
sample = parse_heartbeat(b"CFD1,1,500,9,26,1,24,1,0,1,1,26,1,0\n")
assert sample["uart_bytes"] == 26
assert sample["usb_accepted_bytes"] == 26
```

- [x] Focused tests then one full unittest suite. Report RED/GREEN/full outcomes and freeze source.
- [x] Task review.
- [x] Strongest-model final whole-change review of both tasks.

## Root verification and deployment

- [x] Independently rerun covering tests/build on final frozen sources; compare backups/original HEX and ELF hashes; update PROJECT_LOG/ledger. Final read-only review approved the unchanged tested snapshot; fresh full110 tests68.823s exit0, Task1 build1.110s exit0, final protected hashes9/9 match.
- [x] Operator closes START_DEMO terminal and confirms empty state and Teensy4.0 identity. Read-only verified process/8765 listener0 and unique serial16454680. No bypass of tool process-control restrictions.
- [x] Verified reviewed HEX hash; installed PIO supported reboot helper then loader completed Programming/Booting exit0. Actual same serial PID048B MI00 data COM6 / MI02 diagnostic COM8.
- [x] Bounded diagnostic-port read:20 idle CFD1 records pass. Authorized empty-state standalone raw startup i/s then final i:10.0223387s/2003frames/199.853553Hz, invalid/discard/saturation0 and no CFD1 on raw; concurrent20 diagnostics pass. Batch --port updated only COM10->COM6 after raw PASS. Ports released; HTTP service not started. Evidence .superpowers/sdd/teensy-diagnostics-deployment-20260928.json.
- [x] Captured actual waiting before reset in teensy-diagnostics-minusx-stalled-20260928.json and explicit-release follow-up teensy-diagnostics-release-stalled-20260928.json: PC read loop/main loop/timer progress, UART-consumed/packets/USB attempts stalled. UART consumption gated by available()>25; physical wire/root cause remains unresolved. No recovery observed after release. Proposed operator-only service i/s restart comparison next; not performed. No root-cause/repair or stable-direction claim.
