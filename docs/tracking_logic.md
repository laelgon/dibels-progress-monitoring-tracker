# How the tracking works

The rules the pipeline applies. The settings live in `config/rules.yaml` and in the Settings sheet of the testing calendar.

## Who is tracked (the denominator)
1. **Roster:** students currently enrolled in K-5 (PowerSchool CC table). A student's **homeroom teacher** is the teacher of their
   active section whose `Section_Number` ends with the homeroom suffix (default `HR`). That teacher is the accountable teacher.
2. **Level:** the student's composite level on the beginning-of-year DIBELS benchmark, joined on student number. Only **Well Below**
   and **Below** are expected to be progress monitored (`tracked_levels`).
3. Students on the roster with **no benchmark result** (for example, enrolled after the benchmark) appear in a separate group for
   follow-up. They are not counted in percentages.
4. Students who have left (not on the current roster) are excluded. A progress monitoring record for a student who is not on the
   roster is flagged for review and not counted.
5. Progress monitoring is **K-5 only** (`grades_in_scope`). Other grades in an export are dropped and listed in `data_quality.xlsx`.

The level stays the beginning-of-year level all year.

## What counts as tested
A student is **tested in a window** if they have at least **1 progress monitoring probe** dated inside the window (the probe's
`Device Date`). The export contains completed probes only, so "tested" is a yes or no per window. A student with no probes does
not appear in the progress monitoring export at all, which is why the roster and benchmark files are needed.

- Setting: `tested_rule_min_probes` in the calendar's Settings sheet (default 1).
- One probe can produce several export rows (two measures at the same sitting), so the pipeline counts distinct probe dates.

## Windows
The school year is cut into windows by level, in the testing calendar:

- **Well Below:** 2-week windows (8 in the example calendar).
- **Below:** 4-week windows (4 in the example calendar).

Lengths follow Amplify's progress monitoring guidance for these levels; use your own calendar if your school differs.

## Checkpoints and status
Each window has checkpoints with a target percent of students tested so far (the example calendar uses 40, 70, 90 and 95). The
status compares the percent tested to the **current checkpoint**: the most recent one on or before the run date.

| Status | Meaning |
|---|---|
| On track | At or above the current checkpoint target |
| Behind | Under it by up to `behind_points` (default 15) |
| Off track | Under it by more than `behind_points` |
| Not started | The window has not opened, or no checkpoint has passed |
| Met target | The window has closed and the percent tested is at least the final target (default 95) |
| Missed target | The window has closed and the percent tested is under the final target |

Percent tested = tested students / tracked students, per level and window.

## How the pipeline works
`python -m apm_metrics.build_dibels [--as-of YYYY-MM-DD]`. Without `--as-of`, today is the "as of" date, and the window states,
checkpoints and days left are all worked out from it.

1. Roster: K-5 students with an active enrollment on the roster export date (`DateEnrolled <= date < DateLeft`).
2. Join the benchmark level by student number. Keep Well Below and Below (the "tracked" students).
3. Give each tracked student one row per window of their level's schedule.
4. A window is tested (1) if the student has at least 1 probe date inside it, else 0.
5. Attach the window state (Closed, Current or Upcoming) and the current and next checkpoints and targets.
6. Write the Tableau files, the data quality report, the data dictionary and the guide page.

**Files.** The roster and benchmark use only the newest file. Progress monitoring uses **all** files for the school year, combined
oldest to newest; a probe in more than one export is kept once, from the newest (it has the most up-to-date aimline and goal). A
probe is "the same" when student, measure, device date, progress monitoring period and probe number match.

**Student groups that are not tracked** (listed in `data_quality.xlsx` and `dibels_students.csv`):

- **At or Above:** not expected to be progress monitored.
- **No benchmark:** on the roster, but no benchmark record.
- **Not scored:** benchmark Partial or Not Started, so no level yet.
- A student with two benchmark rows (for example one Complete and one Partial) uses the row that has a level.

**History.** Each run recalculates every window from the files it is given, so a closed window's percentage can drift if enrollment
changes. Each run also saves a dated copy of the main file in `output/history/` (same-day runs overwrite).

## Aimline columns (growth)
The main file carries two aimline fields per row, from the progress monitoring export's `Aimline Status`:

- `latest_aimline_status` and `latest_probe_date`: from the student's most recent probe in any window.
- `window_aimline_status`: from the student's most recent probe inside that row's window ("No probe" when they have none).

When a probe date has several measures: **Below** if any measure is Below the aimline; otherwise **At or Above** if any measure is;
otherwise **Not available** (the platform gave no status, usually for early probes). Probe-by-probe detail (score, aimline value,
goal) is in `dibels_probes.csv`.

## Notes on the Amplify progress monitoring export
- **Device Date** is when the probe was given on the device; **Sync Date** is when it reached the platform. A probe given but not
  yet synced is not in the export, so the student looks untested until the sync.
- **PM Period** (BOY->MOY, MOY->EOY, After EOY): the export covers the selected period(s). **Probe Number** and **Total Number of
  Probes** count within the period and start over in the next one.
- **Aimline Status** is only "At or Above", "Below" or blank.
- **Assessing Teacher** is who gave the probe. The dashboard credits the PowerSchool homeroom teacher, whoever gave the probe.

## Known limits
- The export lags: the dashboard shows a "data as of" date, the date of the newest probe.
- Roster differences against platform reports of a few students per grade are expected: this pipeline uses current enrollment, not
  the enrollment on the day of the benchmark.
