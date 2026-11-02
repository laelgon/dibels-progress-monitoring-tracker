"""Data dictionary for the Tableau files: written as data_dictionary.csv and data_dictionary.html on every run.

Every column in every output file must be described here; the build stops if one is missing (or if a described
column no longer exists), so the dictionary can't drift away from the data.
"""

import html
from datetime import date

import pandas as pd

from apm_metrics.utils.html_style import STYLE

MAIN, STUDENTS, CPS, PROBES = ("dibels_student_window.csv", "dibels_students.csv", "dibels_checkpoints.csv",
                               "dibels_probes.csv")

# (file, group, column, type, description, example, used in Tableau for)
ROWS = [
    # main file: identity of the row
    (MAIN, "What the row is", "school_year", "text", "School year the data belongs to (from config).", "2026-2027", "Context. Not shown today."),
    (MAIN, "What the row is", "assessment", "text", "Which assessment this row tracks. Future assessments (i-Ready, DnA) reuse this column.", "DIBELS PM", "Context / future page filter."),
    (MAIN, "What the row is", "level", "text", "The student's fall (BOY) benchmark level. Decides which schedule they follow: Well Below = 2-week windows, Below = 4-week windows.", "Well Below", "Level toggle (`p_Level`) and `In Level` filter on every sheet."),
    # window
    (MAIN, "Window", "window_id", "whole number", "Order number of the window inside the level's schedule (Well Below 1-8, Below 1-4).", "4", "Window selector (`p_Window`), previous-window lookup, heat grid column order."),
    (MAIN, "Window", "window_label", "text", "Readable window name.", "Well Below window 4", "Heat grid column headers, tile subtitles."),
    (MAIN, "Window", "start_date", "date", "First day of the window.", "2026-10-13", "Opens card in the checkpoint strip."),
    (MAIN, "Window", "end_date", "date", "Last day of the window (the deadline).", "2026-10-26", "Days left in the window."),
    (MAIN, "Window", "window_state", "text", "Where the window is as of the run date: Closed, Current or Upcoming.", "Current", "Picks the default window; drives `Status` (closed windows are judged against 95%)."),
    # checkpoint now
    (MAIN, "Checkpoint today", "current_checkpoint_label", "text", "Name of the most recent checkpoint on or before the run date. 'Window opens' before the first one, 'Window closed' after the end.", "Check 2", "The 'Compared to' banner."),
    (MAIN, "Checkpoint today", "current_checkpoint_date", "date", "Date of that checkpoint.", "2026-10-20", "The 'Compared to' banner; CURRENT card in the strip."),
    (MAIN, "Checkpoint today", "current_target_pct", "whole number", "Percent of students that should be tested by now (the target teachers are compared to). 0 before the first checkpoint; the final target once the window closes.", "70", "Pace marker on the bars; the On track / Behind / Off track status."),
    (MAIN, "Checkpoint next", "next_checkpoint_label", "text", "Name of the next upcoming checkpoint. Blank when none is left.", "Pre-deadline checkpoint", "'Next checkpoint' tile."),
    (MAIN, "Checkpoint next", "next_checkpoint_date", "date", "Date of the next checkpoint. Blank when none is left.", "2026-10-23", "'Next checkpoint' tile."),
    (MAIN, "Checkpoint next", "next_target_pct", "whole number", "Target % at the next checkpoint. Blank when none is left.", "90", "'Next checkpoint' tile."),
    # checkpoint strip
    *[(MAIN, "Checkpoint strip", f"cp{i}_{f}", t, d.format(i=i), ex, "Checkpoint strip card.")
      for i in range(1, 5) for f, t, d, ex in (("label", "text", "Name of checkpoint {i} in this window.", "Check 1"),
                                               ("date", "date", "Date of checkpoint {i}.", "2026-10-16"),
                                               ("target_pct", "whole number", "Target % tested at checkpoint {i}.", "40"))],
    (MAIN, "Checkpoint strip", "final_target_pct", "whole number", "Target % tested by the end of the window.", "95", "Solid 95% line on the bars; Met / Missed when a window closes."),
    # student
    (MAIN, "Student", "grade", "text", "Current grade from PowerSchool (K, 1-5).", "2", "Grade bars; drill-down to teachers."),
    (MAIN, "Student", "teacher", "text", "Accountable teacher: the teacher of the student's current homeroom section in PowerSchool, 'Last, First'.", "Lastname, Firstname", "Teachers table; teacher x window heat grid; click-through to students."),
    (MAIN, "Student", "homeroom", "text", "Homeroom section name (the PowerSchool section number without 'HR').", "3A", "Reference only."),
    (MAIN, "Student", "student_id", "text", "PowerSchool student number. Same ID used in the DIBELS exports.", "123456", "Counts students (`COUNTD`); shown on the untested list."),
    (MAIN, "Student", "student_name", "text", "First and last name from PowerSchool, 'First Last'.", "Jane Smith", "Student detail page title."),
    (MAIN, "Student", "student_name_last_first", "text", "Name from PowerSchool as 'Last, First'. Use this in lists so compound last names sort correctly.", "Smith, Jane", "Student list."),
    # result
    (MAIN, "Result", "probes_in_window", "whole number", "How many distinct days the student had a progress monitoring probe inside this window. Several scores on one day (e.g. Decoding + Letter Sounds) count as one probe.", "2", "Untested list column; check for repeat testing."),
    (MAIN, "Result", "tested", "0 or 1", "1 if the student had at least 1 probe in the window, else 0. The minimum is `tested_rule_min_probes` in the calendar's Settings sheet.", "1", "The core number: % tested = sum(tested) / count of students."),
    (MAIN, "Result", "last_probe_date", "date", "Most recent probe date inside the window. Blank when not tested.", "2026-10-15", "Untested / tested lists."),
    (MAIN, "Result", "window_aimline_status", "text", "Aimline status from the student's most recent probe inside this window: Below, At or Above, or Not available (Amplify gives no status yet). 'No probe' when the student has no probe in the window. If a probe date has several measures, any one Below makes it Below.", "Below", "Growth view: is the student meeting the aimline this window?"),
    (MAIN, "Result", "latest_probe_date", "date", "Date of the student's most recent probe in any window. Blank when they have never been probed.", "2026-10-08", "Student list: when they were last tested."),
    (MAIN, "Result", "latest_aimline_status", "text", "Aimline status from the student's most recent probe in any window (same rule as window_aimline_status). 'No probes' when the student has never been probed this year.", "Below", "Student list: current standing against the aimline."),
    # freshness
    (MAIN, "Freshness", "as_of_date", "date", "The date the pipeline was run. Window states, checkpoints and days left are all worked out from this date.", "2026-10-21", "Days left; strip state (passed / current / upcoming)."),
    (MAIN, "Freshness", "data_as_of", "date", "Date of the latest probe in the DIBELS export. Probes after this date are not in the dashboard yet.", "2026-10-21", "'Data through ...' note at the top of each page."),
    (MAIN, "Freshness", "roster_as_of", "date", "Export date of the PowerSchool roster used.", "2026-10-21", "'Roster ...' note at the top of each page."),
    # students file
    (STUDENTS, "Student", "student_id", "text", "PowerSchool student number.", "123456", "Join key."),
    (STUDENTS, "Student", "student_name", "text", "First and last name, 'First Last'.", "Jane Smith", "Follow-up lists."),
    (STUDENTS, "Student", "student_name_last_first", "text", "Name as 'Last, First'.", "Smith, Jane", "Follow-up lists."),
    (STUDENTS, "Student", "grade", "text", "Current grade (K, 1-5).", "3", "Follow-up lists."),
    (STUDENTS, "Student", "homeroom", "text", "Homeroom section name.", "3A", "Follow-up lists."),
    (STUDENTS, "Student", "teacher", "text", "Homeroom teacher.", "Lastname, Firstname", "Follow-up lists."),
    (STUDENTS, "Benchmark", "level", "text", "Fall benchmark level: Well Below, Below, At, Above. 'No benchmark' = on the roster but no benchmark record. 'Not scored' = benchmark Partial or Not Started, so no level yet.", "Below", "Who is tracked; follow-up page for students who still need a benchmark."),
    (STUDENTS, "Benchmark", "benchmark_status", "text", "Status of the benchmark record: Complete, Partial, Not Started, or No record.", "Complete", "Follow-up page."),
    (STUDENTS, "Benchmark", "tracked", "True / False", "True when the student is Well Below or Below, so is expected to be progress monitored.", "True", "Separates tracked from not tracked students."),
    # checkpoints file
    (CPS, "Calendar", "assessment", "text", "Assessment the checkpoint belongs to.", "DIBELS PM", "Reference copy of the calendar."),
    (CPS, "Calendar", "level", "text", "Well Below or Below (each has its own schedule).", "Below", "Reference copy of the calendar."),
    (CPS, "Calendar", "window_id", "whole number", "Window the checkpoint belongs to.", "2", "Reference copy of the calendar."),
    (CPS, "Calendar", "checkpoint_date", "date", "Date of the checkpoint.", "2026-10-13", "Reference copy of the calendar."),
    (CPS, "Calendar", "label", "text", "Checkpoint name.", "Check 1", "Reference copy of the calendar."),
    (CPS, "Calendar", "target_pct_tested", "whole number", "Target % of students tested by that date.", "40", "Reference copy of the calendar."),
    (CPS, "Calendar", "notes", "text", "Free-text notes from the calendar file.", "", "Reference only."),
]
# demographics (from the DIBELS benchmark export): (column, description, example)
_DEMO = [
    ("gender", "Gender as recorded in the DIBELS export.", "Female"),
    ("race", "Race as recorded in the DIBELS export. 'Not reported' when blank.", "Black or African-American"),
    ("hispanic_latino", "Hispanic or Latino ethnicity: Yes, No, or Not reported.", "No"),
    ("special_education", "Special Education field from the DIBELS export. Mostly 'Not reported' (the export rarely fills it), "
                          "so use iep_status to filter on special education.", "Not reported"),
    ("iep_status", "Whether the student has an IEP (Yes / No).", "No"),
    ("ell_status", "Whether the student is an English language learner (Yes / No).", "Yes"),
]
for _file in (MAIN, STUDENTS, PROBES):
    ROWS += [(_file, "Demographics", c, "text", d, ex, "Filters to compare groups of students.") for c, d, ex in _DEMO]

