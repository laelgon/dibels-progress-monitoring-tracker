"""Builds a COMPLETELY FAKE copy of the Tableau datasets, for a public Tableau Public demo.

    python demo/make_fake_data.py [--raw]

Nothing real goes in. Names are "<NATO word> FAKE###", ids are FAKE-####, teachers are FakeTeacher-<grade><letter>; every score,
demographic and probe is random (fixed seed, so a rerun gives the same files). It writes fake raw exports (roster, benchmark,
progress monitoring) in the same formats as the real exports, runs them through this project's pipeline (apm_metrics) in a scratch
folder, so every column and rule matches what the dashboards expect, and copies only the Tableau CSVs to the output folder.

History: the pipeline is run for several "today" dates (demo_config.yaml snapshots), each seeing only the probes made by then, and
the dated copies are kept in <output>/history like the real pipeline does. The last date is the current data.

--raw also leaves the newest fake raw exports in data/raw/, so you can try the whole pipeline end to end:
    python -m apm_metrics.build_dibels --as-of 2026-11-02
    python tests/verify_dibels.py
(data/raw/ and output/ are ignored by git.) The testing calendar is data/calendar/testing_calendar.xlsx; it is created from
tools/make_example_calendar.py when missing. It is a schedule, not student data.
"""
import argparse
import random
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

import settings

settings.use_pipeline_code()
from apm_metrics import build_dibels as b  # noqa: E402
from apm_metrics.utils import config  # noqa: E402

CFG, OUT_DIR = settings.CFG, settings.OUT_DIR
SNAPSHOTS = CFG["snapshots"]
LAST_PROBE = date.fromisoformat(CFG["last_probe"])
SEED = CFG["seed"]
FIRST_PROBE = date(2026, 9, 1)            # window 1 has data too
BREAK = {date(2026, 9, 7)} | {date(2026, 11, 23) + timedelta(days=i) for i in range(5)}     # Labor Day and Thanksgiving week
PERIOD_START, PERIOD_END = date(2026, 9, 1), date(2027, 1, 15)

NATO = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India", "Juliet", "Kilo", "Lima", "Mike",
        "November", "Oscar", "Papa", "Quebec", "Romeo", "Sierra", "Tango", "Uniform", "Victor", "Whiskey", "Xray", "Yankee", "Zulu"]
GRADES = ["K", "1", "2", "3", "4", "5"]
LETTERS = ["A", "B", "C"]
PER_CLASS = 20
# Chance a tracked student is tested in a CLOSED window, by grade, so some grades meet the 95% target in a window and others miss it.
GRADE_BASE = {"K": 0.97, "1": 0.89, "2": 0.93, "3": 0.80, "4": 0.96, "5": 0.86}
WINDOW1_FACTOR = 0.90        # a slower start in the first window
JITTER = 0.05                # each grade moves up or down a little from window to window
# The CURRENT window is judged against its checkpoint target, so each grade is placed this many points from that target:
# ahead = On track (green), up to 15 points behind = Behind (amber), more than 15 behind = Off track (red).
CURRENT_DELTA = {"K": 12, "1": 3, "2": -5, "3": -12, "4": -23, "5": -32}
CURRENT_DELTA_BELOW = {"K": 8, "1": -4, "2": -10, "3": -24, "4": 4, "5": -13}      # the Below level has tiny classes, so its own placement
# Each homeroom teacher is a little above or below their grade (18 teachers: K-A, K-B, K-C, 1-A, ...), so the teacher page varies too.
TEACHER_OFFSET = [0.05, -0.02, -0.08, 0.03, 0.00, -0.06, 0.04, -0.04, 0.01, -0.09, 0.02, 0.05, 0.00, -0.05, 0.03, 0.06, -0.07, -0.01]
MEASURES = {"K": ["Letter Sounds (NWF-CLS)", "Decoding (NWF-WRC)"], "1": ["Letter Sounds (NWF-CLS)", "Decoding (NWF-WRC)"],
            "2": ["Reading Fluency (ORF)", "Reading Accuracy (ORF-Accu)"], "3": ["Reading Fluency (ORF)", "Reading Accuracy (ORF-Accu)"],
            "4": ["Reading Fluency (ORF)", "Reading Accuracy (ORF-Accu)"], "5": ["Reading Fluency (ORF)", "Reading Accuracy (ORF-Accu)"]}
