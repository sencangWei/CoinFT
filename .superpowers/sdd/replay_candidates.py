import csv
from pathlib import Path
from statistics import median

for path in (Path("calibration")).rglob("*.csv"):
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.reader(source)
        first = next(reader, [])
        if all(f"CH{i}" in first for i in range(1, 13)):
            indices = [first.index(f"CH{i}") for i in range(1, 13)]
        elif len(first) == 12:
            indices = list(range(12))
            reader = iter([first] + list(reader))
        else:
            continue
        for row in reader:
            try:
                rows.append([int(float(row[i])) for i in indices])
            except (ValueError, IndexError):
                continue
    if len(rows) < 401:
        continue
    baseline = [median(row[i] for row in rows[:400]) for i in range(12)]
    levels = [median(abs(row[i] - baseline[i]) for i in range(12)) for row in rows[400:]]
    peak = max(levels)
    if peak >= 100:
        print(f"{path}: {len(rows)} rows, peak median delta {peak:.0f} counts")
