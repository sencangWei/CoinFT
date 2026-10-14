# Pending duplicate-snapshot acquisition correction

2026-09-28. User explicitly approved this repair after the0.125s retry failed.
Implementation is assigned to a bounded worker; physical acquisition awaits
TDD/independent review. This file preserves the diagnosed failure and design.

The approved0.125s cadence amendment passed six focused tests and independent
review. Its actual empty retry still failed after22 observations/2.5865461s:
the last HTTP response repeated frame1865364 and its byte/parsed/read counters,
with statuslive/recentinvalid0 and cumulativeinvalid62/recovery3/2 unchanged.
The last receive interval was105ms despite125ms request scheduling: HTTP latency
variation makes receipt spacing shorter than request-start spacing. A larger
fixed interval alone is not a robust duplicate policy.

Proposed bounded repair, not a data-quality relaxation:

- Preserve all received states, including duplicates and rejected final states.
- An otherwise healthy response with exactly the last accepted frame number is
  a cached duplicate, not a new sample. Do not append/count it. Keep pacing and
  the original total request and admission deadlines; no busy polling.
- Invalid status/recent faults/nonfinite or malformed channels/frame regression
  still reject immediately, even if the frame number repeats. Observer errors
  and late HTTP results retain their existing stop/isolation semantics.
- Diagnostics may stay constant for a cached response, never regress. A fresh
  accepted observation retains advancing byte/parsed counters and unchanged
  quality/recovery/owner requirements.
- Keep125ms requests. Continue within the existing6s admission deadline until
  >=40 distinct accepted snapshots AND both actual5s clock spans are present.
  If impossible, fail; never copy/relabel old snapshots. Generic callers retain
  the existing30-snapshot policy; only this command requires40 before success.
- Only supporting capture command/helper/tests can change. Backend, serial
  settings, firmware, profile, visualization and fitting/replay gates stay fixed.

Covering tests must verify complete duplicate observation retention without
sample inflation, bad duplicated state rejection, frame regression, stalled
deadline, no late callbacks, original caller compatibility and40/5s success.
TDD, independent review and root verification precede any new physical hold.
