# New CoinFT Runtime-Tuning Recovery

## Goal

Recover the newly connected CoinFT from the 33782-count saturation caused by the existing sensor's startup tuning table, without changing or reflashing either device.

## Method

1. Keep the CoinFT unloaded and continuously powered.
2. Send runtime-only tuning commands through the already verified five-byte Teensy passthrough.
3. Preserve each channel's current Resolution and Ref values; initially set Compensation to 127 for all 12 channels.
4. Capture six seconds of raw data without sending any additional tuning.
5. Continue only when all 12 unloaded medians are between 5000 and 30000 and every channel has zero saturated samples.
6. If necessary, adjust Compensation one channel at a time toward an unloaded target of 20000-28000, recapturing after each bounded adjustment.

## Safety and stop conditions

- Do not place a weight on the sensor until the unloaded acceptance check passes.
- Stop tuning a channel if it remains saturated at Compensation 127, falls below 5000, or behaves inconsistently after a repeated capture.
- Do not power-cycle during this diagnostic because the Teensy would resend the existing startup table.
- Runtime values are intentionally volatile. They will not replace the existing sensor's saved table unless the new sensor later passes mechanical acceptance.

## Mechanical A/B acceptance

After unloaded acceptance passes, use the unchanged 15 mm plastic puck and support geometry for one bracketed `empty -> 200 g -> empty` test. Record all 12 channels, rate, resyncs, saturation, drift-corrected response, and unloading residual. This first test diagnoses whether the new sensor produces a separable Fz response; it is not calibration data.
