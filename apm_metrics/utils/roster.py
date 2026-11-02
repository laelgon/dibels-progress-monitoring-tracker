"""PowerSchool roster: the students who count (denominator) and each student's homeroom teacher.

Input: Direct Database Export of the CC table (e.g. "powerschool_cc_2026-27_boy_2026-10-21.txt") - every course enrollment, current
and past. Only enrollments active on the export date are used:

    DateEnrolled <= export date < DateLeft

A student's homeroom is their active section whose Section_Number ends with "HR" (config/rules.yaml); that
section's teacher is the accountable teacher.
"""

import pandas as pd

from apm_metrics.utils import config, data_loader, quality

FIELDS = {
    "student_id": "[01]Student_Number", "last_name": "[01]Last_Name", "first_name": "[01]First_Name",
    "grade": "[01]Grade_Level", "section_number": "Section_Number", "teacher": "[05]LastFirst",
    "date_enrolled": "DateEnrolled", "date_left": "DateLeft",
}


def load_roster() -> tuple[pd.DataFrame, pd.Timestamp | None]:
    path = data_loader.latest_file(config.source_dir("powerschool_cc"), data_loader.export_pattern("cc"), "powerschool_cc")
    if path is None:
        return pd.DataFrame(), None
    raw = data_loader.read_any(path)
    missing = [c for c in FIELDS.values() if c not in raw.columns]
    if missing:
        raise SystemExit(f"{path.name} is missing PowerSchool fields {missing}. See README for the export field list.")
    df = raw[list(FIELDS.values())].rename(columns={v: k for k, v in FIELDS.items()})
    as_of = pd.Timestamp(data_loader.export_date(path))

    enrolled, left = data_loader.to_datetime(df["date_enrolled"]), data_loader.to_datetime(df["date_left"])
    active = df[(enrolled <= as_of) & (left > as_of)].copy()
    active["_enrolled"] = enrolled[active.index]
    active["teacher"] = active["teacher"].str.strip()

    suffix = str(config.rules()["homeroom_section_suffix"]).upper()
    homerooms = active[active["section_number"].str.strip().str.upper().str.endswith(suffix)].sort_values("_enrolled")
    doubled = homerooms.groupby("student_id").filter(lambda g: len(g) > 1)
    if len(doubled):
        quality.add("Student in more than one homeroom",
                    "Fix in PowerSchool; the most recently enrolled homeroom is used. Students: "
                    + quality.sample_ids(doubled["student_id"]), source="powerschool_cc",
                    count=doubled["student_id"].nunique())
    homerooms = homerooms.drop_duplicates("student_id", keep="last").set_index("student_id")

    students = active.drop_duplicates("student_id").set_index("student_id")
    no_hr = students.index.difference(homerooms.index)

    out = pd.DataFrame(index=students.index)
    out["student_name"] = students["first_name"].str.strip() + " " + students["last_name"].str.strip()
    out["student_name_last_first"] = students["last_name"].str.strip() + ", " + students["first_name"].str.strip()
    out["grade"] = data_loader.norm_grade(students["grade"])
    out["homeroom"] = homerooms["section_number"].str.strip().str[: -len(suffix)]
    out["teacher"] = homerooms["teacher"]
    out = out.reset_index()
    out["homeroom"] = out["homeroom"].fillna("")
    out["teacher"] = out["teacher"].fillna("")

    out = data_loader.keep_k5(out, "grade", "powerschool_cc")
    kept_no_hr = [s for s in no_hr if s in set(out["student_id"])]
    if kept_no_hr:
        quality.add(f"No active '{suffix}' homeroom section",
                    "These students appear with a blank teacher. Students: " + quality.sample_ids(kept_no_hr),
                    source="powerschool_cc", count=len(kept_no_hr))
        out.loc[out["student_id"].isin(kept_no_hr), "teacher"] = "(no homeroom)"
    return out, as_of
