# How to pull the data

The pipeline needs three exports. Save each one in its folder and rename it by hand to the standard pattern:

`source_schoolyear_window_pulldate[_HHMM].ext`

- school year as `2026-27`
- window `boy`, `moy`, `eoy` (or `boy-moy`, or `all`)
- pull date as `YYYY-MM-DD`, and an optional 24-hour time `_HHMM`

The older Amplify and PowerSchool default names are also recognized, so you may keep a mix.

## 1. DIBELS benchmark (beginning of year)
Folder: `data/raw/dibels/`. Example name: `dibels_bm_2026-27_boy_2026-10-21_1240.csv`.

1. Amplify home page, under "Your programs", open **mCLASS Literacy**.
2. Choose **Download Your Data**.
3. Choose **Benchmark**.
4. Reporting period: the current school year, **BOY**.
5. Check **Show students enrolled now**.
6. Pick your school. The code keeps grades K-5 and drops the rest.
7. Click **Download CSV**.

The benchmark is used for one thing: each student's level (Well Below, Below, At, Above), plus demographics for filters. Pull it
again only if results changed, for example late or unfinished benchmarks.

## 2. DIBELS progress monitoring
Folder: `data/raw/dibels/`. Example name: `dibels_pm_2026-27_boy-moy_2026-10-26_1338.csv`.

1. In mCLASS Literacy, **Download Your Data**, then **Progress Monitoring**.
2. Same school year, **Show students enrolled now**, your school.
3. Click **Download CSV**.

Pull it as often as you want fresh numbers. Keep the older files: the pipeline combines every progress monitoring file for the
school year and keeps a repeated probe once, from the newest file. Probes appear after the device syncs, so the newest export
can lag by a few days.

## 3. PowerSchool CC table
Folder: `data/raw/powerschool_cc/`. Example name: `powerschool_cc_2026-27_boy_2026-10-21.txt`.

1. PowerSchool Start Page: select your currently enrolled K-5 students.
2. System, then **Direct Database Export**.
3. Table **CC**, match selection **Students**.
4. Fields, in this order: `[01]Student_Number`, `[01]Last_Name`, `[01]First_Name`, `[01]Grade_Level`, `Course_Number`,
   `[02]Course_Name`, `Section_Number`, `SectionID`, `Expression`, `[05]LastFirst`, `DateEnrolled`, `DateLeft`.
5. Export as tab-delimited text with column titles.

The pull date in the file name is the date the roster is "as of": a student is on the roster when `DateEnrolled <= date < DateLeft`.
A student's homeroom is their active section whose `Section_Number` ends with the suffix in `config/rules.yaml` (default `HR`);
change that suffix to match how your school names homeroom sections.

## 4. Testing calendar
`python tools/make_example_calendar.py --start 2026-09-01` writes `data/calendar/testing_calendar.xlsx` with 2-week windows for Well
Below students and 4-week windows for Below students, and four checkpoints per window (40, 70, 90 and 95 percent tested). The
percentages are placeholders. Edit the spreadsheet for your breaks, holidays and targets.

## Then run
```
python -m apm_metrics.build_dibels          # or add --as-of YYYY-MM-DD to run as of another date
python tests/verify_dibels.py
```
Open `output/data_quality.xlsx` to see anything that needs a look, then refresh the Tableau data sources.