# measure: (starting score range, growth per probe, goal choices, aimline starts at this share of the goal, max score)
MODEL = {"Letter Sounds (NWF-CLS)": ((6, 30), 3.0, [39, 52, 63], 0.30, 137), "Decoding (NWF-WRC)": ((1, 9), 1.5, [13, 18, 30], 0.16, 60),
         "Reading Fluency (ORF)": ((20, 60), 4.5, [60, 77, 96, 111], 0.30, 160), "Reading Accuracy (ORF-Accu)": ((62, 92), 1.8, [90, 96], 0.70, 100)}
NO_AIMLINE_SHARE = 0.08                   # a few probes have no aimline status, as in the real exports
PM_HEAD = ["Student Primary ID (studentNumber)", "Enrollment Grade", "Device Date", "PM Period", "Measure", "Probe Number",
           "Total Number of Probes", "Score", "Aimline Status", "Aimline Value By Date", "Growth Goal Set", "Assessing Teacher Name"]


def us(d):
    return f"{d.month}/{d.day}/{d.year}"


def weekdays(lo, hi):
    days = [lo + timedelta(days=i) for i in range((hi - lo).days + 1)]
    return [d for d in days if d.weekday() < 5 and d not in BREAK]


def make_students(rng):
    students, i = [], 0
    for gi, g in enumerate(GRADES):
        for li, L in enumerate(LETTERS):
            teacher = f"FakeTeacher-{g}{L}, Demo"
            offset = TEACHER_OFFSET[gi * 3 + li]
            for _ in range(PER_CLASS):
                i += 1
                r = rng.random()
                level = "Well Below Benchmark" if r < 0.42 else "Below Benchmark" if r < 0.57 else "At Benchmark" if r < 0.82 else \
                    "Above Benchmark" if r < 0.98 else ""
                students.append({
                    "n": i, "id": f"FAKE-{i:04d}", "first": NATO[(i - 1) % 26], "last": f"FAKE{i:03d}", "grade": g, "letter": L,
                    "teacher": teacher, "offset": offset, "level_raw": level,
                    "status": "Complete" if level else rng.choice(["Partial", "Not Started"]),
                    "gender": rng.choice(["Female", "Male"]),
                    "race": rng.choices(["Black or African-American", "White", "American Indian or Alaska Native", "Asian",
                                         "Two or More Races", "No Value Provided"], [45, 26, 9, 5, 10, 5])[0],
                    "hispanic": rng.choices(["No", "Yes", "No Value Provided"], [78, 20, 2])[0],
                    "sped": rng.choices(["No Value Provided", "No", "Yes"], [80, 17, 3])[0],
                    "iep": rng.choices(["No", "Yes"], [88, 12])[0], "ell": rng.choices(["No", "Yes"], [88, 12])[0]})
    return students


def cc_rows(students):
    head = ["[01]Student_Number", "[01]Last_Name", "[01]First_Name", "[01]Grade_Level", "Course_Number", "[02]Course_Name",
            "Section_Number", "SectionID", "Expression", "[05]LastFirst", "DateEnrolled", "DateLeft"]
    rows = []
    for s in students:
        gl = "0" if s["grade"] == "K" else s["grade"]
        base = 9000 + s["n"] * 4
        sec = f"{s['grade']}{s['letter']}"
        for k, (cno, cname, suffix) in enumerate([(f"HR-{s['grade']}", "Homeroom", "HR"), (f"ELA-{s['grade']}", "English Language Arts", "ELA"),
                                                  (f"MATH-{s['grade']}", "Math", "MATH")]):
            rows.append([s["id"], s["last"], s["first"], gl, cno, cname, f"{sec}{suffix}", str(base + k), "1-6(A-E)", s["teacher"],
                         "8/10/2026", "5/27/2027"])
        rows.append([s["id"], s["last"], s["first"], gl, "HR-PRIOR", "Homeroom", "XHR", str(-(base + 3)), "1-6(A-E)", "FakeTeacher-Prior, Demo",
                     "8/10/2025", "5/28/2026"])                      # a past enrollment (negative section id), ignored by date
    return head, rows


def bm_rows(students):
    head = ["Student Primary ID (studentNumber)", "Enrollment Grade", "Composite Level", "Completion Status", "Gender", "Race",
            "Hispanic or Latino Ethnicity", "Special Education", "IEP Status", "ELL Status"]
    return head, [[s["id"], s["grade"], s["level_raw"], s["status"], s["gender"], s["race"], s["hispanic"], s["sped"], s["iep"], s["ell"]]
                  for s in students]


