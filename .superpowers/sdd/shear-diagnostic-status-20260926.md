# Shear demo diagnostic status

## Outcome

The reported pure-press false shear and missing +X animation remain unresolved. No production code, firmware or profile was changed during this diagnostic sequence. Horizontal positioning did not eliminate the issue. The only page zero was explicitly performed after the operator confirmed horizontal empty state.

## Evidence

All listed windows were operator-confirmed, individually captured for approximately five seconds, with live data and zero recent invalid/saturated frames. API signed scores are not the filtered rendered animation targets.

| Horizontal action | Median normal score | Median current shear score | Positive / negative start-threshold crossings |
| --- | ---: | ---: | --- |
| Hand center press | 709.5 | +91.48 | 20 / 0 of 45 |
| Hand minus-X | 1065.75 | +155.09 | 35 / 0 of 44 |
| Hand plus-X | 1121 | +42.99 | 6 / 0 of 45 |
| Released after press | 0 | -4.63 | 0 / 0 of 44 |
| Plastic rod minus-X | 88 | +28.55 | 5 / 0 of 45 |
| Plastic rod plus-X | 0 | +14.33 | 1 / 2 of 45 |

Current signed shear activation threshold is +/-99.111 counts. Plastic-rod plus-X range was -128.82 to +110.28; its median is not a stable negative direction response. Plastic-rod minus-X range was -81.55 to +140.85. Both overlap the observed empty fluctuation.

## Interpretation limits

- Earlier samples labelled plus/minus-X before lower-PCB fixation actually involved moving the whole CoinFT according to the operator; they are not valid relative-shear training samples.
- Horizontal positioning alone was insufficient to eliminate the observed issues. Pure press is operator-described, not an independent zero-shear force measurement.
- Plastic rod changes both electrical proximity and mechanics/load magnitude. Reduced common response does not isolate hand capacitance as the root cause; lack of a stable rod direction signal does not establish broken hardware.
- Exploratory fits were not deployed. Same-data results did not robustly separate both directions from pure press/background; no independent acceptance was performed.

## Next bounded step

Pause repeated held-action captures. Request a clear side photograph of the horizontal assembly, both PCBs, lower-PCB fixture and plastic-rod contact point. Verify that the fixture does not immobilize both layers or bypass the silicone load path, and that the rod contacts the intended upper layer rather than a shared support. Do not assume this is the cause before inspecting the setup. Then choose one controlled comparison based on that evidence, not another blind threshold change.

## Live state

Visible Edge session 38434, last probe frame 23583077; data normal, no JS errors, normal/shear animation targets zero. Page baseline: [-63,-60,-121,-55.5,-96,-72.5,-97.5,-0.5,-47,-69.5,-97,-50]. No automatic hardware tare. Individual JSON evidence is under this directory with horizontal_* and insulated_*_diagnostic_20260926 names.
