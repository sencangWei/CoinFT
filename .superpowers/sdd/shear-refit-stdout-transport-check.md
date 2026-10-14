# Capture evidence transport dry-run

2026-09-28. MOCK ONLY; no current sensor acquisition or physical pose is represented.

The controller executed a Python process via the actual exec_command transport,
using 70 synthetic full HTTP states plus 70 sample records. State shape came
from a previously saved complete state and included a representative nested
recovery last_fault with diagnostics. All generated values were marked MOCK;
they are not input to fitting or physical acceptance.

- exec_command max_output_tokens: 60000.
- Exit: 0.
- Returned output: 99817 characters; original token count: 24955.
- JSON.parse of the entire returned stdout succeeded.
- Both observations and samples retained all 70 entries.
- No generated evidence file, HTTP request, serial access or service control.

This establishes transport headroom beyond the planned approximately 51 states
for this representative schema. It does not replace mocked tests of the exact
prepared command, timeout tests, real capture validation, or physical direction
acceptance. Use the same output budget and store the result without displaying
raw counts; announce release before parsing/saving real captures.
