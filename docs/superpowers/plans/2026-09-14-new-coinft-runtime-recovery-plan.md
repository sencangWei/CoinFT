# New CoinFT Runtime-Recovery Implementation Plan

**Execution status (2026-09-14): COMPLETE WITH OPERATOR-APPROVED DEVIATION.** Tasks 1-2 passed. Task 3 used 100 g instead of 200 g and produced a clean transport/electrical capture but no separable mechanical response (CH9-CH12 drift-corrected sum +18.5 counts). Further loading stopped pending visual load-path inspection.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover valid unloaded raw counts on the newly connected CoinFT using volatile runtime commands, then perform one controlled 200 g mechanical A/B test.

**Architecture:** Use the existing verified Teensy five-byte tuning passthrough on COM10. Do not edit or reflash firmware; first move all channel Compensation values to the conservative maximum of 127, validate raw data, and only then load the sensor.

**Tech Stack:** PowerShell, Python 3, pyserial, existing `coinft_acceptance.py`, Teensy 4.x, CoinFT UART at 1,000,000 baud behind the Teensy USB serial bridge.

## Global Constraints

- Keep the new CoinFT unloaded until all 12 medians are within 5000-30000 and saturation count is zero.
- Do not power-cycle during runtime recovery; existing startup tuning would be resent.
- Preserve the current per-channel Resolution and Ref values; initially change only Compensation to 127.
- Runtime values remain volatile and must not overwrite the existing sensor's embedded startup table.

---

### Task 1: Apply conservative runtime compensation

**Files:**
- Read: `C:/Users/winer/Desktop/CoinFT_Teensy_Interface/teensy_coinft_serial_interface.cpp`
- No source files modified.

**Interfaces:**
- Consumes: COM10 Teensy serial bridge and five-byte packet `t, channel, resolution, ref, compensation`.
- Produces: 12 volatile CoinFT channel configurations with Compensation 127.

- [x] **Step 1: Confirm the sensor is unloaded and COM10 is not in use**

Run:

```powershell
Get-CimInstance Win32_SerialPort | Where-Object DeviceID -eq 'COM10' | Select-Object DeviceID,Name
```

Expected: one COM10 serial device and no acquisition process holding the port.

- [x] **Step 2: Send the 12 runtime commands**

Run from `D:/semg.claude/coinft`:

```powershell
python -c "import serial,struct,time; rows=[(12,50),(12,30),(12,30),(12,30),(12,30),(12,30),(12,30),(12,30),(12,100),(12,100),(12,80),(12,80)]; s=serial.Serial('COM10',115200,timeout=1); s.write(b'i'); time.sleep(.1); [(s.write(struct.pack('BBbbb',ord('t'),ch,res,ref,127)),time.sleep(.06)) for ch,(res,ref) in enumerate(rows)]; s.close(); print('sent 12 runtime tuning packets: compensation=127')"
```

Expected: `sent 12 runtime tuning packets: compensation=127`.

### Task 2: Validate unloaded operating range

**Files:**
- Read: `D:/semg.claude/coinft/coinft_acceptance.py`
- Create: `D:/semg.claude/coinft/calibration/new_coinft_comp127_idle_20260914.csv`

**Interfaces:**
- Consumes: runtime-tuned CoinFT on COM10.
- Produces: six-second 12-channel unloaded acceptance evidence.

- [x] **Step 1: Capture unloaded data**

Run:

```powershell
python .\coinft_acceptance.py --port COM10 --seconds 6 --out .\calibration\new_coinft_comp127_idle_20260914.csv
```

Expected: approximately 1200 frames at approximately 200 Hz, zero resyncs, zero saturation, and every median between 5000 and 30000.

- [x] **Step 2: Apply the stop condition**

If any channel remains at 33782, falls below 5000, or reports saturation, do not load the sensor. Preserve the CSV and revise the per-channel Compensation search using that evidence. If all channels pass, continue to Task 3.

### Task 3: Run the first mechanical A/B bracket (operator changed load to 100 g)

**Files:**
- Create: `D:/semg.claude/coinft/calibration/new_coinft_unshielded_15mm_puck_100g_empty_before_20260914.csv`
- Create: `D:/semg.claude/coinft/calibration/new_coinft_unshielded_15mm_puck_100g_load_20260914.csv`
- Create: `D:/semg.claude/coinft/calibration/new_coinft_unshielded_15mm_puck_100g_empty_after_20260914.csv`
- Modify: `D:/semg.claude/coinft/PROJECT_LOG.md`

**Interfaces:**
- Consumes: unloaded acceptance PASS, same 15 mm puck, same support geometry, operator confirmation at each physical stage.
- Produces: drift-corrected all-12 response and a PASS/FAIL decision for separable 200 g response.

- [x] **Step 1: Capture adjacent pre-load empty data**

```powershell
python .\coinft_acceptance.py --port COM10 --seconds 6 --out .\calibration\new_coinft_unshielded_15mm_puck_100g_empty_before_20260914.csv
```

Expected: zero resyncs and zero saturation.

- [x] **Step 2: After explicit operator confirmation, capture centered 100 g load**

```powershell
python .\coinft_acceptance.py --port COM10 --seconds 6 --out .\calibration\new_coinft_unshielded_15mm_puck_100g_load_20260914.csv
```

Expected: zero resyncs and zero saturation; no response magnitude is assumed in advance.

- [x] **Step 3: After explicit operator confirmation, capture post-load empty data**

```powershell
python .\coinft_acceptance.py --port COM10 --seconds 6 --out .\calibration\new_coinft_unshielded_15mm_puck_100g_empty_after_20260914.csv
```

Expected: zero resyncs and zero saturation.

- [x] **Step 4: Compute and record the result**

For each channel, subtract the midpoint of the two empty medians from the loaded median. Report CH1-CH8 sum, CH9-CH12 values and sum, all-12 sum, and post-minus-pre residual. Record evidence and status in `PROJECT_LOG.md`; do not call the test calibration data.