def make_probes(students, windows, ctx, rng):
    """Every fake probe up to LAST_PROBE as a DataFrame (one row per measure per probe); snapshots filter it by date.
    ctx = the window state and checkpoint target as of the final fake "today" (from the pipeline's calendar logic)."""
    rows = []
    span = (PERIOD_END - PERIOD_START).days
    drift = {}
    level_of = {"Well Below Benchmark": "Well Below", "Below Benchmark": "Below"}
    state = {(r.level, int(r.window_id)): (r.window_state, float(r.current_target_pct)) for r in ctx.itertuples()}

    # Who is tested in which window. The number tested in each class is set exactly (rate x class size), so each grade lands where
    # it was placed instead of drifting with random luck in small classes.
    classes = {}
    for s in students:
        if s["level_raw"] in level_of:
            lv = level_of[s["level_raw"]]
            # Well Below is set class by class; Below has only 2-3 students per class, so it is set grade by grade
            classes.setdefault((lv, s["teacher"] if lv == "Well Below" else f"grade {s['grade']}"), []).append(s)
    tested = set()                                               # (student id, level, window id)
    for level in ("Well Below", "Below"):
        for w in windows[windows["level"] == level].itertuples():
            key = (level, int(w.window_id))
            st, target = state[key]
            if st == "Upcoming" or not weekdays(max(w.start_date.date(), FIRST_PROBE), min(w.end_date.date(), LAST_PROBE)):
                continue
            for (lv, teacher), group in sorted(classes.items()):
                if lv != level:
                    continue
                grade = group[0]["grade"]
                if st == "Current":                              # placed relative to today's checkpoint target
                    rate = (target + (CURRENT_DELTA_BELOW if level == "Below" else CURRENT_DELTA)[grade]) / 100
                else:                                            # closed: the grade's usual rate, moved a little each window
                    rate = GRADE_BASE[grade] + drift.setdefault((key, grade), rng.uniform(-JITTER, JITTER))
                    rate *= WINDOW1_FACTOR if key[1] == 1 else 1.0
                p = min(1.0, max(0.03, rate + (group[0]["offset"] if level == "Well Below" else 0)))
                k = round(p * len(group))
                if k == 0 and p >= 0.05:                         # small classes: never show a grade at exactly 0% in a window with activity
                    k = 1
                for s in rng.sample(group, min(len(group), k)):
                    tested.add((s["id"], level, key[1]))

    for s in students:
        level = level_of.get(s["level_raw"])
        if not level:
            continue
        probe_days = []
        for w in windows[windows["level"] == level].itertuples():
            key = (level, int(w.window_id))
            if (s["id"], level, key[1]) not in tested:
                continue
            lo, hi = max(w.start_date.date(), FIRST_PROBE), min(w.end_date.date(), LAST_PROBE)
            days = weekdays(lo, hi)
            two = level == "Well Below" and state[key][0] == "Closed" and rng.random() < 0.25
            probe_days += sorted(rng.sample(days, min(len(days), 2 if two else 1)))
        probe_days = sorted(set(probe_days))
        if not probe_days:
            continue
        for measure in MEASURES[s["grade"]]:
            (lo_s, hi_s), slope, goals, aim_start, cap = MODEL[measure]
            goal = rng.choice(goals)
            score = rng.uniform(lo_s, hi_s) * (0.9 if level == "Well Below" else 1.2)
            aim0 = goal * aim_start
            for n, d in enumerate(probe_days, 1):
                score = max(0.0, min(cap, score + rng.gauss(slope, slope * 1.2) if n > 1 else score))
                aim = aim0 + (goal - aim0) * ((d - PERIOD_START).days / span)
                none = rng.random() < NO_AIMLINE_SHARE
                rows.append({"pdate": d, "pkey": (s["id"], measure), "id": s["id"], "grade": s["grade"], "measure": measure, "n": n,
                             "score": int(round(score)), "status": "" if none else ("At or Above" if round(score) >= round(aim) else "Below"),
                             "aim": "" if none else str(int(round(aim))), "goal": goal, "teacher": s["teacher"]})
    return pd.DataFrame(rows)


def pm_snapshot(probes, cutoff):
    """The PM export as of one date: only probes up to the cutoff, with the per-measure totals recounted."""
    p = probes[probes["pdate"] <= cutoff].copy()
    p["total"] = p.groupby("pkey")["n"].transform("count")
    rows = [[r.id, r.grade, us(r.pdate), "BOY->MOY", r.measure, str(r.n), str(r.total), str(r.score), r.status, r.aim, str(r.goal), r.teacher]
            for r in p.itertuples()]
    return PM_HEAD, rows


