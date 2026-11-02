"""Cleans a COPY of a Tableau workbook (.twb) before it goes public: removes where it was published from and any saved drill-down.

    python demo/clean_workbook_copy.py "C:/path/to/Workbook copy.twb"

Close the workbook in Tableau first. A backup "<name> - backup before cleanup.twb" is written next to it, and the file is changed in
place. Never run this on the original workbook, only on the demo copy. It removes:
  * the server address in the workbook header (xml:base)
  * the repository-location record (the site and workbook id from when it was published to a server)
  * saved action filters (the drill-down from grade to teacher to student) and their entries in each view
  * saved mark selections (the highlighted grade, teacher, student, measure or card), so the dashboard opens un-filtered
Then it checks the XML is still valid. Run scan_workbook_for_real_data.py afterwards.
"""
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main(path):
    p = Path(path)
    if p.suffix.lower() != ".twb":
        sys.exit("Give a .twb file (save a packaged .twbx from Tableau after cleaning).")
    backup = p.with_name(p.stem + " - backup before cleanup.twb")
    shutil.copy2(p, backup)
    with open(p, encoding="utf-8", newline="") as f:
        t = f.read()
    before = len(t)
    counts = {}

    def sub(name, pattern, repl, flags=0):
        nonlocal t
        t, n = re.subn(pattern, repl, t, flags=flags)
        counts[name] = n

    sub("server address (xml:base) removed", r"(<workbook\b[^>]*?)\s+xml:base='[^']*'", r"\1")
    sub("repository-location removed", r"[ \t]*<repository-location\b[^>]*/>[ \t]*\r?\n?", "")
    sub("saved action filters removed", r"[ \t]*<filter class='categorical' column='\[[^']*\]\.\[Action \([^']*\)\]'>.*?</filter>[ \t]*\r?\n?", "", re.S)
    sub("action entries in view slices removed", r"[ \t]*<column>\[[^\]]*\]\.\[Action \([^)]*\)\]</column>[ \t]*\r?\n?", "")
    sub("saved mark selections removed", r"[ \t]*<selection-collection\b.*?</selection-collection>[ \t]*\r?\n?", "", re.S)
    sub("empty slices removed", r"[ \t]*<slices>\s*</slices>[ \t]*\r?\n?", "")
    ET.fromstring(t.encode("utf-8"))                         # must still be valid XML before anything is written
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(t)
    for k, v in counts.items():
        print(f"{k}: {v}")
    print(f"characters {before} -> {len(t)} | backup: {backup}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
