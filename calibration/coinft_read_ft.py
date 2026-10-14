"""Real-time CoinFT 6-axis F/T reader using a fitted calibration.

    D:/conda/python.exe coinft_read_ft.py --port COM10 --calib coinft_calib.json

Tares automatically on startup (first 1 s, keep the sensor unloaded), then
prints Fx Fy Fz Mx My Mz at ~10 Hz. Ctrl+C to stop.
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import serial

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from coinft_acceptance import parse_frames  # noqa: E402


def collect(ser, seconds):
    ser.reset_input_buffer()
    ser.write(b"s")
    frames, resyncs = [], [0]
    buf = b""
    t0 = time.monotonic()
    while time.monotonic() - t0 < seconds:
        chunk = ser.read(4096)
        if chunk:
            buf = parse_frames(buf + chunk, frames, resyncs)
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="COM10")
    ap.add_argument("--calib", default="coinft_calib.json")
    args = ap.parse_args()

    calib = json.loads(Path(args.calib).read_text(encoding="utf-8"))
    A = np.array(calib["matrix_24x6"])

    ser = serial.Serial(args.port, 115200, timeout=0.1)
    ser.write(b"i")
    time.sleep(0.2)

    print("去皮中，请勿触碰传感器（1 秒）...")
    tare_frames = collect(ser, 1.0)
    tare = np.array(tare_frames).mean(axis=0)
    print("开始输出 Fx Fy Fz (N) | Mx My Mz (N·m)，Ctrl+C 停止\n")

    try:
        while True:
            frames = collect(ser, 0.1)
            if not frames:
                continue
            x = np.array(frames).mean(axis=0) - tare
            ft = np.concatenate([x, x ** 2]) @ A
            print(f"F: {ft[0]:+7.3f} {ft[1]:+7.3f} {ft[2]:+7.3f} N   "
                  f"M: {ft[3]:+7.4f} {ft[4]:+7.4f} {ft[5]:+7.4f} N·m",
                  end="\r")
    except KeyboardInterrupt:
        pass
    finally:
        ser.write(b"i")
        ser.close()
        print("\n已停止")


if __name__ == "__main__":
    main()
