"""Checks the safety scanner with made-up workbook text (no real data needed).

    python tests/test_scanner.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "demo"))
import scan_workbook_for_real_data as s  # noqa: E402

fails = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"  - {detail}" if detail else ""))
    if not ok:
        fails.append(name)


SETS = ({"pat person", "person, pat"}, {"teacher, real"}, {"4455667"})
PATHS = ["d:/data/real_folder"]
CLEAN = "<workbook xmlns:user='http://www.tableausoftware.com/xml/user'><connection directory='D:/data/fake_demo' filename='a.csv'/></workbook>"


def run(text, extra=()):
    hits, notes = s.scan_text(text, SETS, extra, PATHS)
    return {k: sum(v.values()) for k, v in hits.items()}, notes


h, n = run(CLEAN)
check("a clean workbook has no hits", not h, str(h))
check("a path to a fake folder is only a note", len(n) == 1)
h, _ = run(CLEAN.replace("<workbook ", "<workbook xml:base='https://tableau.example-server.org' "))
check("an xml:base server address is caught", "web address that is not a standard Tableau/W3C one" in h, str(h))
h, _ = run(CLEAN + "<repository-location id='x' site='y'/>")
check("a repository-location publish record is caught", "publish record (repository-location)" in h)
h, _ = run(CLEAN + "<member value='Pat Person'/>")
check("a real student name is caught (any case)", h.get("real student names") == 1, str(h))
h, _ = run(CLEAN + "<member value='Teacher, Real'/>")
check("a real teacher name is caught", h.get("real teacher names") == 1)
h, _ = run(CLEAN + "<value>4455667</value><value>14455667</value>")
check("a real student id is flagged as possible, but only as a whole number", h.get("possible real student ids") == 1, str(h))
h, _ = run(CLEAN.replace("fake_demo", "real_folder"))
check("a connection into a real data folder is caught", h.get("path into a real data folder") == 1, str(h))
h, _ = run(CLEAN + "<title>My Org</title>", extra=("my org",))
check("extra words passed on the command line are caught", h.get("extra words you asked to search") == 1)

print(f"\n{len(fails)} check(s) failed" if fails else "\nAll checks passed")
sys.exit(1 if fails else 0)
