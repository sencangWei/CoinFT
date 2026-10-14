### Task 3: Prepare bounded single-pose command, then collect fitting evidence

**Approved interval amendment (2026-09-28):** user approved changing only HTTP observation interval0.1s to0.125s. Preserve >=40 distinct snapshots/actual>=5s span, all quality and total-timeout checks; retain failed first attempt. Backend/firmware/serial settings remain unchanged. Mock success now approximately41 observations; preserve them all.

**Files:** eight new fit evidence JSON files; no production edits.

**Approved duplicate-snapshot amendment (2026-09-28):** user explicitly approved retaining healthy cached duplicate observations without counting them as samples. Preserve125ms pacing,6s request admission/1.5s total request timeout,all real-fault checks and40 distinct samples/actual5s requirement. Generic capture callers keep their original30-snapshot policy; add optional minimum_samples for the fitting command to wait for40 within the same existing deadline. Existing repeated-state valid_state predicate remains strict; only capture treats otherwise-healthy exact repeated frame as a cached non-sample. Never skip regression, malformed/nonfinite/invalid state or observer error. Diagnostics may hold for cached duplicate but never regress; fresh frames still require byte/parsed progress. No backend,firmware,serial,profile or UI change. This amendment overrides the original immediate-duplicate rejection in earlier reference code.


- [ ] Create evidence directories with apply_patch marker .keep files. Prepare the following Python command before asking for any pose. Set pose to the exact confirmed key and out to its fresh fitting/validation filename; do not run multiple poses automatically.
~~~python
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
            if state["diagnostics"][key] <= previous["diagnostics"][key]:
                raise ValueError("byte/frame observation not advancing")
        if (state["diagnostics"]["parser_discarded_bytes"] !=
                first["diagnostics"]["parser_discarded_bytes"]):
            raise ValueError("parser discarded bytes increased")

try:
    data = capture("http://127.0.0.1:8765", pose,
                   "coinft-current-20260925", 5.0, 0.125, on_state=observe)
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
~~~

This command emits complete compact JSON, not a file write. Use functions.exec store(toolResult) and output only exit/small metadata. Immediately notify the operator of completion/release; only then parse toolResult.output and persist full evidence through apply_patch. Allocate enough exec output budget for51 full states; do not print base data back to the chat. An owner preflight failure before capture is a setup failure; preserve its output too.

- [ ] Dry-run by using mock URL/time/owner inputs, not physical HTTP, to verify failed observations are retained and no HTTP POST/serial commands exist. Reuse Task1 successful/unsafe fixtures; callback rejection must abort immediately. Verify JSON serializes every observation (>=40 successful snapshots) and the selected out path is fresh.
- [ ] Request each physical state separately after prior window is saved; preserve chronological order:

| key | request |
|---|---|
| press_before | empty, hands/weights removed |
| press | center pure pressure, no additional shear |
| press_after | release, empty and settled |
| right_before | empty, unchanged fixture |
| right | upper relative to fixed lower PCB, −X / screen right |
| right_after | release, empty and settled |
| left_before | empty, unchanged fixture |
| left | upper relative to fixed lower PCB, +X / screen left |

On waiting/bad state/epoch change: stop that capture, notify release, retain failed evidence; never fit it. Do not ask harder force just to cross a threshold. Do not tare/reconnect to hide faults. Owner/epoch change invalidates the same-epoch input requirement and needs a separately agreed new acquisition sequence.

- [ ] Load eight successful files and fit/replay using actual code:
~~~python
import json
import statistics
from pathlib import Path
from calibration.shear_refit_replay import KEYS, fit_candidate, replay, passes
root = Path("calibration/shear_refit_20260928/fit")
windows = {k: json.loads((root/(k+".json")).read_text(encoding="utf-8")) for k in KEYS}
old = json.loads(Path("demo_web/shear_demo_profile.json").read_text(encoding="utf-8"))
baseline = [statistics.median(s["channels"][i] for s in windows["press_before"]["samples"])
            for i in range(12)]
candidate = fit_candidate(windows, old)
report = replay(candidate, old, windows, baseline)
print(json.dumps({"candidate": candidate, "baseline": baseline, "report": report,
                  "accepted": passes(report)}, ensure_ascii=False, allow_nan=False))
~~~
Persist full result with apply_patch to .superpowers/sdd/shear-refit-fitting-report-20260928.json; production profile remains unchanged. Build/replay failure is a stop condition, not permission to weaken gates.

- [ ] Review checkpoint: freeze candidate SHA256 and chosen baseline; no validation data has been captured or used to tune. No Git commit.
