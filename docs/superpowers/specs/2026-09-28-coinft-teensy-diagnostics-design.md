# Teensy-side CoinFT diagnostics — proposed design

Status: detailed dual-USB design approved by user on 2026-09-28, including possible COM renumbering. Implementation now authorized; upload remains contingent on tests, exact target and closed-service checks.

Supplement approved by user on 2026-09-28: diagnostic-build-only non-waiting USB send adaptation. The installed SDK capacity check can advertise space while the current transmit head is busy; its default write can wait about120ms. The diagnostic build therefore substitutes a project/build-local copy of usb_serial2.c through PlatformIO middleware, with an exact upstream SHA256 guard. Global SDK files and original usb_serial.c remain untouched. Only CDC2 diagnostic transmit write/capacity paths change: a bounded line is accepted in full when current capacity permits, otherwise skipped immediately without yielding, timeout polling, flush or error logging. Suppress CDC2 autoflush briefly while inspecting/copying the bounded line, restoring the prior flag. The original teensy40 environment does not load this adapter. Native tests exercise the actual transformed SDK functions, not just a mocked availableForWrite, including busy/error/unconfigured/insufficient capacity and subsequent recovery. Physical timing and hardware fault cause still need bench observation.

## Purpose and boundary

The PC reader completes reads but receives no new bytes. Observe the next upstream boundaries without changing CoinFT firmware, the 12-channel tuning table, current raw data framing, normal/shear visuals or thresholds. Diagnostic availability is not proof of accurate force or a hardware defect.

## Approaches

1. Recommended: Teensy USB_DUAL_SERIAL. Keep Serial for existing i/s/t commands and 00 00 + 24 raw bytes, add SerialUSB1 for diagnostic heartbeat. No mixing diagnostic text into raw frames; no extra wiring. USB PID changes from 0483 to 048B and Windows COM numbers may change.
2. Same-port multiplexed diagnostics: avoids a second port but changes framing/parser and risks diagnostic bytes resembling raw headers. Reject for this scoped instrumentation.
3. External UART observation: avoids firmware instrumentation but needs another receiver/logic analyzer and wiring; not selected because the operator finds rewiring difficult.

## Diagnostic firmware

Source C:/Users/winer/Desktop/CoinFT_Teensy_Interface/teensy_coinft_serial_interface.cpp; platformio.ini board remains teensy40. Use a distinct diagnostic build environment with USB_DUAL_SERIAL, preserving the original build environment and its artifacts.

Keep NUM_COINFTS=1, Serial2 at 1,000,000 baud, exact existing TUNING[12][3], boot delays, i/s/t behavior, 1ms IntervalTimer, sensor framing reads and data USB writes. Do not refactor the existing forwarding architecture as a speculative fix.

Add cumulative 32-bit counters only at existing operations: loop progress, successful UART bytes consumed, header-selected data reads and their actual lengths, observed end markers/timeouts, timer callback entries, USB forwarding attempts and actual accepted byte returns, i/s commands. Include uptime and firmware diagnostic version. Retain sequence/uptime and absolute counters so wrap/reboot remains visible to the observer; do not calculate differences across resets. USB accepted bytes are not proof of PC delivery.

Heartbeat reports on SerialUSB1 from the main loop at 2Hz, only when the port is open and the whole bounded line fits availableForWrite. No waiting for diagnostic connection or buffer space, no output on raw Serial, no commands sent to CoinFT by diagnostics, no automatic restart/tare. Take a brief atomic snapshot of interrupt-updated counters; preserve interrupt state. If main loop stalls, heartbeat can disappear; absence alone cannot identify which component stalled.

## Host observation and deployment

Provide a separate bounded diagnostic capture tool: read-only serial input on the explicitly identified diagnostic port, no write/start/stop/tare commands. Record heartbeat progress and absolute counters with sequence/uptime; do not compute deltas across wrap/reboot. Identify the data vs diagnostic interface using new PID048B and their interfaces; do not assume COM10 remains the data port. Do not open both ports by guessing.

Deployment requires the operator to close the current START_DEMO terminal manually before flashing, keep the sensor empty and verify Teensy4.0 identity. The environment previously rejected assistant service start/stop commands; do not bypass it. Flash only the approved diagnostic Teensy build, not CoinFT. After enumeration, verify the raw port and normal packet protocol before changing the startup batch to a newly confirmed port if necessary. Never silently change unrelated firmware_imu/platformio.ini.

## Backup, verification and limitations

Backup saved at .superpowers/sdd/teensy-before-diagnostics-20260928: existing source, config, firmware.hex and firmware.elf. Hashes match originals. The on-disk binary is not independently verified as the firmware currently on the Teensy; backup does not certify an exact current-device rollback. Preserve both original environment/artifacts and diagnostic build separately.

Before uploading: tests with fake Arduino/USB/UART boundaries should exercise actual instrumented source paths, confirm no diagnostic writes on raw Serial, exact tuning/commands/framing preservation, closed/full diagnostic port skipping and actual UART/USB return accounting. Native compile and Teensy4.0 firmware build must pass. Recheck original hashes and make a scoped diff; do not claim these tests establish hardware behavior.

Bench check after upload: correct two-port enumeration/version, original data frames on the data port, advancing heartbeat/UART/USB counters while live. At a stop compare same-boot counters: no UART bytes suggests no upstream bytes consumed; UART progress without accepted USB progress suggests the forwarding boundary; accepted USB progress without host bytes suggests a USB/host boundary. These are localization clues, not conclusive physical causes. Capture failing evidence before any reset. Force/direction, single-frame jitter and true acquisition latency remain out of scope.

## Review checklist

- Context inspected; no Git repository exists, no commit/init/worktree operations.
- Visual companion skipped: text protocol decision, no UI/layout question.
- User accepted the second USB port and possible COM renumbering.
- Alternatives, scope, error/stop behavior, tests and rollback limitations are explicit.
- Written-spec approval received; proceed through implementation/TDD and safe upload gates.
