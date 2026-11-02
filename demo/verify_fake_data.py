"""Checks the fake datasets: documented columns, nothing real in them, and that they look right.

    python demo/verify_fake_data.py

Real values are only used if you set real_data folders in demo_config.yaml (or the DEMO_REAL_* environment variables); they are
built in memory and never printed. SCAN_EXTRA_WORDS (comma-separated, for example your organization's name) adds a text search.
Prints PASS / FAIL per check; exit code 1 if any check fails.
"""
import os
import re
import sys

import pandas as pd

import settings

settings.use_pipeline_code()
import scan_workbook_for_real_data as scanner  # noqa: E402
from apm_metrics.utils import dictionary  # noqa: E402

FAKE = settings.OUT_DIR
FILES = ["dibels_student_window.csv", "dibels_probes.csv", "dibels_students.csv", "dibels_checkpoints.csv"]
fails = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"  - {detail}" if detail else ""))
    if not ok:
        fails.append(name)


have_real = bool(settings.real_data_folders())
names, teachers, ids = scanner.real_sets() if have_real else (set(), set(), set())
real_last = {n.split(", ")[0] for n in names if ", " in n}


def overlaps(df):
    n = 0
    for c in df.columns:
        if c == "student_id":
            n += len(set(df[c]) & ids)
        if c in ("teacher", "assessing_teacher"):
            n += len({v.strip().lower() for v in df[c]} & teachers)
        if c.startswith("student_name"):
            n += len({v.strip().lower() for v in df[c]} & names)
        if c == "student_name":
            n += len({v.split(" ")[-1].lower() for v in df[c]} & real_last)
    return n


for f in FILES:
    df = pd.read_csv(FAKE / f, dtype=str, keep_default_na=False)
    documented = [r[2] for r in dictionary.ROWS if r[0] == f]
    check(f"{f}: columns match the data dictionary ({len(df.columns)} columns, {len(df)} rows)", set(df.columns) == set(documented))
    if have_real:
        check(f"{f}: no real student ids, names or teachers", overlaps(df) == 0)

hist = sorted((FAKE / "history").glob("*.csv"))
if have_real:
    for h in hist:
        check(f"history/{h.name}: nothing real", overlaps(pd.read_csv(h, dtype=str, keep_default_na=False)) == 0)
else:
    print("SKIP  real-data overlap checks: set real_data folders in demo/demo_config.yaml to run them")

w = pd.read_csv(FAKE / "dibels_student_window.csv", dtype=str, keep_default_na=False)
p = pd.read_csv(FAKE / "dibels_probes.csv", dtype=str, keep_default_na=False)
check("every student id starts with FAKE-", w["student_id"].str.startswith("FAKE-").all() and p["student_id"].str.startswith("FAKE-").all())
check("every student name looks fake (<word> FAKE###)", w["student_name"].str.match(r"^[A-Za-z]+ FAKE\d{3}$").all())
check("every teacher starts with FakeTeacher-", w["teacher"].str.startswith("FakeTeacher-").all())
words = [x.strip() for x in os.environ.get("SCAN_EXTRA_WORDS", "").split(",") if x.strip()]
if words:        # your organization's names are passed at run time (they are not stored in this project)
    pattern = "|".join(re.escape(x) for x in words)
    check(f"none of the {len(words)} extra words (SCAN_EXTRA_WORDS) appear in any file", not any(
        re.search(pattern, (FAKE / f).read_text(encoding="utf-8", errors="ignore"), re.I) for f in FILES))
else:
    print("SKIP  extra-word check: set SCAN_EXTRA_WORDS (comma-separated, for example your organization's name) to also look for it")
check("probe students are all tracked students", set(p["student_id"]) <= set(w["student_id"]))
check("history has one file per snapshot", len(hist) == len(settings.CFG["snapshots"]), f"{len(hist)} files")
check("current data is the last snapshot", w["as_of_date"].iloc[0] == settings.CFG["snapshots"][-1], w["as_of_date"].iloc[0])

# what the grade bars will look like: the dashboard's own status rule, applied to each grade
BEHIND_POINTS, FINAL = 15, 95
COLOR = {"Met target": "green", "On track": "green", "Behind": "amber", "Off track": "red", "Missed target": "red", "Not started": "gray"}


def status(pct, state, target):
    if state == "Closed":
        return "Met target" if pct >= FINAL else "Missed target"
    if state == "Upcoming" or target == 0:
        return "Not started"
    return "On track" if pct >= target else ("Behind" if target - pct <= BEHIND_POINTS else "Off track")


w["tested"] = w["tested"].astype(int)
w["window_id"] = w["window_id"].astype(int)
print()
current = {}
for level in ("Well Below", "Below"):
    cur = w[(w["level"] == level) & (w["window_state"] == "Current")]
    target = float(cur["current_target_pct"].iloc[0])
    by_grade = cur.groupby("grade")["tested"].mean().mul(100)
    stat = {g: status(v, "Current", target) for g, v in by_grade.items()}
    current[level] = {COLOR[s] for s in stat.values()}
    print(f"      {level} current window ({cur['window_label'].iloc[0]}), checkpoint target {target:.0f}%: "
          + ", ".join(f"{g} {v:.0f}% {stat[g]}" for g, v in sorted(by_grade.items())))
check("Well Below current window (the default view) shows green, amber and red grade bars", current["Well Below"] >= {"green", "amber", "red"},
      str(sorted(current["Well Below"])))
for level in ("Well Below", "Below"):
    first = w[(w["level"] == level) & (w["window_id"] == 1)]
    check(f"{level} window 1 has data ({int(first['tested'].sum())} of {len(first)} students tested)", first["tested"].sum() > 0)
closed = w[(w["level"] == "Well Below") & (w["window_state"] == "Closed")]
mix = {}
for wid, g in closed.groupby("window_id"):
    by_grade = g.groupby("grade")["tested"].mean().mul(100)
    mix[wid] = (int((by_grade >= FINAL).sum()), int((by_grade < FINAL).sum()))
print("      Well Below closed windows, grades that Met / Missed the 95% target:", {k: f"{a} / {b}" for k, (a, b) in mix.items()})
check("closed windows show both Met and Missed grades (not all one color)", any(a > 0 and b > 0 for a, b in mix.values()))
latest_probe = pd.to_datetime(p["probe_date"]).max()
check("fake data runs up to the current point in time, and not past it", pd.Timestamp(w["data_as_of"].iloc[0]) == latest_probe <= pd.Timestamp(w["as_of_date"].iloc[0]),
      f"latest probe {latest_probe.date()}, as of {w['as_of_date'].iloc[0]}")

print(f"\n{len(fails)} check(s) failed" if fails else "\nAll checks passed")
sys.exit(1 if fails else 0)
