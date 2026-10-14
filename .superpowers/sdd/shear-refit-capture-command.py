import json
import time
from datetime import datetime
from pathlib import Path
import psutil
from calibration.capture_demo_pose import capture

def owner():
    candidates = []
    for proc in psutil.process_iter(["pid", "create_time", "cmdline"]):
        args = proc.info["cmdline"] or []
        if any(Path(a).name == "coinft_demo.py" for a in args):
            candidates.append(proc.info)
    listeners = [c for c in psutil.net_connections(kind="tcp")
                 if c.status == psutil.CONN_LISTEN and c.laddr.port == 8765]
    if len(candidates) != 1 or len(listeners) != 1:
        raise ValueError("not exactly one HTTP capture owner")
    p = candidates[0]
    if listeners[0].pid != p["pid"]:
        raise ValueError("listener does not belong to capture owner")
    return {"pid": p["pid"], "created": p["create_time"]}

pose = "press_before"
out = Path("calibration/shear_refit_20260928/fit/press_before.json")
if out.exists():
    raise FileExistsError(out)
who = owner()
observations = []
def observe(state):
    observations.append({"host": datetime.now().astimezone().isoformat(),
                         "monotonic": time.monotonic(), "state": state})
    if state.get("port") != "COM6" or state.get("mode") != "live":
        raise ValueError("wrong port/mode")
    if state.get("tare_progress") != 100:
        raise ValueError("tare/baseline epoch not stable")
    if not state.get("diagnostics") or not state.get("recovery"):
        raise ValueError("missing stream quality evidence")
    if len(observations) > 1:
        first, previous = observations[0]["state"], observations[-2]["state"]
        for key in ("invalid_frames", "saturated", "resyncs"):
            if state[key] != first[key]:
                raise ValueError("new cumulative quality fault: "+key)
        for key in ("attempts", "successes"):
            if state["recovery"][key] != first["recovery"][key]:
                raise ValueError("stream recovery changed epoch")
        for key in ("serial_bytes", "parsed_frames"):
            if (state["diagnostics"][key] < previous["diagnostics"][key] or
                    (state["diagnostics"][key] == previous["diagnostics"][key] and
                     state["frames"] != previous["frames"])):
                raise ValueError("byte/frame observation not advancing")
        if (state["diagnostics"]["parser_discarded_bytes"] !=
                first["diagnostics"]["parser_discarded_bytes"]):
            raise ValueError("parser discarded bytes increased")

try:
    data = capture("http://127.0.0.1:8765", pose,
                   "coinft-current-20260925", 5.0, 0.125, on_state=observe, minimum_samples=40)
    if len(data["samples"]) < 40 or owner() != who:
        raise ValueError("insufficient samples or owner changed")
    a, b = observations[0], observations[-1]
    rate = (b["state"]["frames"]-a["state"]["frames"])/(b["monotonic"]-a["monotonic"])
    if not 150 <= rate <= 250:
        raise ValueError("aggregate frame rate outside150–250Hz")
    data.update(owner=who, evidence=out.name, observations=observations,
                aggregate_rate=rate, capture_ok=True)
    print(json.dumps({"out": str(out), "evidence": data},
                     ensure_ascii=False, allow_nan=False, separators=(",", ":")))
except Exception as exc:
    print(json.dumps({"out": str(out.with_suffix(".failed.json")),
                      "evidence": {"capture_ok": False, "pose": pose,
                                   "owner": who, "error": repr(exc),
                                   "observations": observations}},
                     ensure_ascii=False, separators=(",", ":")))
    raise SystemExit(1)
