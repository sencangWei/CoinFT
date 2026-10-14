# CoinFT serial stream diagnostics (approved 2026-09-26)

## Goal

Distinguish serial silence from received bytes that the parser cannot turn into frames. Diagnose the repeated waiting state without assuming wiring failure or changing visual/force interpretation.

## Alternatives

1. Add counters to the existing acquisition service/API (recommended): one COM10 owner, no firmware change, observes the actual reader and parser. Requires one manual restart to load changed Python code.
2. Add Teensy firmware UART/USB counters: can distinguish lower layers but requires verifying the flashed source and rebuilding/reflashing. Out of scope for this first diagnostic step.

## Minimal design

Only modify coinft_demo.py and tests. Add a diagnostics object to /api/state with process-lifetime serial read and byte totals, parsed frame total, last nonempty read time, last parsed frame time, parser pending byte count and discarded/resync byte count. Zero timestamps represent never observed. Preserve existing status, frames, channels, axes, zero/tare and startup i/s behavior. Keep counters cumulative across port reopen; report current parser buffer state separately. Snapshot diagnostics must be copied under the existing lock so callers cannot mutate live state.

Counters must advance on bytes even if no complete frame exists or all data is malformed. Empty reads advance read count but not byte time/count. Parsed frame time counts parser output including frames later rejected by range validation; existing updated_at remains the time of valid frame consumption. This avoids equating parser success with valid sensor data.

No automatic retries, restart endpoint, device writes, firmware changes, raw byte file logging, frontend changes or direction-template fitting are introduced.

## Verification

TDD serial read-loop tests using an isolated fake serial transport and real parser: empty reads; malformed nonempty bytes; partial frame split across reads; valid frames; out-of-range parsed frames; independent snapshots; reconnect cumulative totals/current parser reset. Never open COM10 in automated tests. Run focused tests and full existing suite before claiming diagnostic implementation complete.

## Live deployment and stop condition

Current service must be manually restarted once to load the fields because the tool environment rejected process stop/start. Inform operator about the existing startup tare and require empty state. Verify counters in /api/state while live. At the next waiting event, compare two snapshots: reads increasing with bytes frozen indicates no incoming bytes; bytes increasing with parsed frames frozen indicates parser/protocol trouble; no read progression may indicate blocked read loop. Do not infer which upstream hardware failed from these counters alone. Physical root cause remains unresolved until this live evidence is captured.

## Environment

This project has no Git repository; do not initialize one or commit. Preserve all existing edits. User approved this minimal scope. Live deployment remains pending implementation, tests and manual service restart.