ROWS += [
    (PROBES, "What the row is", "school_year", "text", "School year of the data.", "2026-2027", "Context."),
    (PROBES, "What the row is", "level", "text", "Student's fall benchmark level (Well Below or Below).", "Well Below", "Level toggle."),
    (PROBES, "Window", "window_id", "whole number", "Window the probe date falls in, for the student's level. Blank if the date is outside every window.", "3", "Window filter on the student detail page."),
    (PROBES, "Window", "window_label", "text", "Readable window name.", "Well Below window 3", "Student detail page."),
    (PROBES, "Student", "grade", "text", "Current grade (K, 1-5).", "2", "Filter."),
    (PROBES, "Student", "teacher", "text", "Accountable homeroom teacher.", "Lastname, Firstname", "Filter / header."),
    (PROBES, "Student", "student_id", "text", "PowerSchool student number.", "123456", "Link from the untested students list."),
    (PROBES, "Student", "student_name", "text", "First and last name, 'First Last'.", "Jane Smith", "Student detail page header."),
    (PROBES, "Student", "student_name_last_first", "text", "Name as 'Last, First'.", "Smith, Jane", "Lists."),
    (PROBES, "Probe", "probe_date", "date", "Date the probe was given (DIBELS 'Device Date').", "2026-09-25", "Probe history table."),
    (PROBES, "Probe", "pm_period", "text", "Which benchmark cycle the probe belongs to: BOY (between the fall and winter benchmarks, Amplify's 'BOY->MOY'), MOY (winter to spring, 'MOY->EOY') or EOY (after spring, 'After EOY'). Probe number and total probes restart in each period. The window (by date) is separate from the period.", "BOY", "Student detail: which period a probe falls in."),
    (PROBES, "Probe", "measure", "text", "The DIBELS measure that was monitored.", "Decoding (NWF-WRC)", "Probe history table; one row per measure per probe."),
    (PROBES, "Probe", "probe_number", "whole number", "Which probe this is for this student and measure: 1 = first.", "2", "Probe history table."),
    (PROBES, "Probe", "total_probes", "whole number", "How many probes this student has on this measure within the progress monitoring period (Amplify's 'Total Number of Probes' counts per PM period, e.g. BOY to MOY, and starts over in the next period), so 'probe 2 of 2'.", "2", "Probe history table."),
    (PROBES, "Probe", "score", "number", "The student's score on the probe.", "27", "Probe history table; score over time."),
    (PROBES, "Probe", "aimline_status", "text", "Amplify's read of the score against the aimline (Below, At or Above). 'Not available' when Amplify gives no status, usually early probes.", "Below", "Probe history table; colour."),
    (PROBES, "Probe", "aimline_value_by_date", "number", "Where the aimline says the score should be on that date. Blank when there is no aimline yet.", "31", "Score vs aimline."),
    (PROBES, "Probe", "growth_goal_set", "number", "The goal score set for this student on this measure. Blank when no goal is set.", "50", "Goal line."),
    (PROBES, "Probe", "assessing_teacher", "text", "Teacher who gave the probe in DIBELS, which may differ from the homeroom teacher.", "Lastname, Firstname", "Reference."),
]
COLS = ["file", "group", "column", "type", "description", "example", "used_in_tableau_for"]


