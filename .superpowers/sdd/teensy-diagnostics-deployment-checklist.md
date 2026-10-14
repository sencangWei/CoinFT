# Diagnostic firmware deployment guardrails

Software gates and deployment functional bench checks passed on2026-09-28. Root preflight verified operator closed/empty, process/listener0 and single exact Teensy4.0/serial16454680; reviewed HEX hash matched. Loader completed Programming/Booting exit0. Actual PID048B/COM6 raw/COM8 diagnostic;20 valid idle heartbeats and10.0223387s/2003 new raw frames with invalid/discard/saturation0, no CFD1 mixed. Concurrent diagnostic counters progress in same boot. Evidence teensy-diagnostics-deployment-20260928.json. START_DEMO port changed only after raw PASS; actual demo service restart remains manual. No intermittent-fault repair or long-term stability conclusion.

## Predefined bench checks (performed; functional PASS only)

- Operator subsequently launched COM6 service manually;PID41924 and8765 listener verified. Read-only21 HTTP snapshots over19.9295485s/3982new frames/199.803824Hz, every interval progresses, invalid/discard/saturation0;40 same-boot COM8 heartbeats show upstream progression and no command-count changes. Startup functional PASS, resources HTTP200; actual browser rendering/animation SKIPPED because existing CDP unavailable. Evidence teensy-diagnostics-service-startup-20260928.json. No waiting event captured; root-cause task remains.

- Mode bench/no-motion; operator keeps CoinFT empty and the physical sensor/Teensy model is confirmed. No force or direction test in this deployment window.
- Software gate: both task reviews and final review approved, fresh covering tests/full suite/diagnostic ARM build exit0, protected-file SHA256 values match pre-adapter snapshot. Global SDK and original raw USB implementation unchanged.
- Diagnostic window10s: at least10 valid CFD1 lines on confirmed CDC2, correct13 unsigned fields, sequence/uptime and loop counter progress in one boot. Skips allowed; this is functional observation, not a claim of2Hz jitter or zero diagnostic overhead. Opening only confirmed CDC2 setsDTR, sends no sensor commands.
- Raw window10s after operator-authorized empty-state normal startup: parser produces new26-byte data frames, frame count increment1750–2250 (nominal200Hz; no cached rate-only acceptance), invalid/discard counters do not increase, no CFD1 text in raw stream. Record actual host observation span and sample counts, not acquisition timestamps.
- If enumeration/target differs, required evidence missing, or stream stops: no force tests, preserve counters/evidence before reset and report failed/blocked check. Force calibration, direction fidelity, single-frame jitter/drop/latency and long-term stability explicitly not accepted by these checks.

- Existing live USB identity: VID16C0/PID0483, serial16454680; data COM10/MI00. Do not assume Dual Serial remains COM10.
- Actual board Teensy4.0 explicitly confirmed by operator on2026-09-28. Existing teensy40_diag target matches; recheck physical USB identity before upload.
- Local tools already installed: C:/Users/winer/.platformio/packages/tool-teensy/teensy_loader_cli.exe, teensy_ports.exe. Read help/port identification before any write. Never generic upload while multiple Teensys might be attached.
- Current service may still occupy COM10. Operator must close START_DEMO terminal manually and confirm empty state before upload. Do not bypass previous start/stop tool denials.
- Backup manifest .superpowers/sdd/teensy-before-diagnostics-20260928/MANIFEST.md: originals unchanged; binary not certified as flashed image. Preserve diagnostic and original env artifacts separately.
- After upload expected PID048B, MI00 raw and MI02 diagnostic, same physical serial identity. Verify actual enumeration before opening.
- Diagnostic capture tool only opens explicitly verified diagnostic port, reads heartbeat and sends no bytes. Opening CDC can set DTR; not sensor tare/start.
- Raw data requires original i/s startup; use explicit empty-state normal service workflow, not diagnostic bytes on data port.
- START_DEMO.bat port update only after correct new raw port identified and raw framing verified. Preserve other launch options.
- Root cause localized only by same-boot counter evidence at real stop; no guarantee instrumentation fixes fault.
