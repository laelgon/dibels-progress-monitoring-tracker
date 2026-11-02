"""Finds and reads the raw exports in the data folders. Every value is read as text so IDs never lose
leading zeros; numbers and dates are converted where used."""

import re
from datetime import datetime
from io import StringIO
from pathlib import Path

import pandas as pd

from apm_metrics.utils import config, quality


def read_any(path: Path) -> pd.DataFrame:
    """CSV (comma- OR tab-delimited) or Excel, all values as text, headers trimmed."""
    suffix = path.suffix.lower()
    if suffix == ".xls":
        df = pd.read_excel(path, dtype=str, engine_kwargs={"logfile": StringIO()}).fillna("")
    elif suffix == ".xlsx":
        df = pd.read_excel(path, dtype=str).fillna("")
    else:
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp1252")
        first = text.split("\n", 1)[0]
        sep = "\t" if first.count("\t") > first.count(",") else ","
        df = pd.read_csv(StringIO(text), sep=sep, dtype=str, keep_default_na=False)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def to_datetime(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values.astype(str).str.strip(), errors="coerce", format="mixed")


def norm_grade(values: pd.Series) -> pd.Series:
    """'Pre-K', 'PK', '-1' (PowerSchool) -> 'PK'; 'K', 'KG', 'Kindergarten', '0' -> 'K'; '3', '03' -> '3'."""
    s = values.astype(str).str.strip().str.lower()
    is_pk = s.isin(["pk", "-1", "-2"]) | s.str.startswith("pre")
    is_k = s.isin(["k", "kg", "kindergarten", "0", "00"]) | s.str.startswith("kinder")
    number = s.str.extract(r"(\d+)", expand=False).str.lstrip("0")
    return number.where(~is_k, "K").where(~is_pk, "PK").fillna("")


def keep_k5(df: pd.DataFrame, grade_col: str, source: str) -> pd.DataFrame:
    """Keeps grades K-5 (config/rules.yaml grades_in_scope) and notes what was dropped. grade_col must be
    normalized. Safe to run even when the export was already filtered."""
    scope = {str(g) for g in config.rules()["grades_in_scope"]}
    out = ~df[grade_col].isin(scope)
    if out.any():
        quality.add("Rows outside K-5 skipped",
                    f"Grades {sorted(df.loc[out, grade_col].unique())} - progress monitoring is K-5 only.",
                    source=source, count=int(out.sum()))
    return df[~out].copy()


# Raw exports are being renamed to  source_schoolyear_window_pulldate[_HHMM].ext  (for example
# dibels_pm_2026-27_boy-moy_2026-10-26_1333.csv, powerschool_cc_2026-27_boy_2026-10-21.txt). Both the old and the new
# names are accepted, so the pipeline works before, during and after the rename:
#   DIBELS old  dibels8_PM_2026-2027_BOY-MOY_grades-KG-..-05_2026-10-26_13-33-55.csv
#   PowerSchool old  cc-10.21.26.txt
_STAMP_OLD_DIBELS = re.compile(r"(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})\.[A-Za-z]+$")
_STAMP_NEW = re.compile(r"(\d{4})-(\d{2})-(\d{2})(?:_(\d{2})(\d{2}))?\.[A-Za-z]+$")          # pull date, optional _HHMM
_STAMP_OLD_CC = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})")


def _export_stamp(path: Path) -> datetime:
    """Pull date (and time, when the name has one) read from the file name, old or new pattern."""
    name = path.name
    m = _STAMP_OLD_DIBELS.search(name)
    if m:
        return datetime(*map(int, m.groups()))
    m = _STAMP_NEW.search(name)
    if m:
        y, mo, d, hh, mm = m.groups()
        return datetime(int(y), int(mo), int(d), int(hh or 0), int(mm or 0))
    m = _STAMP_OLD_CC.search(name)
    if m:
        mo, d, y = map(int, m.groups())
        return datetime(y + 2000 if y < 100 else y, mo, d)
    return datetime.fromtimestamp(path.stat().st_mtime)


def export_pattern(kind: str, school_year: str | None = None, period: str | None = None) -> str:
    """Regex that matches a raw export's file name in the OLD or the NEW naming pattern.

    kind "cc" (PowerSchool current courses), "bm" (DIBELS benchmark; `period` such as "BOY") or "pm" (progress monitoring).
    `school_year` is the config value "2026-2027"; the new names write it as "2026-27".
    The grade list that used to be in DIBELS names (grades-KG-...) is gone: grades come from the file contents.
    """
    if kind == "cc":
        return r"^(?:cc[-_ ]|powerschool_cc_)"
    m = re.match(r"(\d{4})-(\d{2,4})$", str(school_year))
    if not m:
        raise ValueError(f"school_year should look like 2026-2027, got {school_year!r}")
    start = int(m[1])
    long_year, short_year = f"{start}-{start + 1}", f"{start}-{m[2][-2:]}"
    if kind == "pm":
        return rf"(?:dibels8_PM_{long_year}_|^dibels_pm_{short_year}_)"
    if kind == "bm":
        per = period or ""
        # old names: ..._BM_2026-2027_BOY_...   new names: dibels_bm_2026-27_boy_... (boy-moy also counts as a BOY export)
        return rf"(?:dibels8_BM_{long_year}_{per}_|^dibels_bm_{short_year}_{per.lower()}(?:-[a-z]+)*_)"
    raise ValueError(f"unknown export kind {kind!r}")


def latest_file(folder: Path, pattern: str, source: str) -> Path | None:
    """Newest export (by date in the filename) whose name matches the regex `pattern`."""
    if not folder.exists():
        quality.add("Source folder missing", str(folder), source=source)
        return None
    matches = [p for p in folder.iterdir()
               if p.is_file() and re.search(pattern, p.name, re.I) and p.suffix.lower() in {".csv", ".txt", ".text", ".xls", ".xlsx"}]
    if not matches:
        quality.add("Source file missing", f"No file in {folder} matching /{pattern}/.", source=source)
        return None
    return max(matches, key=_export_stamp)


def all_files(folder: Path, pattern: str, source: str) -> list[Path]:
    """Every export whose name matches the regex `pattern`, oldest to newest (by the date in the filename)."""
    if not folder.exists():
        quality.add("Source folder missing", str(folder), source=source)
        return []
    matches = [p for p in folder.iterdir()
               if p.is_file() and re.search(pattern, p.name, re.I) and p.suffix.lower() in {".csv", ".txt", ".text", ".xls", ".xlsx"}]
    if not matches:
        quality.add("Source file missing", f"No file in {folder} matching /{pattern}/.", source=source)
    return sorted(matches, key=_export_stamp)


def export_date(path: Path) -> datetime:
    return _export_stamp(path)
