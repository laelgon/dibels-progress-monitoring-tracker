"""Builds an example testing_calendar.xlsx: the windows, checkpoints and settings the pipeline needs.

    python tools/make_example_calendar.py [--start 2026-09-01] [--out data/calendar/testing_calendar.xlsx]

Defaults: Well Below students are monitored in 2-week windows (8 of them) and Below students in 4-week windows (4 of them),
starting on --start. Each window has four checkpoints (the share of students that should be tested by then): 40, 70, 90 and
95 percent. These percentages are placeholders; edit the Excel file (or the numbers below) to match your school's calendar,
including breaks and holidays.

Sheets: Windows, Checkpoints, Settings (the same columns the pipeline reads).
"""
import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ASSESSMENT = "DIBELS PM"
LEVELS = {"Well Below": (14, 8), "Below": (28, 4)}                # level: (days per window, number of windows)
# checkpoint: (label, day of the window, target percent tested). Day 1 is the first day of the window.
CHECKPOINTS = {
    14: [("Check 1", 4, 40), ("Check 2", 8, 70), ("Pre-deadline checkpoint", 11, 90), ("Window closes", 14, 95)],
    28: [("Check 1", 7, 40), ("Check 2", 15, 70), ("Pre-deadline checkpoint", 22, 90), ("Window closes", 28, 95)],
}
FINAL_TARGET = 95


def build(start: date):
    windows, checkpoints = [], []
    for level, (days, count) in LEVELS.items():
        for i in range(count):
            begin = start + timedelta(days=i * days)
            end = begin + timedelta(days=days - 1)
            windows.append({"assessment": ASSESSMENT, "level": level, "window_id": i + 1, "window_label": f"{level} window {i + 1}",
                            "start_date": begin, "end_date": end, "final_target_pct": FINAL_TARGET, "notes": ""})
            for label, day, pct in CHECKPOINTS[days]:
                checkpoints.append({"assessment": ASSESSMENT, "level": level, "window_id": i + 1,
                                    "checkpoint_date": begin + timedelta(days=day - 1), "label": label, "target_pct_tested": pct,
                                    "notes": "PLACEHOLDER: adjust for breaks and holidays"})
    settings = pd.DataFrame([
        ("tested_rule_min_probes", 1, "A student is tested in a window with at least this many probes dated in it"),
        ("behind_points", 15, "Under the current checkpoint target by up to this many points = Behind; more = Off track"),
        ("final_target_pct", FINAL_TARGET, "Default end-of-window target"),
        ("grades", "K,1,2,3,4,5", "Grades included"),
        ("levels_tracked", "Well Below,Below", "From the fall benchmark composite level")], columns=["setting", "value", "meaning"])
    return pd.DataFrame(windows), pd.DataFrame(checkpoints), settings


def write(out: Path, start: date) -> Path:
    windows, checkpoints, settings = build(start)
    out.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out) as xl:
        windows.to_excel(xl, sheet_name="Windows", index=False)
        checkpoints.to_excel(xl, sheet_name="Checkpoints", index=False)
        settings.to_excel(xl, sheet_name="Settings", index=False)
    return out


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-09-01", help="first day of window 1 (YYYY-MM-DD)")
    ap.add_argument("--out", default=str(root / "data" / "calendar" / "testing_calendar.xlsx"))
    a = ap.parse_args()
    print(f"Wrote {write(Path(a.out), date.fromisoformat(a.start))}")