def write_csv(path, head, rows, sep):
    pd.DataFrame(rows, columns=head).to_csv(path, sep=sep, index=False, encoding="utf-8", lineterminator="\r\n")


def ensure_calendar():
    """Creates the example testing calendar when the project does not have one yet."""
    path = config.source_dir("calendar") / config.paths()["calendar_file"]
    if not path.exists():
        sys.path.insert(0, str(settings.ROOT / "tools"))
        import make_example_calendar
        make_example_calendar.write(path, date(2026, 9, 1))
        print(f"Created the example calendar {path}")


def main(raw=False):
    ensure_calendar()
    rng = random.Random(SEED)
    students = make_students(rng)
    windows, checkpoints, _ = b.load_calendar()                  # the schedule only (no student data)
    ctx = b.window_context(windows, checkpoints, pd.Timestamp(SNAPSHOTS[-1]))       # window states and checkpoint targets "today"
    probes = make_probes(students, windows, ctx, rng)
    tmp = Path(tempfile.mkdtemp(prefix="FAKE_apm_"))
    raw_dibels, raw_cc, out_scratch = tmp / "dibels", tmp / "cc", tmp / "out"
    for d in (raw_dibels, raw_cc, out_scratch):
        d.mkdir()
    write_csv(raw_dibels / "dibels_bm_2026-27_boy_2026-10-21_1240.csv", *bm_rows(students), sep=",")

    real_source = config.source_dir
    config.source_dir = lambda name: {"dibels": raw_dibels, "powerschool_cc": raw_cc}.get(name) or real_source(name)
    config.output_dir = lambda: out_scratch                      # the pipeline writes to a scratch folder, not to output/
    for as_of in SNAPSHOTS:                                      # oldest to newest, so the last run is the current data
        day = date.fromisoformat(as_of)
        for f in list(raw_cc.iterdir()) + [x for x in raw_dibels.iterdir() if "_pm_" in x.name]:
            f.unlink()
        write_csv(raw_cc / f"powerschool_cc_2026-27_boy_{as_of}.txt", *cc_rows(students), sep="\t")
        write_csv(raw_dibels / f"dibels_pm_2026-27_boy-moy_{as_of}_1338.csv", *pm_snapshot(probes, day - timedelta(days=3)), sep=",")
        sys.argv = ["build_dibels", "--as-of", as_of]
        print(f"\nSnapshot {as_of}")
        b.main()

    if raw:                                                      # leave the newest fake raw exports in data/raw/ for an end-to-end trial
        for src, dest in ((raw_dibels, real_source("dibels")), (raw_cc, real_source("powerschool_cc"))):
            dest.mkdir(parents=True, exist_ok=True)
            for f in src.iterdir():
                shutil.copy2(f, dest / f.name)
        print(f"\nFake raw exports copied to {real_source('dibels')} and {real_source('powerschool_cc')}")

    if OUT_DIR.exists():                                         # replace any earlier fake build (this folder only ever holds fake data)
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)
    names = ["dibels_student_window.csv", "dibels_probes.csv", "dibels_students.csv", "dibels_checkpoints.csv"]
    for n in names:
        shutil.copy2(out_scratch / "tableau" / n, OUT_DIR / n)
    (OUT_DIR / "history").mkdir()
    for f in sorted((out_scratch / "history").glob("dibels_student_window_*.csv")):
        shutil.copy2(f, OUT_DIR / "history" / f.name)
    (OUT_DIR / "README_FAKE_DATA.txt").write_text(
        "ALL DATA IN THIS FOLDER IS FAKE.\nStudents are named '<NATO word> FAKE###' with ids FAKE-####; teachers are FakeTeacher-<grade><letter>.\n"
        "Scores, probes, levels and demographics are random. Window dates and checkpoint targets come from the testing calendar (a schedule).\n"
        f"Current data: 'today' is {SNAPSHOTS[-1]}. history/ holds the dated copies for {', '.join(SNAPSHOTS)}.\n"
        "Built by demo/make_fake_data.py with a fixed seed.\n", encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)                       # scratch copies (roster, benchmark, PM, dictionary, guide) are deleted
    print(f"\nWrote {', '.join(names)} and history/ to {OUT_DIR}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", action="store_true", help="also leave the newest fake raw exports in data/raw/")
    main(ap.parse_args().raw)
