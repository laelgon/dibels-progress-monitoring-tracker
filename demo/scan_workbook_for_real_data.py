"""Scans a Tableau workbook (.twb or .twbx) or a folder for REAL data before you publish it publicly.

    python demo/scan_workbook_for_real_data.py "C:/path/to/Workbook.twbx" [--also-search WORD ...]

It looks for (real values are built in memory from the real roster and real Tableau CSVs named under real_data in demo_config.yaml,
or in the DEMO_REAL_CC_FOLDER and DEMO_REAL_TABLEAU_FOLDER environment variables; they are NEVER printed):
  * real student names ("First Last" and "Last, First"), real teacher names ("Last, First"), real student ids
  * where the workbook came from: a repository-location record (a Tableau Server publish record), an xml:base or any other web
    address that is not a standard Tableau/W3C namespace, and any path into the real data folders
  * any extra words you pass with --also-search, or put in the SCAN_EXTRA_WORDS environment variable (comma-separated), for example
    your organization's name. They are not stored in this project.
It searches every text file inside a .twbx and the raw bytes of any .hyper extract. Prints, per file, hits per category and the XML
tag they were inside, then PASS or FAIL (exit code 1 on FAIL). A 5-9 digit number equal to a real student id is only "possible".
"""
import argparse
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

import settings

REAL = settings.real_data_folders()          # may be empty: the structural checks (server address, publish record) still run
TEXT_EXT = {".twb", ".csv", ".txt", ".xml", ".tds", ".json", ".html", ".htm", ".svg", ".py", ".md", ".yaml", ".yml"}
# web addresses every Tableau workbook legitimately contains
ALLOWED_HOSTS = {"www.w3.org", "www.tableausoftware.com", "tableausoftware.com", "www.tableau.com", "tableau.com", "public.tableau.com",
                 "community.tableau.com", "help.tableau.com", "localhost", "www.sas.com", "fonts.googleapis.com", "fonts.gstatic.com"}


def real_sets():
    names, teachers, ids = set(), set(), set()
    for f in sorted(Path(REAL["cc_folder"]).glob("*")) if REAL.get("cc_folder") else []:
        if f.suffix.lower() in (".txt", ".text"):
            d = pd.read_csv(f, sep="\t", dtype=str, keep_default_na=False)
            first, last = d["[01]First_Name"].str.strip(), d["[01]Last_Name"].str.strip()
            names |= {f"{a} {b}".lower() for a, b in zip(first, last) if a and b} | {f"{b}, {a}".lower() for a, b in zip(first, last) if a and b}
            teachers |= {t.strip().lower() for t in d["[05]LastFirst"] if t.strip()}
            ids |= {i for i in d["[01]Student_Number"] if len(i) >= 5}
    for f in Path(REAL["tableau_folder"]).glob("*.csv") if REAL.get("tableau_folder") else []:
        d = pd.read_csv(f, dtype=str, keep_default_na=False)
        for c in ("student_name", "student_name_last_first"):
            if c in d.columns:
                names |= {v.strip().lower() for v in d[c] if v.strip()}
        if "teacher" in d.columns:
            teachers |= {v.strip().lower() for v in d["teacher"] if v.strip() and not v.startswith("(")}
        if "student_id" in d.columns:
            ids |= {v for v in d["student_id"] if len(v) >= 5}
    return names, teachers, ids


def real_paths():
    """Lower-case, forward-slash spellings of the real data folders (a connection to one of these means real data is attached)."""
    return [str(Path(p)).replace("\\", "/").lower() for p in REAL.values()]


def tag_at(text, idx):
    """Name of the XML tag the position is inside (to locate a hit without showing its value)."""
    lt = text.rfind("<", 0, idx)
    m = re.match(r"<\s*/?([\w:.-]+)", text[lt:lt + 80]) if lt >= 0 else None
    return m.group(1) if m else "(text)"


