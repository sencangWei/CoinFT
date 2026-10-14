# CoinFT acquisition auto-recovery

Date: 2026-09-28. User approved the detailed proposal and written spec with “可以”, then selected split-task execution with independent review. This project has no Git repository; keep this file and review evidence in place, without initializing or claiming a commit.

## Purpose and evidence

Make the existing qualitative demo recover from a silent sensor stream without manually restarting the PC program or zeroing again. This is continuity mitigation, not a claim that the intermittent hardware/protocol root cause has been repaired.

The recorded fault has a live PC read loop and live Teensy main loop/timer, but stalled UART-consumed/packet/USB attempt counters. Release alone did not recover. An operator-only service restart restored UART and PC frames with diagnostic boot continuity consistent with no Teensy reboot. That intervention included serial close/open, i/s, PC input-buffer clearing and PC baseline acquisition; it did not isolate the single effective step. Evidence: `.superpowers/sdd/teensy-diagnostics-service-restart-recovered-20260928.json` and the preceding stalled records.

Two approaches were presented. Reopening the configured data port inside the same reader process and replaying normal i/s startup is selected because it most closely reproduces the successful intervention. Keeping the port open and sending i/s alone is not selected because its independent recovery effectiveness has not been measured.

## Scope and ownership

- Change only the PC serial acquisition behavior in `coinft_demo.py` and its covering tests. Reuse the existing frontend's pause/resume behavior; do not edit chart layout, `app.js`, `surface.js`, force matrix, shear profile or gain settings.
- The current serial reader remains the sole owner/writer of the configured raw port, currently COM6. Do not open diagnostic COM8 for writes, introduce another serial-writer thread, or hardcode new port discovery.
- No Teensy/CoinFT firmware, tuning table, voltage, power cycle, USB unplug or startup-batch change. No device t command. Current NUM1/1Mbps/12-channel parameters remain intact.
- No assistant bypass of existing service process-control restrictions. Deployment is an operator-controlled service restart after software verification.

## Detection and retry behavior

1. Use monotonic time. After starting a connection, track the last nonempty raw read and last parsed frame. Both must show no progress for at least2.0s before silence recovery is eligible.
2. Constant-valued valid frames are progress: sustained force or a quiet sensor must not cause reconnect. Saturation, invalid-range values or garbage bytes alone do not trigger this silence recovery. Existing range validation and waiting/degraded reporting remain in force; corrupt continuous traffic is not silently treated as absence.
3. Before closing/resetting the connection, freeze the current fault reason, host observation time, frame count and serial diagnostics, including byte/frame/discard totals and parser pending size.
4. Keep the HTTP server/process alive. Close the old data-port handle, reopen the same configured port, and perform the original i/0.2s/input-buffer reset/s sequence. Existing orderly-stop i behavior may be retained; no firmware reset, tuning write or automatic tare is added.
5. At least5.0s must elapse between automatic recovery-attempt starts, including failed port opens. Retry indefinitely at that bounded cadence while the service is running; do not spin or flood commands. An OS serial failure remains visibly error/waiting and follows the same automatic-recovery spacing.
6. Stop requests interrupt retry waits and the startup delay. No new reopen/start command after stop has been observed; normal best-effort idle/close cleanup remains allowed. Serial read timeout stays0.1s.

## Baselines, counters and display safety

- Preserve an established `RelativeProjector.baseline`, accumulated raw-frame/cumulative diagnostics counts and intentional tare state across automatic recovery. Frame numbers must never restart or regress within the same server process.
- Initial service startup still collects the original400 valid raw frames for the PC baseline. Automatic reconnect must not restart that acquisition from zero or call `request_tare()` on its own. A user-requested tare retains its intentional reset/reacquisition semantics, including while recovering.
- Clear only connection-local partial parser data and reset the rate calculation window on reopen. Preserve cumulative discard/resync accounting and observation timestamps; fault snapshots must be taken before pending data is cleared.
- Expose a separate `recovery` object in `/api/state`: `attempts` (automatic reopen attempts, excluding the initial open), `successes` (at most one per attempt), and `last_fault` (initially null; otherwise reason, host observation time, frame count and a copied serial-diagnostics snapshot). Increment attempts when the automatic open is actually attempted, not on each cooldown poll. Preserve the existing `diagnostics` schema and meaning; snapshot callers must not mutate internal recovery/fault data.
- Use existing waiting/error status and message while data is absent. Do not report cached raw/axes as newly live, invent frames, count a successful write/open as restored data, or accept invalid raw values as successful recovery.
- Count an attempt as successfully recovered once newly received valid data returns the source to live (or completes an intentional pending initial/manual tare). A retry receiving only invalid data is not a success.
- With the server alive, frame count monotonic and PC baseline unchanged, the existing frontend retains its separate demo baseline during waiting/error and resumes on new healthy live frames. No taring state may be introduced solely by reconnect, since it intentionally disarms that frontend baseline.
- Existing frontend behavior remains: blank/pause during absence/degraded data rather than freeze fake live animation. A new server process, explicit user tare or page reload can still require intentional demo initialization; those are not this recovery mechanism.

## Verification contract

Use deterministic fake serial transports and a fake monotonic clock, never actual COM ports, for RED/GREEN regression cases:

- No reconnect before2.0s; eligibility at the exact boundary; quiet constant-value valid frames stay connected.
- Silent stream triggers close/reopen and only original i/s commands; successful stream resumes in the same process without a second baseline acquisition.
- Loaded raw values after recovery project relative to the old baseline; user-held load must not become zero.
- Repeated silent/open-failure retries are spaced at least5.0s. Cancel during cooldown/startup prevents later opens/s and closes safely.
- Pending parser bytes are cleared only after fault capture; frame/discard/serial cumulative totals and timestamps remain consistent across connections.
- Snapshot recovery diagnostics are isolated. An attempt is not called recovered on port open, cached data, invalid frames or incomplete initial tare.
- Initial400-frame tare and explicit manual tare remain correct across reconnect; saturation/invalid/garbage traffic do not independently invoke silence recovery.
- Existing serial diagnostics/core/UI and full regression suite pass. Protected frontend, profile, matrix, batch and firmware hashes remain unchanged. No unrelated cleanup.

For actual hardware, first verify operator manual deployment restart, unique same Teensy4.0 identity and COM6/COM8 roles. Observe a bounded empty-state healthy window and preserve API plus same-boot diagnostic counters at the next real stall/recovery. Do not induce an electrical disconnect, change wiring, or send a fault command without specific operator approval. Simulation tests establish software policy, not actual hardware recovery effectiveness; a live recovery is accepted only when real new raw/UART progress is recorded without PC frame epoch or baseline reset.

## Stop and handoff conditions

Stop deployment on failed covering/full tests, protected-file drift, unknown target identity, unexpected commands or missing operator confirmation. No permanent-root-cause, calibrated-force/direction, long-term stability or frame-level jitter/drop/latency claims from this implementation. Complete software handoff with updated PROJECT_LOG, test evidence and explicitly separate pending hardware acceptance.
