# Fresh complete right trial refit — 2026-10-05

Final status: DONE / frozen_training_candidate. The existing previous_softmargin profile passes the same selected eight TRAINING windows at the same fresh common raw baseline: left34/34, right34/36 (94.44%), every idle/press output zero, no reversals, normal exactly unchanged. No new fit produced this passing profile. It is frozen only for future independent acceptance and has not been deployed. Candidate SHA256 `e59c5876fe815262811a000f9afe2b755748daf9762b1611a095ecbb21c0e283`.

Earlier fresh joint fitting result: training_gate_failed; actual unchanged Chromium gate=False (preserved below).

Earlier fitting attempt: Existing builder rejected qualitative direction/background separation before a profile could be constructed. Strict joint LP was infeasible in0.00476s (10s limit); the same reviewed temporal MILP solved optimally in0.48496s (30s limit), span2.5, balanced target coverage.448276, gap0, numerical violation8.88e−16. Actual production JS gate fails left25/34 (73.53%) and right16/36 (44.44%). All idle/press outputs are zero; no direction reversals; normal is exactly unchanged. This failed candidate is retained for diagnostics and is not frozen for acceptance or deployed.

Five complete old left/press windows plus the whole fresh unloaded/right/released trial; no sample cropping. Earlier failed right trial remains preserved.

The previously diagnostic right trial becomes TRAINING evidence in this refit; independent physical acceptance remains required.
Old left/press recovery30/2 versus fresh right31/3; these are mixed-stream windows, separately reset in replay, not continuous acceptance.
Cumulative invalid3 to4 occurred in the unobserved interval between fresh empty/right, not inside captures; no force/noise causation is claimed.
Corrected unloaded left_repeat.json is excluded; selected loaded left_confirmed_repeat.json is preserved in full.
No production deployment, tare, device commands, process changes or new physical hold requests.

One fresh unloaded raw median is used for every replay window. Full source provenance, failed attempts, candidate, transition/stable timelines and hashes are in the JSON.

| Window | Stable count / active / reverse | Min / median / max |
|---|---:|---|
| left_before | 36 / 0 / 0 | 0.000000 / 0.000000 / 0.000000 |
| left | 34 / 25 / 0 | -0.333221 / -0.217920 / -0.143261 |
| press_before | 35 / 0 / 0 | 0.000000 / 0.000000 / 0.000000 |
| press | 36 / 0 / 0 | 0.000000 / 0.000000 / 0.000000 |
| press_after | 36 / 0 / 0 | 0.000000 / 0.000000 / 0.000000 |
| right_before | 36 / 0 / 0 | 0.000000 / 0.000000 / 0.000000 |
| right | 36 / 16 / 0 | 0.077881 / 0.197170 / 0.267905 |
| right_after | 36 / 0 / 0 | 0.000000 / 0.000000 / 0.000000 |

| Window | Transition count / active / reverse | Min / median / max |
|---|---:|---|
| left_before | 5 / 0 / 0 | 0 / 0 / 0 |
| left | 6 / 2 / 0 | −.229968 / −.095509 / 0 |
| press_before | 6 / 0 / 0 | 0 / 0 / 0 |
| press | 6 / 0 / 0 | 0 / 0 / 0 |
| press_after | 5 / 0 / 0 | 0 / 0 / 0 |
| right_before | 6 / 0 / 0 | 0 / 0 / 0 |
| right | 6 / 5 / 0 | .178133 / .230478 / .301143 |
| right_after | 5 / 0 / 0 | 0 / 0 / 0 |

Idle/press active above counts abs(output)>.05. Stable cutoff600ms. Left/right active counts use −.20/+.20; required fraction80%; no reverse beyond .05; normal exactly unchanged.

Earlier failed joint diagnostic candidate SHA256: e66b71b3fab322dd78ae7039a3d10f129426f230a4a9f02981a5acb766a641eb. All 31 protected/input/source hashes unchanged=True.

This is in-sample training replay; a passing candidate is frozen only in the report for later independent physical acceptance, without deployment.

This bounded sufficient no-clipping joint formulation could not satisfy both loaded-direction gates while maintaining background protections at the selected current baseline. It does not establish that all clipped/hysteretic profiles are infeasible or identify a hardware fault. Original failed right data and prior reports remain unchanged.

Execution: `D:/conda/python.exe -X utf8 .superpowers/sdd/shear_refit_fresh_right_20261005.py`. Solver math is reused from the previously reviewed joint module with only its common-baseline identity check changed in memory. No old module/report or source was edited.

## Frozen existing profile comparison (no fitting)

No fitting: existing frozen profiles, same eight complete selected TRAINING windows and same fresh common baseline; all previous fitting failures retained.

previous_softmargin: full unchanged JS gate=True; failed poses=[].
- left_before: active0/36, reverse0, min/median/max=0.000000/0.000000/0.000000.
- left: active34/34, reverse0, min/median/max=-1.000000/-0.999948/-0.973479.
- press_before: active0/35, reverse0, min/median/max=0.000000/0.000000/0.000000.
- press: active0/36, reverse0, min/median/max=0.000000/0.000000/0.000000.
- press_after: active0/36, reverse0, min/median/max=0.000000/0.000000/0.000000.
- right_before: active0/36, reverse0, min/median/max=0.000000/0.000000/0.000000.
- right: active34/36, reverse0, min/median/max=0.151634/0.537254/0.839848.
- right_after: active0/36, reverse0, min/median/max=0.000000/0.000000/0.000000.

original_production: full unchanged JS gate=False; failed poses=['left', 'press'].
- left_before: active0/36, reverse0, min/median/max=0.000000/0.000000/0.000000.
- left: active0/34, reverse0, min/median/max=0.000000/0.000000/0.000000.
- press_before: active0/35, reverse0, min/median/max=0.000000/0.000000/0.000000.
- press: active35/36, reverse0, min/median/max=0.046643/0.490248/0.836383.
- press_after: active0/36, reverse0, min/median/max=0.000000/0.000000/0.000000.
- right_before: active0/36, reverse0, min/median/max=0.000000/0.000000/0.000000.
- right: active36/36, reverse0, min/median/max=1.000000/1.000000/1.000000.
- right_after: active0/36, reverse0, min/median/max=0.000000/0.000000/0.000000.


The selected softmargin profile is exactly unchanged: its weights, pressLeak, threshold/span and original evidence were learned on the ORIGINAL older eight windows; it was selected on the NEW eight windows, not retrained on fresh right. Learning/selection source provenance are stored separately in the JSON.

Frozen candidate location: `candidate`; SHA256 `e59c5876fe815262811a000f9afe2b755748daf9762b1611a095ecbb21c0e283`. Fixed baseline location: `feature_basis.common_raw_baseline` = `[27871.5, 27339.0, 25816.5, 26606.0, 26265.5, 26348.0, 27196.0, 25977.5, 28490.5, 28102.0, 29079.0, 28153.5]`. Reference/common baseline are also preserved for exact reconstruction.

Replay-only reproduction (no fitting), from `D:/semg.claude/coinft`: `D:/conda/python.exe -X utf8 -c "import importlib.util;from pathlib import Path;p=Path('.superpowers/sdd/shear_refit_fresh_right_20261005.py');s=importlib.util.spec_from_file_location('fresh_refit',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.compare_frozen_report()"`.
