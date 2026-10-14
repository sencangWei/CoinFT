import csv
from pathlib import Path
from statistics import median

path = Path("calibration/continuous_433g_thin_insulator_transition_20260911.csv")
with path.open(newline="", encoding="utf-8-sig") as source:
    reader = csv.DictReader(source)
    rows = list(reader)
baseline = [median(int(float(row[f"CH{i}"])) for row in rows[:400]) for i in range(1, 13)]
levels = [median(abs(int(float(row[f"CH{i}"])) - baseline[i - 1])
                 for i in range(1, 13)) for row in rows]
peak = max(range(len(levels)), key=levels.__getitem__)
for cutoff in (100, 200, 700):
    count = sum(value >= cutoff for value in levels)
    print(f">={cutoff} counts: {count}/{len(levels)} ({count / len(levels):.1%})")
print(f"peak index {peak}, phase {rows[peak].get('phase')}, median delta {levels[peak]}")
phases = {}
for i, row in enumerate(rows):
    phase = row.get("phase")
    phases.setdefault(phase, []).append(levels[i])
for phase, samples in phases.items():
    print(f"{phase}: {len(samples)} rows, median {median(samples):.0f}, max {max(samples):.0f}")

selected = []
for phase in ("idle_before", "load_stable", "idle_after"):
    selected.extend(row for row in rows if row.get("phase") == phase)
out = Path(".superpowers/sdd/real_433g_replay.csv")
with out.open("w", newline="", encoding="utf-8") as destination:
    writer = csv.writer(destination)
    for row in selected:
        writer.writerow([row[f"CH{i}"] for i in range(1, 13)])
print(f"derived replay: {out}, {len(selected)} raw frames")
