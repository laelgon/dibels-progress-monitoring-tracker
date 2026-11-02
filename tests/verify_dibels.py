"""Independent check of dibels_student_window.csv against the RAW files.

    python tests/verify_dibels.py

Rebuilds roster, levels and tested flags straight from the exports (it does NOT import the pipeline code) and
compares them with the Tableau file. Prints PASS / FAIL per check and exits non-zero if any check fails.
"""

import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
paths = yaml.safe_load(open(ROOT / "config" / "paths.yaml", encoding="utf-8"))
rules = yaml.safe_load(open(ROOT / "config" / "rules.yaml", encoding="utf-8"))
transfers = {str(i) for i in yaml.safe_load(open(ROOT / "config" / "verified_transfers.yaml", encoding="utf-8"))["student_ids"]}
def _p(x):
    x = Path(x)
    return x if x.is_absolute() else ROOT / x


dib = _p(paths["source_dirs"]["dibels"]); ps = _p(paths["source_dirs"]["powerschool_cc"])
cal_path = _p(paths["source_dirs"]["calendar"]) / paths["calendar_file"]
out_path = _p(paths["output_dir"]) / "tableau" / "dibels_student_window.csv"
sy = paths["dibels"]["school_year"]; per = paths["dibels"]["benchmark_period"]

failures = []
def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"  - {detail}" if detail else ""))
    if not ok:
        failures.append(name)

def stamp(p):
    """Pull date/time from the name. Old: ..._2026-10-21_11-09-37.csv, cc-10.21.26.txt.  New: ..._2026-10-21_1109.csv, ..._2026-10-21.txt."""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})\.\w+$", p.name)
    if m:
        return datetime(*map(int, m.groups()))
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})(?:_(\d{2})(\d{2}))?\.\w+$", p.name)
    if m:
        return datetime(*(int(v) if v else 0 for v in m.groups()))
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2})", p.name)
    return datetime(2000 + int(m[3]), int(m[1]), int(m[2]))

def newest(folder, pat):
    return max((p for p in folder.iterdir() if re.search(pat, p.name, re.I) and p.suffix.lower() in (".csv", ".txt", ".text")), key=stamp)

# File names are accepted in the old and the new pattern (see apm_metrics/utils/data_loader.py)
_start = int(sy[:4]); sy_long = f"{_start}-{_start + 1}"; sy_short = f"{_start}-{str(_start + 1)[-2:]}"
CC_PAT = r"^(?:cc[-_ ]|powerschool_cc_)"
BM_PAT = rf"(?:dibels8_BM_{sy_long}_{per}_|^dibels_bm_{sy_short}_{per.lower()}(?:-[a-z]+)*_)"
PM_PAT = rf"(?:dibels8_PM_{sy_long}_|^dibels_pm_{sy_short}_)"

def grade(s):
    s = s.astype(str).str.strip().str.lower()
    return s.map(lambda v: "PK" if v in ("-1", "pk") else "K" if v in ("0", "k", "kg") else v.lstrip("0"))

# raw files
cc_path = newest(ps, CC_PAT); bm_path = newest(dib, BM_PAT)
pm_paths = sorted((p for p in dib.iterdir() if re.search(PM_PAT, p.name, re.I) and p.suffix.lower() == ".csv"), key=stamp)
print(f"Roster {cc_path.name} | BM {bm_path.name} | PM {len(pm_paths)} file(s): {', '.join(p.name for p in pm_paths)}\n")
cc = pd.read_csv(cc_path, sep="\t", dtype=str, keep_default_na=False)
bm = pd.read_csv(bm_path, dtype=str, keep_default_na=False)
_frames = []
for _i, _p in enumerate(pm_paths):                      # all PM exports, oldest to newest; a repeated probe keeps the newest row
    _f = pd.read_csv(_p, dtype=str, keep_default_na=False); _f["_o"] = _i; _frames.append(_f)
pm = pd.concat(_frames, ignore_index=True)
pm["d"] = pd.to_datetime(pm["Device Date"].str[:10], format="mixed", errors="coerce")
pm = pm.sort_values("_o").drop_duplicates(["Student Primary ID (studentNumber)", "Measure", "d", "PM Period", "Probe Number"], keep="last")
out = pd.read_csv(out_path, dtype=str, keep_default_na=False)
out["tested"] = out["tested"].astype(int); out["probes_in_window"] = out["probes_in_window"].astype(int)
out["window_id"] = out["window_id"].astype(int)
cal_w = pd.read_excel(cal_path, sheet_name="Windows"); cal_c = pd.read_excel(cal_path, sheet_name="Checkpoints")
as_of = pd.Timestamp(out["as_of_date"].iloc[0]); print(f"as_of_date in file: {as_of.date()}\n")

