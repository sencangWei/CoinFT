# Task 1 report: minimal serial diagnostics

Status: DONE. Production source and tests frozen after the full suite for root review.

## Changes

Only `coinft_demo.py`, new `tests/test_serial_diagnostics.py`, and this report were edited by this worker. Root owns documentation, ledger and snapshots; those were not edited or reverted. No Git initialization, commits or worktrees. No COM10 access, service restart, or live device interaction.

Production changes are limited to four existing locations: initialize the exact seven diagnostic keys to zero; copy the nested diagnostics dictionary in `snapshot()` under the existing lock; reset pending bytes under the existing rate-reset lock when a fresh parser is constructed; update read/byte/parser totals, wall times, pending bytes and discarded-byte deltas under the existing lock after feeding the real parser once per read. `_consume`, parser behavior, existing resyncs semantics, monotonic frame timing, watchdog, startup commands and final stop command remain unchanged. One new wall-clock call occurs per completed read, including empty reads; existing valid-frame `_consume` wall-clock calls remain untouched.

Tests use the actual `_run_serial`, actual `FrameParser`, and actual `_consume`. Only external serial transport, wall/monotonic time, startup sleep and retry-event wait are replaced. The serial module is replaced before `_run_serial` imports it; source port is `TEST_ONLY`; no real transport is constructed. The last read sets the source's stop event before returning, verifying that its chunk is still processed. The real source event handles termination. Intermediate snapshots are collected at the next read and on opening startup writes to verify partial, empty and reopened states.

Five tests cover exact initial zero keys, independent snapshot mutation, empty reads, garbage byte/discard counts without parsed frames, unchanged no-frame `resyncs`, split frame buffering awaiting following header, final-read processing, valid raw/tare/updated_at consumption, rejected parsed raw frames preserving valid updated_at/raw, and two serial sessions retaining cumulative counts/times while resetting pending bytes. Command sequence checks are `[i, s, i]` for clean shutdown and `[i, s]` then `[i, s, i]` across a transport exception (the first session cannot write final i after a failed read, preserving existing behavior). Time-call assertions verify one diagnostic wall timestamp per completed read plus the unchanged valid-consumer timestamp calls.

## TDD evidence

Read `C:/Users/winer/.codex/skills/test-driven-development/SKILL.md` and its `testing-anti-patterns.md` before adding transport/time mocks.

RED command, from `D:/semg.claude/coinft`, before production edits:

```text
D:/conda/python.exe -m unittest discover -s tests -p test_serial_diagnostics.py -v
test_empty_and_garbage_reads_count_bytes_and_discard_without_frames ... FAIL
test_initial_values_and_snapshot_isolation ... FAIL
test_rejected_parsed_frame_advances_diagnostics_but_not_valid_update ... FAIL
test_reopen_preserves_totals_and_times_and_resets_pending ... FAIL
test_split_frame_waits_for_following_header_and_processes_last_read ... FAIL
Ran 5 tests in 0.007s
FAILED (failures=5)
```

Exit status 1. Every failure was the intended `AssertionError: 'diagnostics' not found` from the helper's explicit missing-key assertion, not setup/transport/parser errors. Existing serial loop ran to completion in each transport test.

GREEN focused command after minimal implementation:

```text
D:/conda/python.exe -m unittest discover -s tests -p test_serial_diagnostics.py -v
test_empty_and_garbage_reads_count_bytes_and_discard_without_frames ... ok
test_initial_values_and_snapshot_isolation ... ok
test_rejected_parsed_frame_advances_diagnostics_but_not_valid_update ... ok
test_reopen_preserves_totals_and_times_and_resets_pending ... ok
test_split_frame_waits_for_following_header_and_processes_last_read ... ok
Ran 5 tests in 0.005s
OK
```

Exit status 0. Removed one unused fake-transport attribute before the full run, with no production changes.

Full suite command, run exactly once at the end:

```text
D:/conda/python.exe -m unittest discover -s tests -q
Ran 86 tests in 62.823s
OK
CAPTURE_REPLAY {"old": {"zero": 24, "variation": 10.410640929680575}, "current": {"zero": 15, "variation": 6.240847099088214}, "normals": [1, ... 48 entries ...]}
```

Exit status 0. Noise: browser-test local HTTP access logs, expected missing `shear_profile.json` 404s with fallback `shear_demo_profile.json` 200s, two `/null` 404 requests, and CAPTURE_REPLAY metrics above. No test failures, skipped tests, or relaxed existing assertions were reported.

## Self-review and concerns

Compared current source with `.superpowers/sdd/coinft_demo.before-stream-diagnostics.py` using a read-only unified diff. Only the four intended locations changed; no adjacent code/comments/style cleanup. No new production abstraction, retries, restart endpoint, firmware/device writes, byte file logging, frontend edits, or fitting logic. Diagnostics retain total parser outputs even when consumer rejects range; discarded count is accumulated parser resync-byte deltas across sessions; existing resync count still updates only through `_consume`.

No blocking concerns. As intended, diagnostics are cumulative for one source lifetime and remain zero for replay because only serial reads update them. The existing HTTP/browser noise is recorded, not changed. This report does not claim hardware verification or that an already-running service has loaded edited source.
