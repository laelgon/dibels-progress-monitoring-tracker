# Tableau build guide: DIBELS progress monitoring dashboards

One workbook, **5 dashboards**, **2 live data sources** (`dibels_student_window.csv` for dashboards 1-4 and
`dibels_probes.csv` for the student detail page). Amber is `#B26A00`. Use **Tableau Desktop 2019 or newer** (Show/Hide
buttons and Navigation objects). Menu names can differ slightly by version. Everything below uses **floating** objects with
exact position and size.

| # | Dashboard | How you get there |
|---|---|---|
| 1 | DIBELS Grades | Opening page |
| 2 | Teachers | Click a grade bar on dashboard 1 |
| 3 | Untested Students | Click a teacher row on dashboard 2 |
| 4 | Heat Grid | Navigation button on dashboard 1 |
| 5 | Student Detail | Click a student on dashboard 3 |

Dashboards 1-4 have a **Level** toggle (Well Below | Below) and a **Window** selector (default: the current window).
Every dashboard has a **How it works** button.

## What will look different from the preview
Tableau cannot draw everything in the preview exactly. These are the closest equivalents the guide uses.

| In the preview | In Tableau |
|---|---|
| Rounded status chips ("Off track") | A small coloured **square mark** with white text (Marks: Square, label = Status) |
| Colored message banner on the student page | A **square mark** sized to fill the sheet, white bold label, Color = state |
| Amber outline around the CURRENT checkpoint card | Amber text with the word **CURRENT**; passed and upcoming cards in gray (Tableau can't outline one card) |
| Whole row highlights on hover | None. Row click still works |
| Click only on the "Not tested" number | The action fires on **any cell in the teacher row**; the Not tested column is bold amber as a cue |
| Dark mode | Not automatic |

---

## 0. Before you start
1. Run the pipeline (`python -m apm_metrics.build_dibels`) and then `python tests/verify_dibels.py`. Check
   `output/data_quality.xlsx`.
2. Data file: `output/tableau/dibels_student_window.csv` (one row per tracked student per window
   for that student's level). Key columns: `level`, `window_id`, `window_label`, `window_state`
   (Closed / Current / Upcoming), `grade`, `teacher`, `student_id`, `student_name`, `tested` (1/0),
   `current_checkpoint_*`, `next_checkpoint_*`, `cp1..cp4_*`, `current_target_pct`, `final_target_pct`,
   `as_of_date`, `data_as_of`, `roster_as_of`, `last_probe_date`, `probes_in_window`. Every column is described in
   `output/data_dictionary.html`.
3. Targets are whole numbers (70 = 70%). `tested` is 0/1, so a percent is a computed field (below).

## 1. Connect
1. Tableau Desktop -> **Connect -> To a File -> Text file** -> pick `dibels_student_window.csv`. Keep it a **live**
   connection.
2. Rename the data source **APM DIBELS**.
3. On the Data pane check the types: `window_id` and `tested` = number (whole), `grade` and `student_id` = string,
   all `*_date` fields = Date. Fix any that are wrong (click the type icon).
4. `grade`: right-click -> **Default Properties -> Sort -> Manual** -> order **K, 1, 2, 3, 4, 5**.
5. **Second data source (student detail page).** **Data -> New Data Source -> Text file** -> `dibels_probes.csv`; rename it
   **APM Probes**. One row per measure per probe for tracked students (`measure`, `probe_number`, `total_probes`,
   `score`, `aimline_status`, `aimline_value_by_date`, `growth_goal_set`, plus the student's grade, teacher, level and
   demographics). Check types: `score`, `probe_number`, `total_probes`, `aimline_value_by_date`, `growth_goal_set` =
   number; `probe_date` = date.
6. **Demographics** (`gender`, `race`, `hispanic_latino`, `special_education`, `iep_status`, `ell_status`) are in both
   files, ready to use as filters later: drag one to Filters on a sheet -> Show Filter -> Apply to Worksheets ->
   Selected Worksheets. `special_education` is mostly "Not reported" in DIBELS, so use `iep_status` for special education.

## 2. Parameters
Create these (Data pane -> down arrow -> **Create Parameter**).

| Name | Type | Allowable values | Current value |
|---|---|---|---|
| `p_Level` | String | List: `Well Below`, `Below` | Well Below |
| `p_Window` | Integer | List: 0 = "Current window", then 1 = "Window 1" ... 8 = "Window 8" | 0 |
| `p_Behind_Points` | Integer | All | 15 |

(Below has only windows 1-4; picking 5-8 with Below shows nothing. That is expected.)

## 3. Calculated fields
Create each with **Analysis -> Create Calculated Field**. Names must match exactly (later fields use them). Build the
**APM DIBELS** fields first.

**Filters (row level)**
- `In Level`: `[level] = [p_Level]`
- `Current Window ID`:
  `IFNULL({FIXED [level] : MAX(IF [window_state] = "Current" THEN [window_id] END)}, {FIXED [level] : MAX([window_id])})`
  (the second part makes the dashboard show the last window after the final window closes)
- `Sel Window ID`: `IF [p_Window] = 0 THEN [Current Window ID] ELSE [p_Window] END`
- `In Window`: `[window_id] = [Sel Window ID]`
- `Is Prev Window`: `[window_id] = [Sel Window ID] - 1`

**Measures**
- `Tracked Students`: `COUNTD([student_id])`
- `Tested Students`: `SUM([tested])`
- `Not Tested`: `[Tracked Students] - [Tested Students]`
- `Pct Tested (pts)`: `100 * SUM([tested]) / COUNTD([student_id])`  -> format: Number (Custom) `0"%"`
- `Target (pts)`: `AVG([current_target_pct])`
- `Final Target (pts)`: `AVG([final_target_pct])`
- `Days Left`: `DATEDIFF('day', MAX([as_of_date]), MAX([end_date]))`

**Status** (the colour on every bar, tile and heat cell)
```
IF ATTR([window_state]) = "Closed" THEN
    IF [Pct Tested (pts)] >= [Final Target (pts)] THEN "Met target" ELSE "Missed target" END
ELSEIF ATTR([window_state]) = "Upcoming" OR [Target (pts)] = 0 THEN "Not started"
ELSEIF [Pct Tested (pts)] >= [Target (pts)] THEN "On track"
ELSEIF [Target (pts)] - [Pct Tested (pts)] <= [p_Behind_Points] THEN "Behind"
ELSE "Off track"
END
```
Set its colours once (drag `Status` to Color on any sheet -> **Edit Colors**), then every sheet reuses them:

| Status | Colour |
|---|---|
| Met target, On track | `#2E7D32` (green) |
| Behind | `#B26A00` (amber) |
| Off track, Missed target | `#C62828` (red) |
| Not started | `#5E6674` (gray) |

**Text fields**
- `Not Tested Text`: `STR([Not Tested]) + CHAR(10) + "of " + STR([Tracked Students]) + " students"`
- `Next CP Text`:
```
IF ISNULL(MAX([next_checkpoint_date])) THEN "None" + CHAR(10) + "Window " + LOWER(ATTR([window_state]))
ELSE DATENAME('month', MAX([next_checkpoint_date])) + " " + STR(DAY(MAX([next_checkpoint_date])))
     + CHAR(10) + "Target " + STR(MAX([next_target_pct])) + "%"
     + CHAR(10) + STR([Days Left]) + " days left in window" END
```
- `Compared To`:
```
IF ATTR([window_state]) = "Closed" THEN
    "Window closed. Statuses compare final results to the " + STR(MAX([final_target_pct])) + "% target."
ELSEIF MAX([current_target_pct]) = 0 THEN
    "Window just opened. No target yet. Next checkpoint: " + MAX([next_checkpoint_label]) + "."
ELSE "Statuses compare to the current checkpoint: " + MAX([current_checkpoint_label]) + " ("
    + DATENAME('month', MAX([current_checkpoint_date])) + " " + STR(DAY(MAX([current_checkpoint_date])))
    + "), " + STR(MAX([current_target_pct])) + "% tested. Behind = up to " + STR([p_Behind_Points])
    + " points under. Off track = more than " + STR([p_Behind_Points]) + " under."
END
```
- `Data As Of Text`: `"Data through " + STR(MAX([data_as_of])) + "  |  Roster " + STR(MAX([roster_as_of]))`
- `Teachers Title`: `IF COUNTD([grade]) = 1 THEN "Grade " + ATTR([grade]) ELSE "All grades" END`
- `Untested Title`: `"Not tested: " + STR([Not Tested])`
- `Cell Text` (heat grid): `IF ATTR([window_state]) = "Upcoming" THEN "" ELSE STR(ROUND([Pct Tested (pts)])) + "%" END`
  (a whole-number percent is safe with `STR(ROUND())`; the Server problem only affects decimals)

**Checkpoint cards: 10 fields.** Create each one separately, name it exactly as shown, and paste the formula as written
(there is nothing to replace). Before you start, check in the Data pane that `cp1_date` ... `cp4_date`, `start_date` and
`as_of_date` have the **Date** type icon (a calendar). If one shows a string or number icon, click it and choose Date.
The error "Reference to undefined field" means a field name was typed with a placeholder or a typo.

`Card 0 Text`
```
"Window opens" + CHAR(10) + DATENAME('month', MAX([start_date])) + " " + STR(DAY(MAX([start_date])))
```
`Card 0 State`
```
IF MAX([start_date]) <= MAX([as_of_date]) THEN "Passed" ELSE "Upcoming" END
```
`Card 1 Text`
```
MAX([cp1_label]) + CHAR(10) + DATENAME('month', MAX([cp1_date])) + " " + STR(DAY(MAX([cp1_date]))) + CHAR(10) + STR(MAX([cp1_target_pct])) + "% tested"
```
`Card 1 State`
```
IF MAX([cp1_date]) = MAX([current_checkpoint_date]) AND ATTR([window_state]) = "Current" THEN "CURRENT" ELSEIF MAX([cp1_date]) <= MAX([as_of_date]) THEN "Passed" ELSE "Upcoming" END
```
`Card 2 Text`
```
MAX([cp2_label]) + CHAR(10) + DATENAME('month', MAX([cp2_date])) + " " + STR(DAY(MAX([cp2_date]))) + CHAR(10) + STR(MAX([cp2_target_pct])) + "% tested"
```
`Card 2 State`
```
IF MAX([cp2_date]) = MAX([current_checkpoint_date]) AND ATTR([window_state]) = "Current" THEN "CURRENT" ELSEIF MAX([cp2_date]) <= MAX([as_of_date]) THEN "Passed" ELSE "Upcoming" END
```
`Card 3 Text`
```
MAX([cp3_label]) + CHAR(10) + DATENAME('month', MAX([cp3_date])) + " " + STR(DAY(MAX([cp3_date]))) + CHAR(10) + STR(MAX([cp3_target_pct])) + "% tested"
```
`Card 3 State`
```
IF MAX([cp3_date]) = MAX([current_checkpoint_date]) AND ATTR([window_state]) = "Current" THEN "CURRENT" ELSEIF MAX([cp3_date]) <= MAX([as_of_date]) THEN "Passed" ELSE "Upcoming" END
```
`Card 4 Text`
```
MAX([cp4_label]) + CHAR(10) + DATENAME('month', MAX([cp4_date])) + " " + STR(DAY(MAX([cp4_date]))) + CHAR(10) + STR(MAX([cp4_target_pct])) + "% tested"
```
`Card 4 State`
```
IF MAX([cp4_date]) = MAX([current_checkpoint_date]) AND ATTR([window_state]) = "Current" THEN "CURRENT" ELSEIF MAX([cp4_date]) <= MAX([as_of_date]) THEN "Passed" ELSE "Upcoming" END
```

Card state colours (set on `Card 1 State`, then re-use via Edit Colors on the others): **CURRENT `#B26A00`**,
Passed `#5E6674`, Upcoming `#444441`.

**Student detail fields** (APM DIBELS; build these when you reach section 4.8)
- `Probes This Year`: `{FIXED [student_id] : SUM([probes_in_window])}`
- `Student Msg State`:
  `IF SUM([tested]) > 0 THEN "Tested" ELSEIF ATTR([window_state]) = "Closed" THEN "Missed" ELSE "Needs probe" END`
- `Student Message`:
```
IF SUM([tested]) > 0 THEN
    "Tested in " + ATTR([window_label]) + ". Last probe: " + DATENAME('month', MAX([last_probe_date])) + " " + STR(DAY(MAX([last_probe_date]))) + "."
ELSE
    "Not tested in " + ATTR([window_label]) + " yet. " + ATTR([teacher]) + " needs to give a progress monitoring probe by "
    + DATENAME('month', MAX([end_date])) + " " + STR(DAY(MAX([end_date]))) + "."
    + (IF MAX([Probes This Year]) = 0 THEN " No probes have been recorded for this student this school year." ELSE "" END)
END
```
- `Window Row State`:
  `IF SUM([tested]) > 0 THEN "Tested" ELSEIF ATTR([window_state]) = "Closed" THEN "Missed" ELSEIF ATTR([window_state]) = "Upcoming" THEN "Upcoming" ELSE "Needs probe" END`
- Colours for `Student Msg State` and `Window Row State`: Tested `#2E7D32`, Needs probe `#B26A00`, Missed `#C62828`,
  Upcoming `#5E6674`.

## 3b. Build order, with a check at each step
Do not build everything and then debug. After each step, check the result against your own data (a pivot of
`dibels_student_window.csv` in a spreadsheet works) before you move on.

| Step | What to build | Check |
|---|---|---|
| 1 | Connect both sources; types; grade sort | The row count matches the CSV; K sorts first |
| 2 | Parameters and the 5 filter fields | With `p_Level` = Well Below, a table of `window_id` shows 1-8 |
| 3 | Test table: Rows `grade`; Columns `Tracked Students`, `Tested Students`, `Pct Tested (pts)`; Filters `In Level`, `In Window` | For the current window, tracked and tested counts per grade match a pivot of the CSV (count of rows, sum of `tested`) |
| 4 | `Status` and its colours; drag to Color on the test table | Each grade's status follows the rule in section 3: compare its percent with the current checkpoint target |
| 5 | Change `p_Level` to Below | The counts change to the Below students; Below has windows 1-4 only |
| 6 | Set `p_Window` to a closed window | Statuses read Met or Missed, never On track |
| 7 | Build the tile sheets and checkpoint cards (4.1, 4.2) | Tested %, Not tested count, Last window %, Next checkpoint date and target, and the CURRENT card all agree with the CSV |
| 8 | `Grade Bars` (4.4), then dashboard 1 | A dashed line at the current target, a black line at the final target, bar order K, 1-5 |
| 9 | Dashboard 2 (`Teachers`), then the grade click action | Clicking a grade lists only that grade's teachers |
| 10 | Dashboard 3 (`Untested Students`) and the teacher click action | The not-tested total equals tracked minus tested; clicking a teacher lists their untested students |
| 11 | Dashboard 4 (`Heat Grid`) | The latest window matches step 3 |
| 12 | Dashboard 5 (student detail), then the student click action | A student with probes shows their window history and probe rows; the message says what the teacher needs to do |
| 13 | A student with no probes | The message adds "No probes have been recorded..."; probe history is empty |
| 14 | "How it works" pop-up (section 6), publish (section 9) | Works on the server as it did in Desktop |

## 4. Sheets
Unless noted, every sheet in dashboards 1-3 has the filters **In Level = True** and **In Window = True** (drag the field
to Filters, tick True). Show no sheet title unless noted. Turn off gridlines and row/column dividers.

**Status as a coloured square (use this wherever the guide says "status badge").** On the mark card, set Marks to
**Square**, drag `Status` to **Color** and to **Label**, set the label font to **white, bold**, and drag the Size slider so
the square fills the cell. This is the closest Tableau comes to the preview's chip.

### 4.1 Tiles (dashboard 1)
Each tile is a text sheet, Marks type **Text**. Format the main number 26 pt bold, the second line 11 pt.

| Sheet name | Marks / fields | Extra |
|---|---|---|
| `Tile Tested` | Text: `Pct Tested (pts)` + `Status`. Color: `Status` | Title (shown): "Tested, this window" |
| `Tile Not Tested` | Text: `Not Tested Text` | Title: "Students not tested" |
| `Tile Last Window` | Text: `Pct Tested (pts)` + `ATTR(window_label)`. **Filters: In Level, Is Prev Window** (not In Window) | Title: "Last window" |
| `Tile Next Checkpoint` | Text: `Next CP Text` | Title: "Next checkpoint" |

Fit: Entire View. Background: Format -> Shading -> `#F1EFE8`.

### 4.2 Checkpoint strip (dashboard 1): 5 sheets
Five sheets named `Card 0`, `Card 1`, `Card 2`, `Card 3`, `Card 4`. On each sheet, Marks = Text; put that card's two fields on
Text (for `Card 2`: `Card 2 Text` and `Card 2 State`) and the State field on Color. Filters: In Level, In Window.
Format 11 pt, centered. Add a border around the sheet: Format -> Borders. The CURRENT card is the amber one with the word
CURRENT; passed cards are gray.

### 4.3 `Compared To`, `Data As Of`
Text sheets with the matching calculated field on Text. `Compared To` filters: In Level, In Window. `Data As Of` has no filter. Font 12 pt gray `#5E6674`.

### 4.4 `Grade Bars` (dashboard 1)
1. Rows: `grade`. Columns: `Pct Tested (pts)`.
2. Marks: Bar. Color: `Status`. Label: `Pct Tested (pts)`.
3. Axis: fixed 0 to 100, hide the axis header.
4. Reference line 1: right-click axis -> **Add Reference Line** -> Line -> Per Cell -> Value: `Target (pts)` Average,
   no label, **dashed, amber `#B26A00`**.
5. Reference line 2: Line -> Per Cell -> Value: `Final Target (pts)` Average, **solid, black**.
6. Drag a second copy of `Pct Tested (pts)` to Columns. For that pane use the **status square** (above).
7. Filters: In Level, In Window. Row height about 50 px (drag a row taller).

### 4.5 `Teachers Title` and `Teachers` (dashboard 2)
- `Teachers Title`: text sheet, `Teachers Title` on Text, 20 pt bold. Filters: In Level, In Window.
- `Teachers` table: Rows: `teacher`. Columns, left to right, each as its own pane:
  `Tracked Students` (Text), `Tested Students` (Text), `Not Tested` (Text, **bold amber `#B26A00`**),
  `Pct Tested (pts)` (Bar, Color `Status`, Label), and a last copy of `Pct Tested (pts)` as the **status square**.
  Sort Rows by `Pct Tested (pts)` ascending (worst first). Filters: In Level, In Window.
  Column headers: rename to "Tracked", "Tested", "Not tested", "% tested", "Status".

### 4.6 `Untested Students` (dashboard 3)
- Text table. Rows (in order): `grade`, `teacher`, `student_name`, `student_id`, `level`, `probes_in_window`, `last_probe_date`.
  Show all as discrete (right-click -> Discrete).
- Filters: In Level, In Window, and `tested` = **0** (drag `tested` to Filters -> Select from list -> 0). This list works for
  **any window**: for a closed window it shows who missed it.
- `Untested Title` sheet: text sheet with `Untested Title`; filters In Level, In Window. Do **not** filter `tested` = 0 on this
  sheet (it computes Not Tested itself).
- Rename headers: Grade, Teacher, Student, ID, Level, Probes this window, Last probe.

### 4.7 `Heat Grid` (dashboard 4)
1. Columns: `window_label` (Sort -> Field -> `window_id` Minimum, ascending). Rows: `grade`, `teacher`.
2. Marks: Square. Color: `Status`. Text: `Cell Text`. Size: full. Label font white, bold.
3. Filter: In Level only (all windows show). Open item: to hide window 1 (probes start 9/18), also filter `window_id` != 1.

### 4.8 Student detail sheets
The page must **always show the student**, even one who has no probes. So the header, the message and the window history
come from the main data source (**APM DIBELS**, where every tracked student has a row for every window), and only the
probe table and chart come from **APM Probes**. Every sheet is filtered to the student clicked on dashboard 3 by the action
in section 7. Build the student detail fields in section 3 first.

- `Student Header` (**APM DIBELS**): text sheet. Text lines: `student_name` (20 pt bold), then `grade`, `teacher`, `level`, and
  `gender`, `race`, `hispanic_latino`, `iep_status`, `ell_status` (12 pt gray `#5E6674`). Put the fields on the Text shelf
  as ATTR (all values are the same for one student). Filters: the student action only.
- `Student Message` (**APM DIBELS**): Marks **Square** sized to fill the sheet, Label = `Student Message` (white, bold, 16 pt),
  Color = `Student Msg State`. Filters: **In Level**, **In Window**, plus the student action. This is the line that tells
  the teacher what to do.
- `Window History` (**APM DIBELS**): Rows: `window_label` (sorted by `window_id`), then as text columns `start_date`, `end_date`,
  `probes_in_window`, `last_probe_date`, and a last column as the **status square** using `Window Row State`.
  Filters: **In Level** and the student action (all windows show). Headers: Window, Opens, Closes, Probes, Last probe, Status.
- `Probe History` (**APM Probes**): text table.
  Rows (in order): `measure`, `probe_number`, `probe_date`, `window_label`.
  Columns (Measure Values): `MIN(total_probes)`, `MIN(score)`, `MIN(aimline_value_by_date)`, `MIN(growth_goal_set)`;
  put `aimline_status` on Rows as a discrete field and on **Color** (set **Below** = `#C62828`, **At or Above** =
  `#2E7D32`, **Not available** = `#5E6674`).
  Sort `measure` A-Z and `probe_number` ascending. Rename headers: Measure, Probe, Date, Window, Total probes, Score,
  Aimline value, Goal.
- `Score Over Time` (optional chart): Columns `probe_date` (exact date, discrete off), Rows `score`, Color `measure`.
  Add `aimline_value_by_date` as a dashed line (dual axis, synchronize axes) and a reference line per measure at `growth_goal_set`
  (average).

## 5. Dashboards
For each: **Size -> Fixed size -> Custom -> 1200 x 820**. Drag objects from the left pane as **Floating**
(or click the object's down arrow -> Floating), then set **Position and Size** in the Layout pane. Add parameter
controls by clicking a sheet's down arrow -> **Parameters** -> the parameter. Set `p_Level` to **Single Value (List)**,
`p_Window` to **Single Value (Dropdown)**.

### Dashboard 1: DIBELS Grades (1200 x 820)
| Object | x | y | w | h |
|---|---|---|---|---|
| Title text: "DIBELS progress monitoring" (22 pt bold) | 20 | 10 | 700 | 40 |
| How it works (Show/Hide button, section 6) | 1060 | 12 | 120 | 32 |
| Navigation button "Heat grid" -> `Heat Grid` | 840 | 12 | 200 | 32 |
| `p_Level` control | 20 | 56 | 240 | 40 |
| `p_Window` control | 280 | 56 | 260 | 40 |
| `Data As Of` | 810 | 56 | 370 | 40 |
| `Tile Tested` | 20 | 106 | 282 | 110 |
| `Tile Not Tested` | 312 | 106 | 282 | 110 |
| `Tile Last Window` | 604 | 106 | 282 | 110 |
| `Tile Next Checkpoint` | 896 | 106 | 282 | 110 |
| `Card 0` | 20 | 226 | 224 | 96 |
| `Card 1` | 254 | 226 | 224 | 96 |
| `Card 2` | 488 | 226 | 224 | 96 |
| `Card 3` | 722 | 226 | 224 | 96 |
| `Card 4` | 956 | 226 | 224 | 96 |
| `Compared To` | 20 | 332 | 1160 | 44 |
| `Grade Bars` | 20 | 386 | 1160 | 400 |

### Dashboard 2: Teachers (1200 x 820)
| Object | x | y | w | h |
|---|---|---|---|---|
| Back button (Navigation -> "DIBELS Grades") | 20 | 56 | 160 | 40 |
| `p_Level` control | 200 | 56 | 240 | 40 |
| `p_Window` control | 460 | 56 | 260 | 40 |
| `Data As Of` | 810 | 56 | 370 | 40 |
| How it works button | 1060 | 12 | 120 | 32 |
| `Teachers Title` | 20 | 106 | 600 | 40 |
| `Compared To` | 20 | 150 | 1160 | 44 |
| `Teachers` | 20 | 204 | 1160 | 580 |

### Dashboard 3: Untested Students (1200 x 820)
| Object | x | y | w | h |
|---|---|---|---|---|
| Back button (Navigation -> "Teachers") | 20 | 56 | 160 | 40 |
| `p_Level` control | 200 | 56 | 240 | 40 |
| `p_Window` control | 460 | 56 | 260 | 40 |
| `Data As Of` | 810 | 56 | 370 | 40 |
| How it works button | 1060 | 12 | 120 | 32 |
| `Untested Title` | 20 | 106 | 600 | 40 |
| `Compared To` | 20 | 150 | 1160 | 44 |
| `Untested Students` | 20 | 204 | 1160 | 580 |

### Dashboard 4: Heat Grid (1200 x 820)
| Object | x | y | w | h |
|---|---|---|---|---|
| Back button (Navigation -> "DIBELS Grades") | 20 | 56 | 160 | 40 |
| `p_Level` control | 200 | 56 | 240 | 40 |
| `Data As Of` | 810 | 56 | 370 | 40 |
| How it works button | 1060 | 12 | 120 | 32 |
| Text: "Green = 95% or more. Amber = below 95% in the open window. Red = below 95% after the window closed. Gray = upcoming." (12 pt) | 20 | 106 | 1160 | 36 |
| `Heat Grid` | 20 | 150 | 1160 | 630 |

### Dashboard 5: Student Detail (1200 x 820)
| Object | x | y | w | h |
|---|---|---|---|---|
| Back button (Navigation -> "Untested Students") | 20 | 56 | 160 | 40 |
| `p_Level` control | 200 | 56 | 240 | 40 |
| `p_Window` control | 460 | 56 | 260 | 40 |
| `Data As Of` | 810 | 56 | 370 | 40 |
| How it works button | 1060 | 12 | 120 | 32 |
| `Student Header` | 20 | 106 | 1160 | 100 |
| `Student Message` | 20 | 214 | 1160 | 50 |
| `Window History` | 20 | 274 | 1160 | 200 |
| `Probe History` | 20 | 484 | 1160 | 160 |
| `Score Over Time` | 20 | 654 | 1160 | 140 |

The page always shows who the student is and what they need to do this window. If the student has no probes, `Probe
History` and `Score Over Time` stay empty, and the `Student Message` says they have not been tested and their teacher
needs to give a probe. A student with no probes all year gets an extra line saying so.

## 6. "How it works" pop-up (all five dashboards)
1. Drag a **Vertical** container floating. Position **x 300, y 110, w 600, h 560**. Fill it with a **Text** object containing
   the text of [dashboard_how_it_works.md](dashboard_how_it_works.md). Set background white, border amber `#B26A00`.
2. Add a **Button** object (Navigation/Show-Hide): floating at **x 1060, y 12, w 120, h 32**, label "How it works",
   Button type = **Show/Hide**, target = the container. Hidden by default.

`output/dashboard_guide.html` is a longer plain-language explanation. Host it somewhere your users can open it and add a link to it
in the pop-up.

## 7. Click-through actions
Dashboard 1 -> 2 (**Dashboard -> Actions -> Add Action**):
1. **Filter** "Grade to Teachers": Source = dashboard `DIBELS Grades`, sheet `Grade Bars`; Run on **Select**;
   Target = dashboard `Teachers`, all sheets; Clearing the selection = **Show all values**; Fields: `grade` to `grade`.
2. **Go to Sheet** "Open Teachers": Source `Grade Bars`; Run on **Select**; Target = dashboard `Teachers`.

Dashboard 2 -> 3:
3. **Filter** "Teacher to Students": Source `Teachers`; Run on **Select**; Target = dashboard `Untested Students`,
   all sheets; Fields: `grade` to `grade`, `teacher` to `teacher`; clearing = Show all values.
4. **Go to Sheet** "Open Students": Source `Teachers`; Run on **Select**; Target = dashboard `Untested Students`.

Dashboard 3 -> 5:
5. **Filter** "Student to Detail": Source `Untested Students`; Run on **Select**; Target = dashboard `Student Detail`,
   all sheets (both data sources); Fields: `student_id` to `student_id` (use **Selected Fields** and map `student_id`; both
   sources have a field with this exact name, which is what lets a filter cross data sources); clearing = **Exclude all values**.
6. **Go to Sheet** "Open Student Detail": Source `Untested Students`; Run on **Select**; Target = dashboard `Student Detail`.

Note: Tableau fires an action when you click anywhere in the teacher row. The **Not tested** column is bold amber to
show it is the one to click.

## 8. Check your numbers
Compare the dashboard with the CSV. In a spreadsheet or pandas, filter `dibels_student_window.csv` to one `level` and one
`window_id`, then for each `grade` count the rows and sum `tested`. The dashboard's tracked, tested and percent should match
exactly. Then confirm:

- **Last window tile:** the same calculation for the previous `window_id`.
- **Checkpoint strip:** the `cp1_*` to `cp4_*` columns of any row in that window.
- **Status:** compare the percent with `current_target_pct`; the gap decides On track, Behind or Off track.

If the numbers differ, check that `In Level` and `In Window` are on the sheet's Filters shelf, and check the parameters.

To see every status colour without real data, run `python demo/make_fake_data.py`: its fake grades are placed to show green, amber
and red bars.

## 9. Publish and refresh
- Publish to your Tableau Server or Tableau Cloud as usual, with a project and name of your choosing.
- **Refresh routine:** run `python -m apm_metrics.build_dibels` -> run `python tests/verify_dibels.py` -> check `data_quality.xlsx` ->
  Tableau Desktop Data -> refresh (F5) -> save -> republish. The window, checkpoint and statuses move on their own
  because the pipeline stamps `as_of_date` on every run.
- Run the pipeline on the days you want the dashboard to update. A dated copy is saved to
  `output/history/` each run.

## 10. If something looks wrong
| Symptom | Likely cause |
|---|---|
| Blank sheet | `p_Window` set above the level's windows (Below has 1-4), or `In Window` filter missing |
| All statuses "Not started" | `as_of_date` earlier than the window start: rerun the pipeline |
| Percent prints 83.29999% on Server | Used `STR(ROUND())` on a decimal; use number formatting instead (`0"%"`) |
| Grade order 1,2,3,4,5,K | Grade sort not set to manual (section 1, step 4) |
| Strip card shows `*` | Sheet is not filtered to one window: add In Level and In Window |
| Clicking a grade doesn't open Teachers | The Go to Sheet action (7.2) is missing |
| Student detail page is empty | The student filter action (7.5) isn't set to target both data sources, or `student_id` is typed differently in the two files |
| Status shows `*` or null | Mixed levels or windows are in the view: add In Level and In Window (the heat grid needs only In Level) |
