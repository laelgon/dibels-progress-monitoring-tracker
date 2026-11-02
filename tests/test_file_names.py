"""Checks that raw export file names are recognized in BOTH the old and the new naming pattern.

    python tests/test_file_names.py

New pattern:  source_schoolyear_window_pulldate[_HHMM].ext   e.g. dibels_pm_2026-27_boy-moy_2026-10-26_1333.csv
Uses only file NAMES (no real files). Prints PASS / FAIL per check; exits non-zero on any failure.
"""

import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apm_metrics.utils import data_loader as dl  # noqa: E402

SY = "2026-2027"
# (kind, old name, new name, pull date and time)
PAIRS = [
    ("cc", "cc-9.28.26.text", "powerschool_cc_2026-27_boy_2026-09-28.text", datetime(2026, 9, 28)),
    ("cc", "cc-10.21.26.txt", "powerschool_cc_2026-27_boy_2026-10-21.txt", datetime(2026, 10, 21)),
    ("bm25", "dibels8_BM_2025-2026_BOY_MOY_EOY_grades-KG-01-02-03-04-05-06-07-08_2026-09-09_11-23-33.csv",
     "dibels_bm_2025-26_all_2026-09-09_1123.csv", datetime(2026, 9, 9, 11, 23)),
    ("bm", "dibels8_BM_2026-2027_BOY_grades-KG-01-02-03-04-05-06-07-08_2026-09-09_11-21-05.csv",
     "dibels_bm_2026-27_boy_2026-09-09_1121.csv", datetime(2026, 9, 9, 11, 21)),
    ("bm", "dibels8_BM_2026-2027_BOY_grades-KG-01-02-03-04-05_2026-10-21_12-40-32.csv",
     "dibels_bm_2026-27_boy_2026-10-21_1240.csv", datetime(2026, 10, 21, 12, 40)),
    ("pm", "dibels8_PM_2026-2027_BOY-MOY_grades-KG-01-02-03-04-05-06-07-08_2026-10-21_11-09-37.csv",
     "dibels_pm_2026-27_boy-moy_2026-10-21_1109.csv", datetime(2026, 10, 21, 11, 9)),
    ("pm", "dibels8_PM_2026-2027_BOY-MOY_grades-KG-01-02-03-04-05_2026-10-26_13-33-55.csv",
     "dibels_pm_2026-27_boy-moy_2026-10-26_1333.csv", datetime(2026, 10, 26, 13, 33)),
    ("pm", "dibels8_PM_2026-2027_BOY-MOY_grades-KG-01-02-03-04-05_2026-10-26_13-38-44.csv",
     "dibels_pm_2026-27_boy-moy_2026-10-26_1338.csv", datetime(2026, 10, 26, 13, 38)),
]
PATTERNS = {"cc": dl.export_pattern("cc"), "bm": dl.export_pattern("bm", SY, "BOY"), "pm": dl.export_pattern("pm", SY)}

fails = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"  - {detail}" if detail else ""))
    if not ok:
        fails.append(name)


for kind, old, new, when in PAIRS:
    for label, name in (("old", old), ("new", new)):
        matched = {k for k, pat in PATTERNS.items() if re.search(pat, name, re.I)}
        want = set() if kind == "bm25" else {kind}
        check(f"{label} name matches only {sorted(want) or 'nothing'}: {name[:60]}", matched == want, str(sorted(matched)))
    s_old, s_new = dl._export_stamp(Path(old)), dl._export_stamp(Path(new))
    check(f"pull date agrees (old vs new): {new}", s_old.date() == s_new.date() == when.date(), f"{s_old} vs {s_new}")
    if kind != "cc":                                                 # DIBELS names carry a time: seconds are dropped in the new names
        check(f"pull time agrees to the minute: {new}", (s_old.hour, s_old.minute) == (s_new.hour, s_new.minute) == (when.hour, when.minute))

# Sorting by pull date and time puts the two files pulled minutes apart in the right order, in either pattern
pm_new = [p for k, _, p, _ in PAIRS if k == "pm"]
pm_old = [o for k, o, _, _ in PAIRS if k == "pm"]
check("PM files sort oldest to newest by pull date and time (new names)", sorted(pm_new, key=lambda n: dl._export_stamp(Path(n))) == pm_new)
check("PM files sort oldest to newest by pull date and time (old names)", sorted(pm_old, key=lambda n: dl._export_stamp(Path(n))) == pm_old)
# Old and new names for the same pull mixed together still order correctly
mixed = [pm_new[1], pm_old[0], pm_old[2], pm_new[0]]
check("Mixed old and new names sort by pull date and time",
      [dl._export_stamp(Path(n)).strftime("%m-%d %H:%M") for n in sorted(mixed, key=lambda n: dl._export_stamp(Path(n)))] ==
      ["10-21 11:09", "10-21 11:09", "10-26 13:33", "10-26 13:38"])
# Other school year / window must not match
check("BM for another school year is not picked up", not re.search(PATTERNS["bm"], "dibels_bm_2025-26_boy_2025-09-09_1121.csv", re.I))
check("BM for another window (moy) is not picked up as BOY", not re.search(PATTERNS["bm"], "dibels_bm_2026-27_moy_2027-01-12_0900.csv", re.I))
check("A boy-moy BM export counts as a BOY export (like the old names)", bool(re.search(PATTERNS["bm"], "dibels_bm_2026-27_boy-moy_2027-01-12_0900.csv", re.I)))
check("PM for another school year is not picked up", not re.search(PATTERNS["pm"], "dibels_pm_2025-26_all_2026-05-20_0900.csv", re.I))
check("Pull date without a time is read as midnight", dl._export_stamp(Path("powerschool_cc_2026-27_boy_2026-10-21.txt")) == datetime(2026, 10, 21))

print(f"\n{len(fails)} check(s) failed" if fails else "\nAll checks passed")
sys.exit(1 if fails else 0)
