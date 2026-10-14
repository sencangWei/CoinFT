# Historical profile fixture correction — 2026-10-05

- Before correction, candidate injected in memory: 8/9 surface stability tests passed. Historical test failed at line 160 with `AssertionError: 30 != 24`.
- Original production profile full suite: 160 tests passed in 106.258 seconds before correction.
- Independent reviewer approved freezing the original 20260925 profile for this historical 20260926 capture only, preserving all assertions and the current-profile extreme-release test.
- Added `tests/fixtures/shear_demo_profile_20260925.json`, semantically identical to backed-up original JSON. Changed only the historical test's profile path and explicit UTF-8 encoding.
- After correction, candidate injected in memory: all 9 stability tests passed in 1.389 seconds; historical old-zero=24/current-zero=15, variation 10.410640929680575 -> 6.240847099088214, normal all 1.
- No production profile, renderer, UI, backend, firmware or assertion was changed for this correction. Actual deployed-profile full suite remains required before release.
- Original profile SHA256 (CRLF bytes): `fae3ea39d65d105795b6cea8e34b999d939a9ab9afbf0495ab5e15614b728e83`. Backup `original_text` is newline-normalized text; original CRLF reconstruction was independently verified against this SHA.
