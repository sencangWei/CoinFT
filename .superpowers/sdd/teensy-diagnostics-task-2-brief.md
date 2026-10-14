# Task 2 — Read-only Teensy diagnostic observer

Own only coinft/capture_teensy_diagnostics.py and coinft/tests/test_teensy_diagnostics_capture.py plus .superpowers/sdd/teensy-diagnostics-task-2-report.md. Root owns docs/deployment and Task1 owns desktop firmware. You are not alone; preserve others. apply_patch edits only. No Git repo/init/commit, no live serial/HTTP/service/USB commands.

## Exact interface

CFD1 CSV line, LF or CRLF terminated, numeric fields in order: seq, uptime_ms, loop_count, uart_bytes, rx_data_reads, rx_payload_bytes, rx_end_markers, rx_end_timeouts, timer_ticks, usb_attempts, usb_accepted_bytes, start_commands, stop_commands. Every number decimal unsigned uint32, including sequence/uptime/counters. Max bounded record buffer192 bytes. Wrong magic, count, signs, non-ASCII/nonnumeric, missing newline, value>4294967295, overlong data rejected with ValueError; do not silently accept truncated final numeric values. Return dict with names as above; do not derive physical forces or reset-sensitive deltas.

Public functions:

```python
FIELD_NAMES = ('seq','uptime_ms','loop_count','uart_bytes','rx_data_reads',
               'rx_payload_bytes','rx_end_markers','rx_end_timeouts',
               'timer_ticks','usb_attempts','usb_accepted_bytes',
               'start_commands','stop_commands')
def parse_heartbeat(line: bytes) -> dict: ...
def capture(port: str, seconds: float) -> list[dict]: ...
def main(argv=None) -> int: ...
```

capture validates nonempty explicit port and finite duration0<seconds<=60 before opening. Imports serial inside function, opens only requested port at115200 timeout0.1. Set DTR for diagnostic CDC readiness; no setbaud1200 or transport write, flush, reset_input_buffer/output, or sensor commands. Use monotonic duration bound. Assemble LF lines across partial reads with capped memory192; discard malformed/overlong record to next newline without accepting tail as fresh valid message. Discard invalid lines; collect valid parsed fields + host_observed_at=time.time. Timestamp is observer wall time, not acquisition or verified link latency. Return records; no automatic port search/reopen, no actions on data serial port. Absolute counters only — no cross-boot/wrap subtraction. Serial errors propagate to CLI as clear nonzero failure rather than hidden retry.

main argparse flags --port required, --seconds optional default10. Print JSON with port, records and note explaining absolute counters and accepted USB bytes vs PC delivery. Return1 on no valid heartbeat, serial error or invalidduration, argparse invalidusage may2. No --out option or file writes; root saves artifacts via apply_patch. Standalone tool does not require production API/schema/UI changes.

## TDD

Write real-parser tests before creating production file. Guard missing file/import in tests so RED fails with intended missing observer assertion, not import setup error. Cases: known valid LF/CRLF; wrong version/count/signed/nonnumeric/overflow/nonASCII/missingnewline/oversize; capture fake external serial chunks with split valid record, invalid record, overlong garbage and resync to next full valid line; monotonic bounded completion; correct port/baud/timeout; no serial writes/flush/buffer reset; no cross-reset delta and timestamps preserved. duration0/negative/NaN/inf/>60 never opens port. CLI emptyrecords/error nonzero and success JSON. Mock only transport/time, not parser/capture; no COM10 calls.

Commands (cwd coinft):

```powershell
& D:\conda\python.exe -m unittest discover -s tests -p test_teensy_diagnostics_capture.py -v
& D:\conda\python.exe -m unittest discover -s tests -q
```

First command RED before production; then GREEN. Run full suite once after final source freeze, report exact counts/time/exit/noise, do not run parallel full browser suites. Source/test may reference no global device state. Report exact TDD outcomes and changed files, concerns, freeze for review. No upload/live verification claim.
