# DIBELS Progress Monitoring Tracker

A Python pipeline and a Tableau dashboard that answer one question for a school or network: **are the students who need extra
reading support being progress monitored on schedule?**

The dashboard drills from grade, to teacher, to student:

1. **Grades:** the share of tracked students tested in the current window, with a status (on track, behind, off track).
2. **Teachers:** each teacher's tested count and percent.
3. **Students:** exactly who still needs a probe.
4. **Student detail:** a student's scores against their aimline and goal, window by window.

A student is "tracked" when they are enrolled in K-5 and scored Well Below or Below on the beginning-of-year DIBELS benchmark. A
student is "tested" in a window when they have at least one progress monitoring probe dated inside it.

This repository contains **no real data**. A fake-data generator lets you run everything and see the dashboard before you touch a
real student record.

## What you need (three exports and a calendar)

| Input | Where it comes from |
|---|---|
| CC table (current course enrollments) | PowerSchool SIS, Direct Database Export of the CC table |
| DIBELS benchmark, beginning of year (BOY) | Amplify mCLASS, Download Your Data, Benchmark |
| DIBELS progress monitoring (PM) | Amplify mCLASS, Download Your Data, Progress Monitoring |
| Testing calendar (windows and checkpoints) | `tools/make_example_calendar.py` makes an example you can edit |

Step by step: [docs/how_to_pull_the_data.md](docs/how_to_pull_the_data.md).

## Quick start with fake data

Requires Python 3.10 or newer.

```
python -m venv .venv
.venv\Scripts\activate            (Mac or Linux: source .venv/bin/activate)
pip install -r requirements.txt

python demo/make_fake_data.py --raw                    # fake roster, benchmark and PM exports, plus the Tableau files
python -m apm_metrics.build_dibels --as-of 2026-11-02  # run the real pipeline on those fake exports
python tests/verify_dibels.py                          # independent check of the output against the raw files
```

The Tableau files are written to `output/tableau/`. The fake demo datasets (with dated history) are in `output/fake_demo/`.

## Use it with your own data

1. Put your exports in `data/raw/dibels/` (benchmark and progress monitoring) and `data/raw/powerschool_cc/` (the CC table).
   Name them like `dibels_pm_2026-27_boy-moy_2026-10-26_1338.csv` (see the table below).
2. Build a calendar: `python tools/make_example_calendar.py --start 2026-09-01`, then edit `data/calendar/testing_calendar.xlsx`
   for your windows, breaks and checkpoint targets.
3. Edit `config/paths.yaml`: your `school_year` and `school_name`.
4. Run `python -m apm_metrics.build_dibels`, then `python tests/verify_dibels.py`, then open `output/data_quality.xlsx`.
5. Build the dashboard from `output/tableau/` with [docs/tableau_build_guide.md](docs/tableau_build_guide.md).

File names use the pattern `source_schoolyear_window_pulldate[_HHMM].ext`:

| Export | Example name |
|---|---|
| PowerSchool CC table | `powerschool_cc_2026-27_boy_2026-10-21.txt` |
| DIBELS benchmark | `dibels_bm_2026-27_boy_2026-10-21_1240.csv` |
| DIBELS progress monitoring | `dibels_pm_2026-27_boy-moy_2026-10-26_1338.csv` |

The roster and the benchmark use the newest file. Progress monitoring uses **every** file for the school year, so keep the older
exports: a probe that appears in more than one file is counted once, from the newest.

## What the pipeline writes (`output/`)

| File | What |
|---|---|
| `tableau/dibels_student_window.csv` | One row per tracked student per window: the main dashboard data |
| `tableau/dibels_probes.csv` | One row per measure per probe, for the student detail page |
| `tableau/dibels_students.csv` | Every K-5 student on the roster, with level and whether tracked |
| `tableau/dibels_checkpoints.csv` | The calendar's checkpoints |
| `history/` | A dated copy of the main file from every run |
| `data_quality.xlsx` | Problems found (missing benchmarks, students not on the roster, and so on) |
| `data_dictionary.html` and `.csv` | Every column in the Tableau files, explained |
| `dashboard_guide.html` | A plain-language page for leaders and teachers |

## Student privacy (FERPA)

Student data stays on your computer or your school's drive. `.gitignore` blocks exports, spreadsheets and the `data/raw/` and
`output/` folders, so they cannot be committed by accident. `config/verified_transfers.yaml` is where you may list student numbers
of students who transferred out; keep real numbers out of any public copy. Check a workbook with
`python demo/scan_workbook_for_real_data.py` before you publish it anywhere (see below).

## Showing the dashboard publicly with fake data

`demo/` has tools for a public Tableau Public version built only from fake data: the generator, a "how this dashboard works" guide
page, a verifier, a scanner that looks for real names, ids and server addresses inside a workbook, and a script that strips a
workbook copy's server address and saved selections. Step by step: [docs/publish_to_tableau_public.md](docs/publish_to_tableau_public.md).

## Folders

| Folder | What |
|---|---|
| `apm_metrics/` | The pipeline: `build_dibels.py` and `utils/` (loading, roster, data dictionary, guide page) |
| `config/` | `paths.yaml`, `rules.yaml` (who is tracked), `verified_transfers.yaml` |
| `data/` | Where your exports and calendar go (ignored by git) |
| `docs/` | How the rules work, how to pull the data, the Tableau build guide, publishing |
| `demo/` | Fake-data and public-demo tools |
| `tools/` | `make_example_calendar.py` |
| `tests/` | Pipeline checks and the scanner test |

## Tests

```
python tests/test_file_names.py      # old and new export file names are recognized
python tests/test_combine_pm.py      # several PM exports are combined, duplicates removed
python tests/test_scanner.py         # the public-demo safety scanner
python tests/verify_dibels.py        # rebuilds the numbers from the raw exports and compares (needs exports in data/raw/)
```

## Notes

This project is independent. It is not affiliated with or endorsed by Amplify or PowerSchool. DIBELS, mCLASS and PowerSchool are
trademarks of their owners. The benchmark levels come from the Amplify export; this code never recalculates them.