def scan_text(text, sets, extra_words=(), paths=None):
    names, teachers, ids = sets
    low = text.lower()
    hits, notes = defaultdict(Counter), []
    for cat, vals in (("real student names", names), ("real teacher names", teachers)):
        for v in vals:
            start = low.find(v)
            while start != -1:
                hits[cat][tag_at(text, start)] += 1
                start = low.find(v, start + len(v))
    for w in extra_words:
        start = low.find(w.lower())
        while start != -1:
            hits["extra words you asked to search"][tag_at(text, start)] += 1
            start = low.find(w.lower(), start + len(w))
    for m in re.finditer(r"<repository-location\b", text):
        hits["publish record (repository-location)"]["repository-location"] += 1
    for m in re.finditer(r"https?://([A-Za-z0-9._-]+)", text):
        if m.group(1).lower() not in ALLOWED_HOSTS:
            hits["web address that is not a standard Tableau/W3C one"][tag_at(text, m.start())] += 1
    flat = low.replace("\\\\", "/").replace("\\", "/")
    for p in (paths or real_paths()):
        for m in re.finditer(re.escape(p), flat):
            hits["path into a real data folder"][tag_at(text, min(m.start(), len(text) - 1))] += 1
    if re.search(r"(?<![\w])[a-z]:[\\/]", low) and not hits.get("path into a real data folder"):
        notes.append("a local file path appears (for example a connection to the fake CSV folder); it does not point at real data")
    for m in re.finditer(r"(?<![\w.])\d{5,9}(?![\w.])", text):
        if m.group(0) in ids:
            hits["possible real student ids"][tag_at(text, m.start())] += 1
    return hits, notes


def scan_bytes(data, sets, extra_words=()):
    names, teachers, _ = sets
    low = data.lower()
    found = Counter()
    for cat, vals in (("real student names", names), ("real teacher names", teachers)):
        for v in vals:
            if v.encode("utf-8") in low or v.encode("utf-16-le") in low:
                found[cat] += 1
    for w in extra_words:
        if w.lower().encode("utf-8") in low or w.lower().encode("utf-16-le") in low:
            found["extra words you asked to search"] += 1
    return found


def files_in(path):
    path = Path(path)
    if path.is_dir():
        for f in sorted(path.rglob("*")):
            if f.is_file():
                yield str(f.relative_to(path)), f.read_bytes()
    elif path.suffix.lower() == ".twbx":
        with zipfile.ZipFile(path) as z:
            for i in z.infolist():
                if not i.is_dir():
                    yield i.filename, z.read(i)
    else:
        yield path.name, path.read_bytes()


def main(target, extra_words=()):
    sets = real_sets()
    print(f"Scanning {target}  (checking against {len(sets[0])} real names, {len(sets[1])} real teacher names, {len(sets[2])} real ids; none are printed)\n")
    failed, possible, notes = False, False, set()
    for name, data in files_in(target):
        ext = Path(name).suffix.lower()
        if ext in TEXT_EXT:
            hits, file_notes = scan_text(data.decode("utf-8", errors="ignore"), sets, extra_words)
            notes |= set(file_notes)
            if hits:
                for cat, tags in hits.items():
                    print(f"HIT  {name}: {cat}: {sum(tags.values())} hit(s) inside tags {dict(tags.most_common(5))}")
                    if cat == "possible real student ids":
                        possible = True
                    else:
                        failed = True
            else:
                print(f"ok   {name}")
        elif ext in (".hyper", ".tde"):
            found = scan_bytes(data, sets, extra_words)
            print(f"{'HIT ' if found else 'ok  '} {name} (binary extract): {dict(found) if found else 'no real strings found by byte search'}")
            notes.add(f"{name} is a data extract. The byte search is not a full check: also open it in Tableau and look at View Data.")
            failed = failed or bool(found)
        else:
            print(f"skip {name} ({ext or 'no extension'}; binary, not scanned)")
    print()
    for n in sorted(notes):
        print("NOTE:", n)
    if possible:
        print("NOTE: some 5-9 digit numbers equal real student ids; check whether they are ids or coincidences.")
    print("\nFAIL: real data or its origin found. Do NOT publish." if failed else "\nPASS: no real names, teachers, origins or paths found." + ("" if not possible else " (ids flagged above: check them)"))
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--also-search", nargs="*", default=[], help="extra words to look for, for example your organization's name")
    a = ap.parse_args()
    env = [w.strip() for w in os.environ.get("SCAN_EXTRA_WORDS", "").split(",") if w.strip()]
    sys.exit(main(a.target, a.also_search + env))
