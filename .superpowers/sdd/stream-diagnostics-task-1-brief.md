# Task 1: minimal serial diagnostics

Work in D:\semg.claude\coinft. Own coinft_demo.py and new tests/test_serial_diagnostics.py only; report .superpowers/sdd/stream-diagnostics-task-1-report.md. Others share this workspace: do not revert unrelated edits. No Git repository, no init/commit/worktree. Use apply_patch. Root owns docs/ledger/snapshots.

## Binding requirements

Only add serial diagnostic counters to the existing API. Preserve existing status, frames, channels, axes, zero/tare and startup i/s behavior. No automatic retries, restart endpoint, device writes, firmware changes, raw byte file logging, frontend changes or direction-template fitting are introduced. Never open COM10 or restart any live service in tests.

State contains a nested diagnostics dictionary with precisely these initial values:

```python
"diagnostics": {
    "serial_reads": 0, "serial_bytes": 0, "parsed_frames": 0,
    "last_byte_at": 0, "last_parsed_frame_at": 0,
    "parser_pending_bytes": 0, "parser_discarded_bytes": 0,
}
```

serial_reads increments for every completed serial read, including empty reads. serial_bytes counts returned bytes, not buffer flushes. last_byte_at is wall time of most recent nonempty read. parsed_frames and last_parsed_frame_at reflect parser outputs including range-rejected raw frames. Zero time means never seen. parser_pending_bytes is current parser buffer length. parser_discarded_bytes is cumulative parser resync/discard byte count across port reopens, not frame count. Totals and last times remain across reopen; pending bytes reset when a new parser is constructed. Existing resyncs semantics are unchanged. Diagnostics must be independent copies in snapshot(), so mutating a returned object cannot affect the source or earlier snapshots.

Keep implementation local in _run_serial, no unnecessary abstraction. Per read, capture previous parser.resyncs, feed the real parser once, update diagnostic totals/times/buffer under existing lock, then consume parsed frames via unchanged _consume and unchanged last_frame watchdog. On opening a fresh port, set pending byte count to zero under lock alongside existing rate reset. Use one time.time timestamp per completed read. Do not call time.time in _consume differently or change monotonic frame timing.

## TDD

Create deterministic tests of actual _run_serial using fake serial transport plus real FrameParser and real _consume; mock only external serial and time/sleeps where necessary. Source stop_event ends after last test read returns, so that chunk is still processed; record snapshots while progressing to verify partial/empty states. Cover all initial zeros; empty reads; garbage updates byte and discarded counters without frames; split frame across reads with following header; valid frame counts; parsed but out-of-range frame vs valid updated_at; immutable snapshots; two port sessions preserving totals/timestamps and resetting pending buffer without real wait. Verify unchanged i/s/final-i command sequence. Read testing anti-patterns before adding mocks.

Run RED command before production edit: D:\conda\python.exe -m unittest discover -s tests -p test_serial_diagnostics.py -v. Report intended missing-diagnostics failures. Then minimal GREEN implementation and focused run. Full existing suite once at end: D:\conda\python.exe -m unittest discover -s tests -q. Report exact counts, duration, exit status, any noise. No intentional relaxation of existing tests. Self-review scope and concurrency.

Write detailed report with RED/GREEN commands/output, changes and concerns. Return only DONE/concerns and short test summary. Leave source frozen after full suite while root reviews and independently verifies.
