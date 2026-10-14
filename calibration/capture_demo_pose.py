"""Capture one operator-held pose from the CoinFT demo HTTP state endpoint."""

import argparse
import json
import math
import queue
import threading
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


def _request_state(url, started, deadline):
    result = queue.Queue(maxsize=1)

    def receive():
        try:
            if time.monotonic() >= min(deadline, started + 1.5):
                raise TimeoutError("HTTP state request admission deadline reached")
            with urllib.request.urlopen(url, timeout=1.5) as response:
                state = json.load(response)
            result.put((True, state))
        except Exception as error:
            result.put((False, error))

    threading.Thread(target=receive, daemon=True).start()
    try:
        success, value = result.get(timeout=max(0, started + 1.5 - time.monotonic()))
    except queue.Empty:
        raise TimeoutError("HTTP state request exceeded total 1.5 seconds") from None
    if time.monotonic() >= started + 1.5:
        raise TimeoutError("HTTP state request exceeded total 1.5 seconds")
    if not success:
        raise value
    return value


def capture(url: str, pose: str, assembly_id: str, seconds: float,
            interval: float, on_state=None, minimum_samples=None) -> dict:
    if not all(math.isfinite(value) and value > 0 for value in (seconds, interval)):
        raise ValueError("seconds and interval must be finite and positive")
    if minimum_samples is not None and (type(minimum_samples) is not int or minimum_samples < 30):
        raise ValueError("minimum_samples must be an integer >= 30")

    samples = []
    previous_frame = -1
    first_valid = None
    deadline = time.monotonic() + seconds + 1.0
    complete = False
    while time.monotonic() < deadline:
        started = time.monotonic()
        if started >= deadline:
            break
        state = _request_state(f"{url.rstrip('/')}/api/state", started, deadline)
        if on_state is not None:
            on_state(state)
        duplicate = (previous_frame >= 0 and isinstance(state, dict) and
                     state.get("frames") == previous_frame)
        validation_frame = previous_frame - 1 if duplicate else previous_frame
        if not valid_state(state, validation_frame):
            raise ValueError(f"unsafe state during {pose}: {'; '.join(invalid_reasons(state, validation_frame))}")
        if not duplicate:
            received = time.monotonic()
            if first_valid is None:
                first_valid = received
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
            host_span = (datetime.fromisoformat(samples[-1]["host"]) -
                         datetime.fromisoformat(samples[0]["host"])).total_seconds()
            if (received - first_valid >= seconds and host_span >= seconds and
                    (minimum_samples is None or len(samples) >= minimum_samples)):
                complete = True
                break
        time.sleep(min(max(0, interval - (time.monotonic() - started)),
                       max(0, deadline - time.monotonic())))

    if not complete:
        raise ValueError("capture deadline reached before valid sample span")
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
