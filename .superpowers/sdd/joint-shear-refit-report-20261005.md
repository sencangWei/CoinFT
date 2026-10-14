# Bounded joint shear / normal-leak fit — 2026-10-05

DONE_WITH_CONCERNS. The requested renewed attempt is complete within the existing profile formula. The strict joint LP is infeasible. The one temporal/cardinality MILP solved optimally, but actual unchanged Chromium replay fails the original right-direction 80% gate: **24/37 (64.86%)** stable samples reach +0.20. Left is **34/34 (100%)**, all six idle/press windows output exactly zero, wrong-direction counts are zero, and normal output is exactly unchanged. The failed candidate is retained only for diagnostics; it is not frozen as an acceptance candidate or deployed.

## Scope and provenance

Only the new offline script, focused test, JSON report and this report were created. Production, firmware, device state, tare, service processes and previous evidence were untouched. All 14 protected files in `stream-recovery-final-manifest.json`, plus `coinft_demo.py`, match their expected hashes before and after. All original source hashes were checked before and after (326 samples total).

Chronological training order is left_before, left, press_before, press, press_after, right_before, right, right_after. Source paths/SHA256, owner, host timestamps, frame ranges and original raw-channel offsets are carried in the JSON. Every derived channel is raw minus the one fixed reference offset from `current_controls_empty.json`, then the same fixed common unloaded baseline is subtracted for every feature/replay window. Raw/frame/time/owner are preserved. Existing `_validate` and `ordered` validators pass. Corrected `left_repeat.json` is unloaded and excluded, as previously documented; no other sample exclusions. `right_after` has recovery 31/3, versus 30/2 for earlier windows. These are separately reset training windows, not one uninterrupted stream or independent acceptance captures.

## Formula and bounded attempts

Features are eight first-channel contrasts plus `normalScore(CH9–12)`. Fit `score = dot(w, contrast) − beta * normalScore`, with `sum(w)=0` and **no intercept**. The normal coefficient is free. For `n=norm(w)`, store weights `w/n`, pressLeak `beta*w/n²`, threshold `1/n`, and span `s/n`. Thus encoded score is exactly raw score/n. Other original profile fields, labels and `normal={threshold:100,span:600}` are preserved. Maximum all-sample encoding error is **1.4211e−13**.

1. Strict raw LP: threshold/span=1/1, all idle/press `abs(score)<=.50`, all right `>=1.1`, all left `<=−1.1`; minimize L1 of scaled joint coefficients. Ten-second limit, result infeasible in 0.0051 s. This raw 100% separation is a diagnostic, not an added acceptance gate.
2. One temporal MILP: threshold=1, continuous span [.5,2.5], selected signed EMA >=1.05; stable targets are ceil(.8*34)=28 left and ceil(.8*37)=30 right. Maximize balanced coverage `rho` up to these two targets, with tiny scaled-L1 (1e−7) and span (1e−8) penalties. Every idle/press raw score stays within ±.50, every loaded signed raw score stays >=−.50, and every loaded raw score is bounded by ±(.6+.85*span). No pre-EMA clipping therefore occurs. EMA uses exact host deltas, 180 ms time constant, direct first-sample initialization, and separate per-window resets, matching production `surface.js`. The selected >=1.05 bound guarantees activation and output >=.20 over the full span range. Binary big-M=1.55 follows from the signed-EMA lower bound −.50. Thirty-second limit; optimal in 0.2533 s, gap=0, maximum constraint violation 8.8818e−16. Span=2.5, rho=.8, selected counts left26/right24. **rho=.8 denotes 80% of each target count, not actual 80% acceptance.** Actual JS is the acceptance authority.

This sufficient no-clipping optimization permits diagnostic partial coverage so an unsuccessful fit still yields interpretable scores. It does not represent every possible clipped/hysteretic profile, nor certify the highest possible actual JS pass fraction.

## Actual production JS replay

`refit.replay(candidate, old, windows, baseline)` ran in Chromium, followed by the unchanged `refit.passes`. Stable means host time >=600 ms. Normal equality was checked at every sample, including transitions. Full transition/stable rows, raw scores and exact unclipped EMA scores are in the JSON.