def _check(frames: dict[str, pd.DataFrame]) -> None:
    for f, df in frames.items():
        documented = [r[2] for r in ROWS if r[0] == f]
        missing = [c for c in df.columns if c not in documented]
        stale = [c for c in documented if c not in df.columns]
        if missing or stale:
            raise SystemExit(f"Data dictionary out of date for {f}: undocumented columns {missing}, "
                             f"described but not in the file {stale}. Edit apm_metrics/utils/dictionary.py.")


def _html(df: pd.DataFrame, stamp: str) -> str:
    e = html.escape
    nav = "".join(f'<a href="#{i}">{e(f)}</a>' for i, f in enumerate(df["file"].unique()))
    body = ""
    for i, (f, g) in enumerate(df.groupby("file", sort=False)):
        what = {MAIN: "The main Tableau file. One row per tracked student per window.",
                STUDENTS: "Every K-5 student on the roster with their benchmark level. Used for follow-up lists.",
                CPS: "The testing calendar's checkpoints, one row per checkpoint.",
                PROBES: "Every progress monitoring probe for tracked students: one row per measure per probe. "
                        "Feeds the student detail page."}[f]
        rows = "".join(
            f"<tr data-t=\"{e((r.column + ' ' + r.description + ' ' + r.group).lower())}\"><td><code>{e(r.column)}</code></td>"
            f"<td>{e(r.group)}</td><td>{e(r.type)}</td><td>{e(r.description)}</td><td>{e(str(r.example))}</td>"
            f"<td>{e(r.used_in_tableau_for)}</td></tr>" for r in g.itertuples())
        body += (f'<section id="{i}"><h2>{e(f)}</h2><p class="lead">{e(what)}</p>'
                 f'<div class="tw"><table><thead><tr><th>Column</th><th>Group</th><th>Type</th><th>What it means</th>'
                 f'<th>Example</th><th>Used in Tableau for</th></tr></thead><tbody>{rows}</tbody></table></div></section>')
    js = ("document.getElementById('q').addEventListener('input',function(){var v=this.value.toLowerCase();"
          "document.querySelectorAll('tbody tr').forEach(function(r){r.style.display=r.dataset.t.indexOf(v)>-1?'':'none'})})")
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>DIBELS progress monitoring: data dictionary</title><style>{STYLE}</style></head><body>'
            f'<header class="hero"><div class="in"><h1>Data dictionary</h1><p>Every column in the DIBELS progress monitoring '
            f'Tableau files: what it means, an example, and where the dashboard uses it.</p><div class="meta">Built {e(stamp)}</div></div></header>'
            f'<nav class="top"><div class="in">{nav}</div></nav><main><input id="q" class="search" type="search" '
            f'placeholder="Search columns (try: checkpoint, teacher, tested)">{body}</main>'
            f'<footer>Generated automatically on every pipeline run from apm_metrics/utils/dictionary.py.</footer><script>{js}</script></body></html>')


def write_all(out_dir, frames: dict[str, pd.DataFrame]) -> None:
    """Checks every output column is documented, then writes data_dictionary.csv and data_dictionary.html."""
    _check(frames)
    df = pd.DataFrame([r for r in ROWS if r[0] in frames], columns=COLS)
    df.to_csv(out_dir / "data_dictionary.csv", index=False)
    (out_dir / "data_dictionary.html").write_text(_html(df, date.today().isoformat()), encoding="utf-8")
