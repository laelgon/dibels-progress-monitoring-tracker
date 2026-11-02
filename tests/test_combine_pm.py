"""Checks that several progress monitoring exports are combined and duplicate probes removed (newest export wins).

    python tests/test_combine_pm.py

Builds two small fake PM exports in a temporary folder (no real student data), points the pipeline at it, and checks
the result. Prints PASS / FAIL per check; exits non-zero on any failure.
"""

import sys
import tempfile
from pathlib import Path
from unittest import mock

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apm_metrics import build_dibels as b  # noqa: E402
from apm_metrics.utils import config  # noqa: E402

COLS = ["Student Primary ID (studentNumber)", "Enrollment Grade", "Device Date", "PM Period", "Measure", "Probe Number",
        "Total Number of Probes", "Score", "Aimline Status", "Aimline Value By Date", "Growth Goal Set",
        "Assessing Teacher Name"]


def row(sid, date, period, probe, score, status, total="2"):
    return [sid, "2", date, period, "Decoding (NWF-WRC)", probe, total, score, status, "5", "13", "Teacher, A"]


old = pd.DataFrame([row("1", "9/25/2026", "BOY->MOY", "1", "3", "Below"),
                    row("1", "10/8/2026", "BOY->MOY", "2", "5", "Below"),
                    row("2", "9/25/2026", "BOY->MOY", "1", "7", "At or Above")], columns=COLS)
new = pd.DataFrame([row("1", "10/8/2026", "BOY->MOY", "2", "5", "At or Above", total="3"),   # same probe, updated aimline
                    row("1", "1/20/2027", "MOY->EOY", "1", "9", "At or Above", total="1"),  # next period: probe number restarts
                    row("3", "1/21/2027", "MOY->EOY", "1", "2", "Below", total="1")], columns=COLS)

fails = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"  - {detail}" if detail else ""))
    if not ok:
        fails.append(name)


sy = config.paths()["dibels"]["school_year"]
sy_short = f"{sy[:4]}-{sy[-2:]}"


def load_with(old_name, new_name, extra=None):
    """Writes the two fake exports under the given names (plus an optional extra copy), and loads them through the pipeline."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        old.to_csv(tmp / old_name, index=False)
        new.to_csv(tmp / new_name, index=False)
        if extra:
            old.to_csv(tmp / extra, index=False)
        real = config.source_dir
        with mock.patch.object(config, "source_dir", lambda name: tmp if name == "dibels" else real(name)):
            return b.load_pm()


# Old names (dibels8_PM_...), the pattern used before the rename
days, last, detail = load_with(f"dibels8_PM_{sy}_BOY-MOY_grades-K-5_2026-10-21_11-00-00.csv",
                               f"dibels8_PM_{sy}_MOY-EOY_grades-K-5_2027-01-22_09-00-00.csv")
# New names (dibels_pm_...): same files, renamed
days_n, last_n, detail_n = load_with(f"dibels_pm_{sy_short}_boy-moy_2026-10-21_1100.csv", f"dibels_pm_{sy_short}_moy-eoy_2027-01-22_0900.csv")
# Mid-rename: one file under its old name, one under its new name, and a leftover old copy of the first (same probes twice)
days_m, last_m, detail_m = load_with(f"dibels8_PM_{sy}_BOY-MOY_grades-K-5_2026-10-21_11-00-00.csv", f"dibels_pm_{sy_short}_moy-eoy_2027-01-22_0900.csv",
                                     extra=f"dibels_pm_{sy_short}_boy-moy_2026-10-21_1100.csv")

key = ["student_id", "probe_date", "pm_period", "probe_number", "score", "aimline_status", "total_probes"]
check("New names give the same result as old names", detail_n[key].reset_index(drop=True).equals(detail[key].reset_index(drop=True)))
check("Mixed old and new names give the same result as old names", detail_m[key].reset_index(drop=True).equals(detail[key].reset_index(drop=True)))
check("A file present under both its old and new name is not counted twice", len(detail_m) == len(detail))

check("Both files are read (6 rows in, 5 distinct probes out)", len(detail) == 5, f"{len(detail)} rows")
dup = detail[(detail.student_id == "1") & (detail.probe_date == "2026-10-08")]
check("A probe in both files appears once", len(dup) == 1)
check("...and keeps the NEWEST export's values (aimline At or Above, total 3)",
      dup.iloc[0].aimline_status == "At or Above" and dup.iloc[0].total_probes == 3)
check("The same probe number in a different period is kept (probe numbers restart per period)",
      len(detail[(detail.student_id == "1") & (detail.pm_period == "MOY")]) == 1)
check("Periods are labeled BOY / MOY (from BOY->MOY / MOY->EOY)", set(detail.pm_period) == {"BOY", "MOY"}, str(set(detail.pm_period)))
check("A student only in the newer file is included", "3" in set(detail.student_id))
check("A student only in the older file is kept", "2" in set(detail.student_id))
check("Latest probe date is the newest across files", str(last.date()) == "2027-01-21", str(last.date()))
print(f"\n{len(fails)} check(s) failed" if fails else "\nAll checks passed")
sys.exit(1 if fails else 0)