| Window | Transition count / active / reverse | Stable count / active / reverse | Stable min / median / max |
|---|---:|---:|---|
| left_before | 5 / 0 / 0 | 36 / 0 / 0 | 0 / 0 / 0 |
| left | 6 / 3 / 0 | 34 / 34 / 0 | −.362586 / −.264509 / −.211765 |
| press_before | 6 / 0 / 0 | 35 / 0 / 0 | 0 / 0 / 0 |
| press | 6 / 0 / 0 | 36 / 0 / 0 | 0 / 0 / 0 |
| press_after | 5 / 0 / 0 | 36 / 0 / 0 | 0 / 0 / 0 |
| right_before | 5 / 0 / 0 | 35 / 0 / 0 | 0 / 0 / 0 |
| right | 4 / 4 / 0 | 37 / 24 / 0 | 0 / .265711 / .435922 |
| right_after | 5 / 0 / 0 | 35 / 0 / 0 | 0 / 0 / 0 |

For idle/press, active above means abs(output)>.05. Their transition and stable outputs are all zero. Transition left min/median/max are −.265729/−.112667/0; transition right are .221957/.239204/.255190. No transition samples were used to satisfy stable cardinality.

Right failures are 12 successive stable samples from **715.573–2095.432 ms**, plus the final **5108.871 ms** sample. In the early segment, raw scores fall from .690056 through negatives (minimum −.265369) and recover to 1.310930. EMA falls below continuation .6, deactivates, and reaches only .947967 by 2095.432 ms, still below activation1. That sample outputs zero despite its positive raw score. Final EMA=.986059 yields only .181675, below .20. This identifies the actual timing/score failure without claiming hardware fault or universal impossibility.

The actual normal/shear output timeline for those misses is below. The normal response varies markedly inside the labeled right window; its cause is not established by these captures. It does not prove an operator release or hardware issue.

| Right ms | Normal output | Shear output |
|---:|---:|---:|
| 715.573 | 1 | .143834 |
| 840.892 | 1 | .005682 |
| 966.828 | .340000 | 0 |
| 1092.524 | 0 | 0 |
| 1234.572 | 0 | 0 |
| 1360.226 | 0 | 0 |
| 1467.626 | .628333 | 0 |
| 1593.260 | .777500 | 0 |
| 1734.880 | .875833 | 0 |
| 1843.903 | 1 | 0 |
| 1969.583 | 1 | 0 |
| 2095.432 | 1 | 0 |
| 5108.871 | 1 | .181675 |

Diagnostic candidate SHA256: `ddae2526893b95db8fd07c861e372e048b0bf1b68b062242afb1300a40645864` (UTF-8 JSON, sorted keys, compact separators, ensure_ascii=True). Encoded threshold/span are 92.4342079244 / 231.085519811; raw beta=.00291382578946, raw weight norm=.01081850564261. Complete profile is in the JSON only.

## Test and execution evidence

Focused behavioral RED: valid naive encoder using pressLeak=zeros fails expected score equality for beta=+.7 and normal=500 (actual4.027319 versus expected−61.533688). Correct encoder restored: `D:/conda/python.exe -X utf8 -m unittest discover -s tests -p test_joint_shear_fit.py -v` passes one test covering positive/negative beta, normal0/500, field/scale preservation and zero/nonfinite inputs. Initial missing-file RED was supplemented with this numerical RED/GREEN check.

The first complete run hit JSON serialization of a NumPy selected-count integer after solving/replay. Converting it to Python int and rerunning the identical two formulations produced the recorded report; no alternate parameters, search, poses or source selection were introduced.

Artifacts: `.superpowers/sdd/shear_refit_joint_leak_20261005.py`, `tests/test_joint_shear_fit.py`, `.superpowers/sdd/shear-refit-joint-leak-20261005.json`. Execution: `D:/conda/python.exe -X utf8 .superpowers/sdd/shear_refit_joint_leak_20261005.py`. No independent physical acceptance was performed.