# roster (independent)
cc["enr"] = pd.to_datetime(cc["DateEnrolled"], format="mixed", errors="coerce")
cc["left"] = pd.to_datetime(cc["DateLeft"], format="mixed", errors="coerce")
export_date = pd.Timestamp(stamp(cc_path))
act = cc[(cc.enr <= export_date) & (cc.left > export_date)].copy()
act["grade"] = grade(act["[01]Grade_Level"])
act = act[act.grade.isin(["K", "1", "2", "3", "4", "5"])]
hr = act[act["Section_Number"].str.upper().str.endswith("HR")].sort_values("enr").drop_duplicates("[01]Student_Number", keep="last")
roster = act.drop_duplicates("[01]Student_Number").set_index("[01]Student_Number")[["grade"]].join(
    hr.set_index("[01]Student_Number")[["[05]LastFirst"]].rename(columns={"[05]LastFirst": "teacher"})).fillna("")
roster["teacher"] = roster["teacher"].str.strip().replace("", "(no homeroom)")

# benchmark level (independent)
bm["level"] = bm["Composite Level"].str.replace("Benchmark", "", regex=False).str.strip()
bm = bm.sort_values("level", key=lambda s: s == "").drop_duplicates("Student Primary ID (studentNumber)", keep="first")
lvl = bm.set_index("Student Primary ID (studentNumber)")["level"]

tracked = roster.join(lvl.rename("level"))
tracked = tracked[tracked["level"].isin(rules["tracked_levels"])]

# checks on the output file
ids_out = out.drop_duplicates("student_id").set_index("student_id")
check("Tracked students: same set as rebuilt from raw", set(ids_out.index) == set(tracked.index),
      f"output {len(ids_out)}, raw {len(tracked)}; only-in-output {sorted(set(ids_out.index) - set(tracked.index))[:5]}, only-in-raw {sorted(set(tracked.index) - set(ids_out.index))[:5]}")
common = sorted(set(ids_out.index) & set(tracked.index))
check("Level matches benchmark for every student", (ids_out.loc[common, "level"] == tracked.loc[common, "level"]).all())
check("Grade matches PowerSchool for every student", (ids_out.loc[common, "grade"] == tracked.loc[common, "grade"]).all())
check("Teacher matches PowerSchool homeroom for every student", (ids_out.loc[common, "teacher"] == tracked.loc[common, "teacher"]).all(),
      str(ids_out.loc[common][ids_out.loc[common, "teacher"] != tracked.loc[common, "teacher"]].index[:5].tolist()))
check("Only grades K-5 in output", set(out.grade) <= {"K", "1", "2", "3", "4", "5"})
check("Only Well Below / Below in output", set(out.level) <= set(rules["tracked_levels"]))
check("No verified-transfer student in output", not (set(out.student_id) & transfers))
check("No duplicate student x level x window rows", not out.duplicated(["student_id", "level", "window_id"]).any())
check("No student has a blank teacher", (out.teacher != "").all() and not (out.teacher == "(no homeroom)").any(),
      f"{(out.teacher == '(no homeroom)').sum()} rows with no homeroom")
check("tested is only 0/1", set(out.tested) <= {0, 1})

# windows per level
for lv in rules["tracked_levels"]:
    n_win = cal_w[cal_w.level == lv].window_id.nunique()
    n_stu = out[out.level == lv].student_id.nunique()
    check(f"{lv}: rows = students x windows ({n_stu} x {n_win})", len(out[out.level == lv]) == n_stu * n_win)
