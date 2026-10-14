# Live serial diagnostic handoff

Instrumentation is additive and observational. No automatic restart, start command, tare, or direction-template fitting is performed by diagnostics. The existing service sends i/s and requests tare only when opening COM10, unchanged.

After tests and reviews, operator must load the changed Python process once: keep sensor empty, stop the current START_DEMO.bat terminal with Ctrl+C, then run the same batch again. Do not restart USB or firmware during this comparison. Assistant process start/stop commands were rejected by the tool environment; do not substitute a different termination method.

First verify /api/state contains diagnostics and that serial_bytes and parsed_frames increase with new live frames. A page baseline from the old process must not be reused after frame reset/device tare; use explicit empty confirmation before any demo zero. A missing diagnostics key means old code is still running, not zero serial activity.

At a waiting event collect two snapshots at least one second apart from the same service process. Compare cumulative counters, not values in isolation:

- serial_reads increases but serial_bytes does not: reads complete but return no incoming bytes.
- serial_bytes increases but parsed_frames does not: transport supplies bytes but the parser is not producing frames; check parser_pending_bytes and parser_discarded_bytes.
- parsed_frames increases but invalid_frames also increases and updated_at remains stale: frames parse but raw values fail range checks; do not mistake this for valid readings.
- None of the counters progresses: possible blocked read/update loop or dead thread; check status/error and process lifetime before interpreting.
- Process restart resets cumulative totals; port reopen resets current parser_pending_bytes only. Do not subtract counters across process resets.

These observations locate the PC reader/parser boundary, not the exact upstream CoinFT/Teensy fault. Do not infer wiring failure, sensor damage, or a firmware defect from serial silence alone. Root cause and independent direction acceptance remain pending.
