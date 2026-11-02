"""Builds the DIBELS progress monitoring dataset for Tableau.

    python -m apm_metrics.build_dibels [--as-of YYYY-MM-DD]

Inputs  (config/paths.yaml): PowerSchool CC roster, DIBELS benchmark (BM), DIBELS progress monitoring (PM),
        testing calendar (windows + checkpoints per level).
Outputs (config/paths.yaml output_dir/tableau):
        dibels_student_window.csv  one row per tracked student per window for that student's level
        dibels_students.csv        every K-5 student on the roster, with level and whether they are tracked
        dibels_checkpoints.csv     the calendar's checkpoints, long
        data_quality.xlsx          issues found while building (output_dir)

Rules live in docs/dibels_tracking_logic.md.
"""

import argparse
import sys
from datetime import date
from pathlib import Path

if __package__ in (None, ""):                      # lets the editor's play button run this file directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from apm_metrics.utils import config, data_loader, dictionary, guide, quality
from apm_metrics.utils.roster import load_roster

BM_ID = PM_ID = "Student Primary ID (studentNumber)"

# Demographics come from the benchmark export (every tracked student has a benchmark row).
DEMOGRAPHICS = {"Gender": "gender", "Race": "race", "Hispanic or Latino Ethnicity": "hispanic_latino",
                "Special Education": "special_education", "IEP Status": "iep_status", "ELL Status": "ell_status"}
DEMO_COLS = list(DEMOGRAPHICS.values())

# Probe-level fields from the progress monitoring export, renamed for Tableau.
PROBE_FIELDS = {"PM Period": "pm_period", "Measure": "measure", "Probe Number": "probe_number", "Total Number of Probes": "total_probes",
                "Score": "score", "Aimline Status": "aimline_status", "Aimline Value By Date": "aimline_value_by_date",
                "Growth Goal Set": "growth_goal_set", "Assessing Teacher Name": "assessing_teacher"}
PROBE_NUMBERS = ["probe_number", "total_probes", "score", "aimline_value_by_date", "growth_goal_set"]
PM_PERIOD_LABELS = {"BOY->MOY": "BOY", "MOY->EOY": "MOY", "After EOY": "EOY"}


def aimline_rule(statuses: pd.Series) -> str:
    """One aimline status for a student on a probe date. A probe date can have several measures; if ANY is Below the
    aimline the student is 'Below'; else 'At or Above' if any measure is; else 'Not available'."""
    values = set(statuses)
    if "Below" in values:
        return "Below"
    return "At or Above" if "At or Above" in values else "Not available"


def load_calendar() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    path = config.source_dir("calendar") / config.paths()["calendar_file"]
    if not path.exists():
        raise SystemExit(f"Calendar not found: {path}")
    windows = pd.read_excel(path, sheet_name="Windows")
    checkpoints = pd.read_excel(path, sheet_name="Checkpoints")
    settings = pd.read_excel(path, sheet_name="Settings").set_index("setting")["value"].to_dict()
    for col in ("start_date", "end_date"):
        windows[col] = pd.to_datetime(windows[col])
    checkpoints["checkpoint_date"] = pd.to_datetime(checkpoints["checkpoint_date"])
    return windows, checkpoints, settings


def load_benchmark() -> pd.DataFrame:
    cfg = config.paths()["dibels"]
    pattern = data_loader.export_pattern("bm", cfg["school_year"], cfg["benchmark_period"])
    path = data_loader.latest_file(config.source_dir("dibels"), pattern, "dibels_bm")
    if path is None:
        raise SystemExit("No benchmark file found.")
    bm = data_loader.read_any(path)
    bm["grade"] = data_loader.norm_grade(bm["Enrollment Grade"])
    bm = data_loader.keep_k5(bm, "grade", "dibels_bm")
    level = bm["Composite Level"].str.replace("Benchmark", "", regex=False).str.strip()
    bm["level"] = level.where(level != "", "Not scored")
    dup = bm[BM_ID].duplicated(keep=False)
    if dup.any():
        quality.add("Student twice in benchmark", "The row with a benchmark level is used. Students: "
                    + quality.sample_ids(bm.loc[dup, BM_ID]), source="dibels_bm", count=int(bm.loc[dup, BM_ID].nunique()))
        # keep the row that has a level (a scored benchmark beats a partial / not-started duplicate)
        bm = bm.sort_values("level", key=lambda s: s == "Not scored").drop_duplicates(BM_ID, keep="first")
    print(f"Benchmark: {path.name}")
    bm = bm.rename(columns={BM_ID: "student_id", "Completion Status": "benchmark_status", **DEMOGRAPHICS})
    for col in DEMOGRAPHICS.values():           # blank or 'No Value Provided' -> one clear label for Tableau filters
        bm[col] = bm[col].str.strip().replace({"": "Not reported", "No Value Provided": "Not reported"})
    return bm[["student_id", "level", "benchmark_status", *DEMOGRAPHICS.values()]]