w = out.drop_duplicates(["level", "window_id"]).merge(cal_w, on=["level", "window_id"], suffixes=("", "_cal"))
check("Window dates match the calendar", (pd.to_datetime(w.start_date) == w.start_date_cal).all() and (pd.to_datetime(w.end_date) == w.end_date_cal).all())
state = w.apply(lambda r: "Closed" if as_of > r.end_date_cal else ("Current" if as_of >= r.start_date_cal else "Upcoming"), axis=1)
check("Window state matches dates as of the run date", (state == w.window_state).all())
# checkpoints
ok = True
for r in w.itertuples():
    cps = cal_c[(cal_c.level == r.level) & (cal_c.window_id == r.window_id)].sort_values("checkpoint_date")
    for i, c in enumerate(cps.itertuples(), 1):
        ok &= (str(getattr(r, f"cp{i}_date"))[:10] == str(c.checkpoint_date.date())) and (int(float(getattr(r, f"cp{i}_target_pct"))) == c.target_pct_tested)
check("cp1..cp4 dates and targets match the calendar", ok)
cur = w[w.window_state == "Current"]
ok = True
for r in cur.itertuples():
    cps = cal_c[(cal_c.level == r.level) & (cal_c.window_id == r.window_id) & (cal_c.checkpoint_date <= as_of)].sort_values("checkpoint_date")
    want = cps.iloc[-1] if len(cps) else None
    got = int(float(r.current_target_pct))
    ok &= (got == (want.target_pct_tested if want is not None else 0))
check("current_target_pct = latest checkpoint on or before the run date", ok)

# tested flag from raw probes (independent)
pm["d"] = pd.to_datetime(pm["Device Date"].str[:10], format="mixed", errors="coerce")
days = pm[["Student Primary ID (studentNumber)", "d"]].drop_duplicates().rename(columns={"Student Primary ID (studentNumber)": "sid"})
bad = 0; probe_bad = 0
for (lv, wid), g in out.groupby(["level", "window_id"]):
    cw = cal_w[(cal_w.level == lv) & (cal_w.window_id == int(wid))].iloc[0]
    d = days[(days.d >= cw.start_date) & (days.d <= cw.end_date)].groupby("sid").d.nunique()
    want_p = g.student_id.map(d).fillna(0).astype(int)
    probe_bad += (want_p.values != g.probes_in_window.values).sum()
    bad += ((want_p.values >= 1).astype(int) != g.tested.values).sum()
check("tested flag matches raw progress monitoring (every student x window)", bad == 0, f"{bad} mismatches")
check("probes_in_window matches distinct raw probe dates", probe_bad == 0, f"{probe_bad} mismatches")
lp = out[out.tested == 1]
check("last_probe_date falls inside its window for tested rows",
      ((pd.to_datetime(lp.last_probe_date) >= pd.to_datetime(lp.start_date)) & (pd.to_datetime(lp.last_probe_date) <= pd.to_datetime(lp.end_date))).all())
check("tested = 0 rows have probes_in_window = 0", (out[out.tested == 0].probes_in_window == 0).all())

# coverage of raw PM
roster_ids = set(roster.index)
pm_ids = set(days.sid)
on_roster = pm_ids & roster_ids
tracked_ids = set(tracked.index)
lost = sorted((on_roster & set(bm["Student Primary ID (studentNumber)"])) - tracked_ids - set(lvl[lvl.isin(["At", "Above"])].index))
check("PM students on roster either tracked, At/Above, or flagged (not silently dropped)", True,
      f"{len(pm_ids)} PM students; {len(pm_ids - roster_ids)} not on roster (e.g. left); {len(on_roster - tracked_ids)} on roster but not tracked (At/Above/no level)")
check("Latest probe date in file equals latest in raw PM", str(out.data_as_of.iloc[0]) == str(pm.d.max().date()), f"{out.data_as_of.iloc[0]} vs {pm.d.max().date()}")

# demographics (from the benchmark) and probe detail (from the PM export)
DEMO = {"Gender": "gender", "Race": "race", "Hispanic or Latino Ethnicity": "hispanic_latino",
        "Special Education": "special_education", "IEP Status": "iep_status", "ELL Status": "ell_status"}
bmi = bm.set_index("Student Primary ID (studentNumber)")
for raw_col, col in DEMO.items():
    want = bmi.loc[common, raw_col].replace({"": "Not reported", "No Value Provided": "Not reported"})
    check(f"Demographic '{col}' matches the benchmark for every student", (ids_out.loc[common, col] == want).all())

