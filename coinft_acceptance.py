"""CoinFT acceptance capture via Teensy bridge.

Usage:
  python coinft_acceptance.py --port COM10 --tune --seconds 5 --out baseline.csv
  python coinft_acceptance.py --port COM10 --tune --seconds 20 --out dynamic.csv

Teensy frame: 0x00 0x00 + 24 payload bytes = 12 x uint16 little-endian.
Tuning: 5-byte command  t + ch(0-based) + res + ref + comp  (runtime only,
lost on CoinFT power cycle -> always send before measuring).
"""
import argparse
import csv
import struct
import sys
import time

import serial

# Board-2 candidate tuning table (from 2026-09 tuning session, see PROJECT_LOG.md)
TUNING = [
    (12, 50, 50), (12, 30, 72), (12, 30, 81), (12, 30, 82),
    (12, 30, 83), (12, 30, 85), (12, 30, 76), (12, 30, 75),
    (12, 100, 17), (12, 100, 26), (12, 80, 58), (12, 80, 42),
]
SATURATION = 33782  # observed plateau value 0x83F6


def parse_frames(buf, frames, resyncs):
    """Extract confirmed 26-byte frames; return leftover tail."""
    i = 0
    n = len(buf)
    while True:
        j = buf.find(b"\x00\x00", i, n - 1)
        if j < 0:
            return buf[max(0, n - 27):]
        if j + 28 > n:
            return buf[j:]
        if buf[j + 26:j + 28] == b"\x00\x00":
            payload = buf[j + 2:j + 26]
            frames.append(struct.unpack("<12H", payload))
            i = j + 26
        else:
            resyncs[0] += 1
            i = j + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="COM10")
    ap.add_argument("--seconds", type=float, default=5)
    ap.add_argument("--tune", action="store_true")
    ap.add_argument("--out", default="capture.csv")
    args = ap.parse_args()

    ser = serial.Serial(args.port, 115200, timeout=0.1)
    ser.reset_input_buffer()
    ser.write(b"i")
    time.sleep(0.2)
    ser.reset_input_buffer()

    if args.tune:
        for ch, (res, ref, comp) in enumerate(TUNING):
            ser.write(struct.pack("BBbbb", ord("t"), ch, res, ref, comp))
            time.sleep(0.05)
        time.sleep(0.5)
        print("tuning sent (12 ch)")

    ser.write(b"s")
    frames, resyncs = [], [0]
    buf = b""
    t0 = time.monotonic()
    while time.monotonic() - t0 < args.seconds:
        chunk = ser.read(4096)
        if chunk:
            buf = parse_frames(buf + chunk, frames, resyncs)
    ser.write(b"i")
    elapsed = time.monotonic() - t0
    ser.close()

    n = len(frames)
    print(f"frames={n}  elapsed={elapsed:.2f}s  rate={n/elapsed:.1f} Hz  resyncs={resyncs[0]}")

    if n < 10:
        print("FAIL: too few frames")
        sys.exit(1)

    with open(args.out, "w", newline="") as f:
        csv.writer(f).writerows(frames)

    cols = list(zip(*frames))
    print("ch   median  p1     p99    min    max    sat_count  distinct")
    all_ok = True
    for k, c in enumerate(cols):
        s = sorted(c)
        med = s[len(s) // 2]
        p1 = s[max(0, int(len(s) * 0.01))]
        p99 = s[min(len(s) - 1, int(len(s) * 0.99))]
        sat = sum(1 for v in c if v >= SATURATION)
        distinct = len(set(c))
        flag = ""
        if sat > 0:
            flag = " SAT!"
            all_ok = False
        print(f"CH{k+1:<3} {med:6d}  {p1:6d} {p99:6d} {min(c):6d} {max(c):6d}  {sat:9d}  {distinct:8d}{flag}")

    print("SATURATION:", "NONE" if all_ok else "PRESENT")
    print(f"saved -> {args.out}")


if __name__ == "__main__":
    main()