def load_pm() -> tuple[pd.DataFrame, pd.Timestamp, pd.DataFrame]:
    cfg = config.paths()["dibels"]
    paths = data_loader.all_files(config.source_dir("dibels"), data_loader.export_pattern("pm", cfg["school_year"]), "dibels_pm")
    if not paths:
        raise SystemExit("No progress monitoring file found.")
    # Every PM export for the school year is combined (oldest to newest). A probe that appears in more than one
    # export is kept once, from the NEWEST export (its aimline and goal fields are the most up to date).
    frames = []
    for order, path in enumerate(paths):
        f = data_loader.read_any(path)
        f["_file_order"] = order
        frames.append(f)
    pm = pd.concat(frames, ignore_index=True)
    pm["grade"] = data_loader.norm_grade(pm["Enrollment Grade"])
    pm = data_loader.keep_k5(pm, "grade", "dibels_pm")
    pm["probe_date"] = data_loader.to_datetime(pm["Device Date"].str[:10]).dt.normalize()
    bad = pm["probe_date"].isna()
    if bad.any():
        quality.add("Probe with no usable date", "Skipped.", source="dibels_pm", count=int(bad.sum()))
        pm = pm[~bad]
    n_before = len(pm)
    pm = (pm.sort_values("_file_order")
            .drop_duplicates([PM_ID, "Measure", "probe_date", "PM Period", "Probe Number"], keep="last")
            .reset_index(drop=True))
    if len(paths) > 1:
        quality.add("Progress monitoring files combined", f"{len(paths)} files; {n_before - len(pm)} duplicate rows removed "
                    "(newest export wins).", source="dibels_pm", count=len(paths))
    # one probe can produce several rows (e.g. Decoding + Letter Sounds), so count distinct dates per student
    days = pm[[PM_ID, "probe_date"]].drop_duplicates().rename(columns={PM_ID: "student_id"})
    # one row per measure per probe, with the score and aimline fields (for the student detail page)
    detail = pm.rename(columns={PM_ID: "student_id", **PROBE_FIELDS})[["student_id", "probe_date", *PROBE_FIELDS.values()]].copy()
    for col in PROBE_NUMBERS:
        detail[col] = pd.to_numeric(detail[col], errors="coerce")
    detail["aimline_status"] = detail["aimline_status"].str.strip().replace("", "Not available")
    # Amplify's PM period -> the benchmark that starts it (anything unexpected is kept as it came)
    detail["pm_period"] = detail["pm_period"].str.strip().replace(PM_PERIOD_LABELS)
    print(f"Progress monitoring: {len(paths)} file(s), {len(pm)} rows after removing duplicates  "
          f"(latest probe {days['probe_date'].max().date()})")
    return days, days["probe_date"].max(), detail


