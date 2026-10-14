"""Capture one operator-held pose from the CoinFT demo HTTP state endpoint."""

import argparse
import json
import math
import time
import urllib.request
from datetime import datetime
from pathlib import Path


def valid_state(state, previous_frame):
    return not invalid_reasons(state, previous_frame)


def invalid_reasons(state, previous_frame):
    if not isinstance(state, dict):
        return ["state is not an object"]
    reasons = []
    if state.get("status") != "live":
        reasons.append(f"status={state.get('status')!r}")
    frame = state.get("frames")
    if not isinstance(frame, int):
        reasons.append(f"frame is not an integer: {frame!r}")
    elif frame <= previous_frame:
        reasons.append(f"frame not increasing: previous={previous_frame}, current={frame}")
    rate = state.get("rate")
    if not isinstance(rate, (int, float)) or not math.isfinite(rate) or rate <= 0:
        reasons.append(f"rate is not finite and positive: {rate!r}")
    for name in ("invalid_recent", "saturated_recent"):
        if state.get(name) != 0:
            reasons.append(f"{name}={state.get(name)!r}")
    resyncs = state.get("resyncs")
    if type(resyncs) is not int or resyncs < 0:
        reasons.append(f"resyncs is not a nonnegative integer: {resyncs!r}")
    for name in ("channels", "raw"):
        values = state.get(name)
        if not isinstance(values, list) or len(values) != 12:
            reasons.append(f"{name} is not a 12-element list")
        else:
            for index, value in enumerate(values):
                if not isinstance(value, (int, float)) or not math.isfinite(value):
                    reasons.append(f"{name}[{index}] is not finite: {value!r}")
    return reasons


def capture(url: str, pose: str, assembly_id: str, seconds: float, interval: float) -> dict:
    if not all(math.isfinite(value) and value > 0 for value in (seconds, interval)):
        raise ValueError("seconds and interval must be finite and positive")

    samples = []
    previous_frame = -1
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        started = time.monotonic()
        with urllib.request.urlopen(f"{url.rstrip('/')}/api/state", timeout=1.5) as response:
            state = json.load(response)
        if not valid_state(state, previous_frame):
            raise ValueError(f"unsafe state during {pose}: {'; '.join(invalid_reasons(state, previous_frame))}")
        previous_frame = state["frames"]
        samples.append({
            "host": datetime.now().astimezone().isoformat(),
            "f": previous_frame,
            "channels": state["channels"],
            "raw": state["raw"],
            "status": state["status"],
            "rate": state["rate"],
            "invalid": state["invalid_recent"],
            "saturated": state["saturated_recent"],
            "resync": state["resyncs"],
        })
        elapsed = time.monotonic() - started
        time.sleep(max(0, interval - elapsed))

    if len(samples) < 30:
        raise ValueError(f"too few distinct snapshots: {len(samples)} < 30")
    return {
        "pose": pose,
        "assemblyId": assembly_id,
        "source": url,
        "sample_kind": "http_snapshot",
        "samples": samples,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pose", required=True, help="one stable operator-held pose name")
    parser.add_argument("--assembly-id", required=True, help="current physical assembly label")
    parser.add_argument("--out", required=True, type=Path, help="new evidence JSON path")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--interval", type=float, default=0.125)
    args = parser.parse_args(argv)

    if args.out.exists():
        raise FileExistsError(args.out)
    evidence = capture(args.url, args.pose, args.assembly_id, args.seconds, args.interval)
    if args.out.exists():
        raise FileExistsError(args.out)
    content = json.dumps(evidence, ensure_ascii=False, indent=2)
    with args.out.open("x", encoding="utf-8") as output:
        output.write(content)
    samples = evidence["samples"]
    print(f"{args.pose}: {len(samples)} HTTP snapshots; frames {samples[0]['f']}..{samples[-1]['f']}; "
          f"rate {samples[-1]['rate']}; invalid {samples[-1]['invalid']}; "
          f"saturated {samples[-1]['saturated']}; resync {samples[-1]['resync']}")


if __name__ == "__main__":
    main()
