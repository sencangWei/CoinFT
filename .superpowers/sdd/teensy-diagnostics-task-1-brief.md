# Task 1 — Teensy conditional diagnostic instrumentation

Read approved spec docs/superpowers/specs/2026-09-28-coinft-teensy-diagnostics-design.md. This task owns only C:/Users/winer/Desktop/CoinFT_Teensy_Interface/teensy_coinft_serial_interface.cpp and platformio.ini; create coinft/tests/teensy_diag_fixture/Arduino.h, coinft/tests/teensy_diag_fixture/test_firmware.cpp and coinft/tests/test_teensy_diagnostic_firmware.py. Report .superpowers/sdd/teensy-diagnostics-task-1-report.md. Root owns docs/ledger/deployment; host observer Task2 is separate. You are not alone; preserve other edits. Use apply_patch, no Git/commits, no live COM/upload/start/stop.

Before snapshot: .superpowers/sdd/teensy-before-diagnostics-20260928 contains original source/config/hex/elf and MANIFEST. Recheck source/config hashes before editing; flag overlap. Original hex/elf must remain identical after builds.

## Binding behavior

- Diagnostics compiled only when USB_DUAL_SERIAL is defined. Original teensy40 build remains behaviorally unchanged, without new UART consumption or USB output. Append [env:teensy40_diag] extending env:teensy40 with build_flags=-DUSB_DUAL_SERIAL; build diagnostic environment only. Local PIO builder recognizes macro and won't inject USB_SERIAL if dual is present.
- Keep existing NUM1, exact 12x3 tuning, commands/delays, Serial2 baud, UART read order/end-marker timeout, newData flag timing, timer interval and Serial.write order. No speculative bug fixes. Do not reshape raw frames, move ISR writes, resend s/tare or introduce recovery.
- At existing read calls count successful UART bytes consumed (read>=0 and actual readBytes return). Record header-selected payload read count, actual payload byte total, observed end markers/timeouts. Preserve original short-circuit end-read semantics and do not consume any extra bytes.
- ISR counts timer entries, each newData forwarding attempt, and actual bytes returned by the same existing three Serial.write calls. Accepted bytes != delivery guarantee. No diagnostic writes in ISR.
- USB size_t return can wrap an underlying -1 failure to SIZE_MAX. Count only sane returns0..requested length as accepted, never huge wrapped error values; preserve actual write calls. Native test covers failure return.
- Main loop progress and consumed i/s commands counted. All counters uint32; ISR-updated snapshots protected by short interrupt mask with original PRIMASK restored. No counter increments with competing writers.
- Main-loop heartbeat every500ms, using unsigned elapsed subtraction for rollover. Only if SerialUSB1 is open and whole line fits availableForWrite; otherwise skip, no wait/flush. Bounded ASCII CSV starts CFD1. Numeric fields in exact order: seq, uptime_ms, loop_count, uart_bytes, rx_data_reads, rx_payload_bytes, rx_end_markers, rx_end_timeouts, timer_ticks, usb_attempts, usb_accepted_bytes, start_commands, stop_commands. All uint32. Include newline. Buffer <=192 bytes is enough: 4+13*(10+1)+newline=148 max. Reject snprintf overflow rather than truncated output. Sequence counts reports attempted when time elapses; gaps allowed when skipped. Never send diagnostic data on Serial (raw port).
- No startup blocking on diagnostics. Keep setup behavior; SerialUSB1.begin optional and nonblocking per local SDK.

## TDD and test boundaries

Use actual firmware included into native C++ harness, replacing only Arduino.h/external USB/UART/timer/time. g++.exe installed on PATH. Python unittest compiles in TemporaryDirectory, invokes native scenarios with clear assertion failures; no hardware. Before production modification, tests should compile baseline and fail at intended absent CFD1 heartbeat, not missing-symbol compilation. Tests can inspect output rather than new production globals. Run legacy scenarios separately without macro to prove baseline protocol unchanged.

Cover initial/periodic CFD1 on SerialUSB1, not raw; skip closed/full port; unchanged exact setup tuning bytes/delays/baud; i/s/t forwarding and timer start/end; 26-byte UART packet consumed+26-byte raw output; actual short read/USB write return counts; end-marker/timeout/garbage reads; state snapshot restoring IRQ mask; timestamp/counter wrap represented as absolute values. Distinguish cumulative stats from PC delivery. Do not assert mock existence: assert instrumented actual loop/setup/transmit outputs.

Commands from coinft:

```powershell
& D:\conda\python.exe -m unittest discover -s tests -p test_teensy_diagnostic_firmware.py -v
& C:\Users\winer\.platformio\penv\Scripts\pio.exe run --disable-auto-clean -d C:\Users\winer\Desktop\CoinFT_Teensy_Interface -e teensy40_diag
```

RED command must precede cpp/ini changes. GREEN native tests and firmware build must exit0. Do not build original environment (would overwrite backed up old binary). Do not run full browser suite in this task; native original-mode regression + diagnostic build are proportional. Root/Task2 run full Python suite later.

Discovery: default PIO auto-clean deletes entire .pio/build when config checksum changes, including original environment even when only -e diag requested. First build triggered this; root restored missing original HEX/ELF from verified backup, hashes identical. All further PIO commands must use --disable-auto-clean; do not pretend the initial build preserved files continuously.

## Report and self review

Document precise RED output/reason, GREEN cases/count/timing, native compiler flags, firmware build summary/size/exit, original source/config/binary hashes, changed files, source-vs-flashed identity limitation, no hardware deployment. Freeze on DONE. If differing SDK behavior impacts nonblocking claims, escalate with evidence instead of hiding it. Do not install packages or change source architecture unless root authorizes.