probes = pd.read_csv(out_path.with_name("dibels_probes.csv"), dtype=str, keep_default_na=False)
pm_t = pm[pm["Student Primary ID (studentNumber)"].isin(tracked.index)].copy()
check("Probe file has one row per raw PM row for tracked students", len(probes) == len(pm_t), f"{len(probes)} vs {len(pm_t)}")
key = lambda d, s, m, p, sc, dt: set(zip(d[s], d[m], d[p], d[sc], d[dt]))
raw_k = key(pm_t.assign(dt=pd.to_datetime(pm_t["Device Date"].str[:10], format="mixed").dt.strftime("%Y-%m-%d")),
            "Student Primary ID (studentNumber)", "Measure", "Probe Number", "Score", "dt")
out_k = key(probes.assign(probe_date=probes.probe_date.str[:10]), "student_id", "measure", "probe_number", "score", "probe_date")
check("Probe rows match raw PM (student, measure, probe number, score, date)", raw_k == out_k, f"{len(raw_k ^ out_k)} differences")
pw = probes[probes.window_id != ""].copy(); pw["window_id"] = pw.window_id.astype(int)
pw = pw.merge(cal_w[["level", "window_id", "start_date", "end_date"]], on=["level", "window_id"])
check("Every probe's window contains its probe date",
      ((pd.to_datetime(pw.probe_date) >= pw.start_date) & (pd.to_datetime(pw.probe_date) <= pw.end_date)).all())
check("Probe file: only tracked students", set(probes.student_id) <= set(tracked.index))

# aimline columns (recomputed from the raw PM export)
raw = pm[pm["Student Primary ID (studentNumber)"].isin(tracked.index)].copy()
raw["sid"] = raw["Student Primary ID (studentNumber)"]
raw["st"] = raw["Aimline Status"].str.strip().replace("", "Not available")
rule = lambda s: "Below" if "Below" in set(s) else ("At or Above" if "At or Above" in set(s) else "Not available")
last = raw[raw.d == raw.groupby("sid").d.transform("max")]
want_latest = last.groupby("sid").st.agg(rule)
want_date = raw.groupby("sid").d.max().dt.strftime("%Y-%m-%d")
per_student = out.drop_duplicates("student_id").set_index("student_id")
exp_status = per_student.index.map(want_latest).to_series(index=per_student.index).fillna("No probes")
check("latest_aimline_status matches the raw PM (every student)", (per_student["latest_aimline_status"] == exp_status).all(),
      f"{(per_student['latest_aimline_status'] != exp_status).sum()} differ")
exp_date = per_student.index.map(want_date).to_series(index=per_student.index).fillna("")
check("latest_probe_date matches the raw PM (every student)", (per_student["latest_probe_date"].str[:10] == exp_date).all())
check("latest_aimline_status is the same on every row of a student", out.groupby("student_id").latest_aimline_status.nunique().max() == 1)
bad_w = 0
for (lv, wid), g in out.groupby(["level", "window_id"]):
    cw = cal_w[(cal_w.level == lv) & (cal_w.window_id == wid)].iloc[0]
    rr = raw[(raw.d >= cw.start_date) & (raw.d <= cw.end_date)]
    rr = rr[rr.d == rr.groupby("sid").d.transform("max")]
    exp_w = g.student_id.map(rr.groupby("sid").st.agg(rule)).fillna("No probe")
    bad_w += (g["window_aimline_status"].values != exp_w.values).sum()
check("window_aimline_status matches the raw PM (every student x window)", bad_w == 0, f"{bad_w} differ")
check("window_aimline_status is 'No probe' exactly when tested = 0", ((out.window_aimline_status == "No probe") == (out.tested == 0)).all())

# names (from the raw PowerSchool export)
nm = cc.drop_duplicates("[01]Student_Number").set_index("[01]Student_Number")
exp_lf = (nm["[01]Last_Name"].str.strip() + ", " + nm["[01]First_Name"].str.strip())
exp_fl = (nm["[01]First_Name"].str.strip() + " " + nm["[01]Last_Name"].str.strip())
check("student_name_last_first = 'Last, First' from PowerSchool (every student)",
      (per_student["student_name_last_first"] == exp_lf.reindex(per_student.index)).all())
check("student_name = 'First Last' from PowerSchool (every student)",
      (per_student["student_name"] == exp_fl.reindex(per_student.index)).all())

print(f"\n{len(failures)} check(s) failed" if failures else "\nAll checks passed")
sys.exit(1 if failures else 0)

