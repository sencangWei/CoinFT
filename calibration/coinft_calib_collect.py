"""Interactive CoinFT calibration data collector (DIY, no ATI sensor).

Run this yourself in a terminal (needs keyboard input):

    D:/conda/python.exe coinft_calib_collect.py --port COM10

For each pose in poses.csv it prints what to set up, waits for Enter,
records --seconds of data, and appends rows (pose_id, ch1..ch12) to the
output CSV. Finish all poses, then hand the output to coinft_calib_fit.py.

NOTE: Teensy firmware already sends the tuning table at power-up, so this
script does NOT send tuning. If you reflash/change tuning, power-cycle the
Teensy before collecting.
"""
import argparse
import csv
import struct
import sys
import time
from pathlib import Path

import serial

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from coinft_acceptance import parse_frames  # noqa: E402

POSES_CSV = Path(__file__).with_name("poses.csv")
SATURATION = 33782


def load_poses(path=POSES_CSV):
    with open(path, encoding="utf-8") as f:
        lines = [l for l in f if not l.startswith("#")]
    rows = csv.DictReader(lines)
    return [r for r in rows if r["pose_id"].strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="COM10")
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--poses", default=str(POSES_CSV), help="姿态表 CSV（默认 poses.csv）")
    ap.add_argument("--out", default=f"calib_raw_{time.strftime('%Y%m%d')}.csv")
    args = ap.parse_args()

    poses = load_poses(args.poses)
    print(f"共 {len(poses)} 个姿态，每个采 {args.seconds} 秒。")
    print("先把传感器基准面调水平，在壳体上标出 +X/+Y 方向再开始。\n")

    ser = serial.Serial(args.port, 115200, timeout=0.1)
    ser.reset_input_buffer()
    ser.write(b"i")
    time.sleep(0.2)

    out_path = Path(args.out)
    header = ["pose_id", "mass_actual_g"] + [f"ch{k}" for k in range(1, 13)]
    if out_path.exists():
        first = open(out_path, encoding="utf-8").readline().strip()
        if first != ",".join(header):
            sys.exit(f"{out_path} 是旧格式（无 mass_actual_g 列），请先改名/删除再运行")
        with open(out_path, encoding="utf-8") as f_chk:
            done = {r["pose_id"] for r in csv.DictReader(f_chk)}
        f_out = open(out_path, "a", newline="")
    else:
        done = set()
        f_out = open(out_path, "w", newline="")
    writer = csv.writer(f_out)
    if out_path.stat().st_size == 0:
        writer.writerow(header)
    if done:
        print(f"已完成 {len(done)} 个姿态，将自动跳过: {sorted(done)}\n")

    try:
        idx = 0
        while idx < len(poses):
            pose = poses[idx]
            if pose["pose_id"] in done:
                idx += 1
                continue
            print(f"[{idx+1}/{len(poses)}] 姿态 {pose['pose_id']}: "
                  f"{describe(pose)}")
            mass = float(pose["mass_g"])
            skip = False
            if mass > 0:
                while True:
                    m_in = input(f"  实际载荷多少克? [回车={mass:g}, s=跳过]: ").strip()
                    if m_in.lower() == "s":
                        skip = True
                        break
                    if not m_in:
                        break
                    try:
                        mass = float(m_in)
                        break
                    except ValueError:
                        print("  !! 只认数字 / 回车 / s")
            while not skip:
                go = input("  摆好后保持静止，按 Enter 开始采集... (s=跳过本姿态): ").strip()
                if go == "":
                    break
                if go.lower() == "s":
                    skip = True
                    break
                print("  !! 只认 回车=开始 / s=跳过")
            if skip:
                idx += 1
                continue
            while True:  # USB 掉线自动重连重采本姿态
                try:
                    ser.reset_input_buffer()
                    ser.write(b"s")
                    frames, resyncs = [], [0]
                    buf = b""
                    t0 = time.monotonic()
                    while time.monotonic() - t0 < args.seconds:
                        chunk = ser.read(4096)
                        if chunk:
                            buf = parse_frames(buf + chunk, frames, resyncs)
                    ser.write(b"i")
                    break
                except serial.SerialException:
                    print("  !! USB 断开，3 秒后自动重连重采本姿态...")
                    try:
                        ser.close()
                    except Exception:
                        pass
                    time.sleep(3)
                    for _ in range(15):
                        try:
                            ser = serial.Serial(args.port, 115200, timeout=0.1)
                            break
                        except serial.SerialException:
                            time.sleep(2)
                    else:
                        raise
                    print("  重连成功，保持姿势别动，重新采集")

            n = len(frames)
            sat = sum(1 for fr in frames for v in fr if v >= SATURATION)
            print(f"  收到 {n} 帧 ({n/args.seconds:.0f} Hz), "
                  f"错位 {resyncs[0]}, 饱和样本 {sat}")
            bad = None
            if n < args.seconds * 150:
                bad = "帧数不足，检查连接"
            elif sat:
                bad = "有饱和，请减小载荷"
            if bad:
                print(f"  !! {bad}")
                if input("  输入 r 重测本姿态，其他键跳过: ").strip() == "r":
                    continue  # retry same pose
                idx += 1
                continue
            for fr in frames:
                writer.writerow([pose["pose_id"], f"{mass:g}", *fr])
            f_out.flush()
            idx += 1
    except KeyboardInterrupt:
        print("\n中断，已采集的数据已保存。")
    except serial.SerialException as e:
        print(f"\n!! USB 断开 ({e})，已采数据已保存。")
        print("   修复连接后重新运行，会自动跳过已采姿态。")
    finally:
        try:
            ser.write(b"i")
            ser.close()
        except Exception:
            pass
        f_out.close()
    print(f"完成 -> {out_path}")


def describe(p):
    """note 列就是完整的摆法说明，直接打印。"""
    note = (p["note"] or "").strip()
    if note:
        return note
    return f"{p['type']} 角度={p['angle_deg']} 载荷={p['mass_g']}g (无说明, 检查 poses.csv)"


if __name__ == "__main__":
    main()