def window_context(windows: pd.DataFrame, checkpoints: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """Per level+window: state as of today and the checkpoint a team is being compared to."""
    rows = []
    for w in windows.itertuples():
        state = "Closed" if as_of > w.end_date else ("Current" if as_of >= w.start_date else "Upcoming")
        cps = checkpoints[(checkpoints["level"] == w.level) & (checkpoints["window_id"] == w.window_id)]
        passed = cps[cps["checkpoint_date"] <= as_of].sort_values("checkpoint_date")
        if state == "Closed":
            label, cdate, target = "Window closed", w.end_date, w.final_target_pct
        elif state == "Upcoming" or passed.empty:
            label, cdate, target = "Window opens", w.start_date, 0
        else:
            last = passed.iloc[-1]
            label, cdate, target = last["label"], last["checkpoint_date"], last["target_pct_tested"]
        row = {"level": w.level, "window_id": w.window_id, "window_state": state,
               "current_checkpoint_label": label, "current_checkpoint_date": cdate,
               "current_target_pct": target}
        upcoming = cps[cps["checkpoint_date"] > as_of].sort_values("checkpoint_date")
        nxt = upcoming.iloc[0] if state == "Current" and not upcoming.empty else None
        row["next_checkpoint_label"] = nxt["label"] if nxt is not None else ""
        row["next_checkpoint_date"] = nxt["checkpoint_date"] if nxt is not None else pd.NaT
        row["next_target_pct"] = nxt["target_pct_tested"] if nxt is not None else pd.NA
        # every checkpoint of the window, wide, so the dashboard's checkpoint strip needs only this file
        for i, c in enumerate(cps.sort_values("checkpoint_date").itertuples(), 1):
            row[f"cp{i}_label"], row[f"cp{i}_date"], row[f"cp{i}_target_pct"] = c.label, c.checkpoint_date, c.target_pct_tested
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", help="Treat this date as today (YYYY-MM-DD). Default: today.")
    args = ap.parse_args()
    as_of = pd.Timestamp(args.as_of or date.today())

    roster, roster_date = load_roster()
    bm = load_benchmark()
    days, last_probe, probe_detail = load_pm()
    windows, checkpoints, settings = load_calendar()
    min_probes = int(settings.get("tested_rule_min_probes", 1))
    tracked_levels = set(config.rules()["tracked_levels"])
    school_year = config.paths()["dibels"]["school_year"]
    print(f"Roster: {len(roster)} K-5 students as of {roster_date.date()}; as-of date {as_of.date()}")

    # who is tracked
    students = roster.merge(bm, on="student_id", how="left")
    students["level"] = students["level"].fillna("No benchmark")
    students["benchmark_status"] = students["benchmark_status"].fillna("No record")
    students[DEMO_COLS] = students[DEMO_COLS].fillna("Not reported")
    students["tracked"] = students["level"].isin(tracked_levels)
    for lvl, why in (("No benchmark", "Enrolled but no fall benchmark record - needs benchmarking or checking"),
                     ("Not scored", "Benchmark Partial or Not Started - level unknown until finished")):
        n = students[students["level"] == lvl]
        if len(n):
            by = ", ".join(f"{k}: {v}" for k, v in n["benchmark_status"].value_counts().items())
            quality.add(f"Students with level '{lvl}'", f"{why} ({by}). Students: " + quality.sample_ids(n["student_id"]),
                        source="dibels_bm", count=len(n))
    off_roster_bm = set(bm["student_id"]) - set(roster["student_id"])
    transferred = off_roster_bm & config.verified_transfers()
    if transferred:
        quality.add("Transferred out (verified in PowerSchool)", "Took the BOY benchmark, then transferred out. "
                    "Not on the roster; do not count against the teacher.", source="dibels_bm", count=len(transferred))
    off_roster_bm -= transferred
    if off_roster_bm:
        quality.add("In benchmark but not on current roster", "Not verified as transferred out - check PowerSchool. "
                    "Students: " + quality.sample_ids(off_roster_bm), source="dibels_bm", count=len(off_roster_bm))
    off_roster_pm = set(days["student_id"]) - set(roster["student_id"])
    if off_roster_pm:
        quality.add("Progress monitored but not on current roster", "Not counted. Students: "
                    + quality.sample_ids(off_roster_pm), source="dibels_pm", count=len(off_roster_pm))

    # student x window
    sw = students[students["tracked"]].merge(windows, on="level")
    sw = sw.merge(days, on="student_id", how="left")
    in_win = sw["probe_date"].between(sw["start_date"], sw["end_date"])
    keys = ["student_id", "level", "window_id"]
    probes = sw[in_win].groupby(keys)["probe_date"].agg(probes_in_window="nunique", last_probe_date="max").reset_index()
    sw = sw.drop(columns="probe_date").drop_duplicates(keys).merge(probes, on=keys, how="left")
    sw["probes_in_window"] = sw["probes_in_window"].fillna(0).astype(int)
    sw["tested"] = (sw["probes_in_window"] >= min_probes).astype(int)
    sw = sw.merge(window_context(windows, checkpoints, as_of), on=["level", "window_id"])
    sw["assessment"] = "DIBELS PM"
    sw["school_year"] = school_year
    sw["as_of_date"] = as_of.date()                      # "today" for this run; window states are computed from it
    sw["data_as_of"] = last_probe.date()
    sw["roster_as_of"] = roster_date.date()
    cols = ["school_year", "assessment", "level", "window_id", "window_label", "start_date", "end_date",
            "window_state", "current_checkpoint_label", "current_checkpoint_date", "current_target_pct",
            "next_checkpoint_label", "next_checkpoint_date", "next_target_pct",
            "cp1_label", "cp1_date", "cp1_target_pct", "cp2_label", "cp2_date", "cp2_target_pct",
            "cp3_label", "cp3_date", "cp3_target_pct", "cp4_label", "cp4_date", "cp4_target_pct",
            "final_target_pct", "grade", "teacher", "homeroom", "student_id", "student_name", "student_name_last_first",
            *DEMO_COLS,
            "probes_in_window", "tested", "last_probe_date", "as_of_date", "data_as_of", "roster_as_of"]
    sw = sw[cols].sort_values(["level", "window_id", "grade", "teacher", "student_name"])

    # probe detail: one row per measure per probe for tracked students (student detail page)
    info = students.loc[students["tracked"], ["student_id", "student_name", "student_name_last_first", "grade", "teacher",
                                              "level", *DEMO_COLS]]
    pr = probe_detail.merge(info, on="student_id")               # tracked students only
    pr["_row"] = range(len(pr))
    hit = pr.merge(windows[["level", "window_id", "window_label", "start_date", "end_date"]], on="level")
    hit = hit[hit["probe_date"].between(hit["start_date"], hit["end_date"])][["_row", "window_id", "window_label"]]
    pr = pr.merge(hit, on="_row", how="left")                    # a probe outside every window keeps a blank window
    outside = pr["window_id"].isna().sum()
    if outside:
        quality.add("Probes outside every window", "Kept in the probe file with a blank window.", source="dibels_pm",
                    count=int(outside))
    pr["school_year"] = school_year
    pr_cols = ["school_year", "level", "window_id", "window_label", "grade", "teacher", "student_id", "student_name",
               "student_name_last_first",
               "probe_date", "pm_period", "measure", "probe_number", "total_probes", "score", "aimline_status",
               "aimline_value_by_date", "growth_goal_set", "assessing_teacher", *DEMO_COLS]
    pr = pr[pr_cols].sort_values(["teacher", "student_name", "measure", "probe_number"])

    # aimline status per student (latest probe overall) and per student-window (latest probe in that window).
    #     One value per row, so the row count of the main file does not change. ---
    n_rows = len(sw)
    latest = probe_detail[probe_detail["probe_date"] == probe_detail.groupby("student_id")["probe_date"].transform("max")]
    sw["latest_probe_date"] = sw["student_id"].map(probe_detail.groupby("student_id")["probe_date"].max())
    sw["latest_aimline_status"] = (sw["student_id"].map(latest.groupby("student_id")["aimline_status"].agg(aimline_rule))
                                   .fillna("No probes"))
    pw = pr.dropna(subset=["window_id"]).copy()
    pw["window_id"] = pw["window_id"].astype(int)
    lw = pw[pw["probe_date"] == pw.groupby(["student_id", "level", "window_id"])["probe_date"].transform("max")]
    wstat = (lw.groupby(["student_id", "level", "window_id"])["aimline_status"].agg(aimline_rule)
             .rename("window_aimline_status").reset_index())
    sw = sw.merge(wstat, on=["student_id", "level", "window_id"], how="left")
    sw["window_aimline_status"] = sw["window_aimline_status"].fillna("No probe")
    assert len(sw) == n_rows, "aimline merge changed the number of rows"

    # write
    out = config.output_dir() / "tableau"
    out.mkdir(parents=True, exist_ok=True)
    sw.to_csv(out / "dibels_student_window.csv", index=False)
    history = config.output_dir() / "history"            # dated copy of every run (same-day runs overwrite)
    history.mkdir(parents=True, exist_ok=True)
    sw.to_csv(history / f"dibels_student_window_{as_of.date()}.csv", index=False)
    students.to_csv(out / "dibels_students.csv", index=False)
    checkpoints.to_csv(out / "dibels_checkpoints.csv", index=False)
    pr.to_csv(out / "dibels_probes.csv", index=False)
    dictionary.write_all(config.output_dir(), {dictionary.MAIN: sw, dictionary.STUDENTS: students,
                                               dictionary.CPS: checkpoints, dictionary.PROBES: pr})
    guide.write(config.output_dir(), windows, checkpoints, settings, as_of, last_probe, config.school_name())
    with pd.ExcelWriter(config.output_dir() / "data_quality.xlsx") as xl:
        quality.frame().to_excel(xl, sheet_name="Issues", index=False)
    print(f"Wrote {len(sw)} student-window rows to {out}")

    # quick check on screen
    cur = sw[sw["window_state"].isin(["Current", "Closed"])]
    summary = (cur.groupby(["level", "window_label", "window_state", "grade"])["tested"]
               .agg(tested="sum", students="count").assign(pct=lambda d: (100 * d["tested"] / d["students"]).round(0)))
    print(summary.to_string())
    print(f"\nIssues logged: {len(quality.frame())} (see data_quality.xlsx)")


if __name__ == "__main__":
    main()
