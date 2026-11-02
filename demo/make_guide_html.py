"""Builds the "How this dashboard works" guide for the FAKE-DATA demo dashboard as one self-contained HTML file.

    python demo/make_guide_html.py

Reads only the fake CSVs (so the example numbers match the demo), writes APM_KPI_Demo_Guide.html next to them. No external files,
fonts or scripts: it works offline and inside an iframe. Nothing real is read.
"""
from html import escape as e

import pandas as pd

import settings

FAKE = settings.OUT_DIR
OUT = FAKE / "APM_KPI_Demo_Guide.html"

def facts():
    w = pd.read_csv(FAKE / "dibels_student_window.csv", dtype=str, keep_default_na=False)
    p = pd.read_csv(FAKE / "dibels_probes.csv", dtype=str, keep_default_na=False)
    w["tested"] = w["tested"].astype(int)
    cur = w[(w["level"] == "Well Below") & (w["window_state"] == "Current")]
    t = cur.groupby(["grade", "teacher"]).agg(n=("student_id", "nunique"), tested=("tested", "sum")).reset_index()
    t["pct"] = (100 * t["tested"] / t["n"]).round(0).astype(int)
    low, high = t.sort_values("pct").iloc[0], t.sort_values("pct").iloc[-1]
    missing = cur[(cur["teacher"] == low["teacher"]) & (cur["tested"] == 0)]
    return {
        "tracked": w["student_id"].nunique(), "teachers": w["teacher"].nunique(), "as_of": w["as_of_date"].iloc[0],
        "data_as_of": w["data_as_of"].iloc[0], "window": cur["window_label"].iloc[0], "start": cur["start_date"].iloc[0], "end": cur["end_date"].iloc[0],
        "pct": round(100 * cur["tested"].mean()), "n_cur": len(cur), "tested_cur": int(cur["tested"].sum()),
        "low_t": low["teacher"], "low_pct": low["pct"], "low_grade": low["grade"], "high_t": high["teacher"], "high_pct": high["pct"],
        "n95": int((t["pct"] >= 95).sum()), "nt": len(t), "miss_student": missing["student_name"].iloc[0] if len(missing) else "",
        "probe_rows": len(p), "probe_students": p["student_id"].nunique(), "p_first": p["probe_date"].min(), "p_last": p["probe_date"].max(),
    }


CSS = """
:root{--bg:#f4f6f9;--card:#fff;--ink:#1b2430;--mut:#5a6675;--line:#dfe4ea;--blue:#1f5fa8;--green:#2E7D32;--amber:#B26A00;--red:#C62828;--gray:#5E6674;--soft:#eef3f9}
@media (prefers-color-scheme:dark){:root{--bg:#12161b;--card:#1a2027;--ink:#e8ecf0;--mut:#9aa6b3;--line:#2b343e;--blue:#6aa6e6;--soft:#202a35}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 "Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:18px 18px 56px}
.hero{background:linear-gradient(135deg,#1f5fa8,#2a7bd1);color:#fff;border-radius:14px;padding:22px 24px}
.hero h1{margin:0 0 4px;font-size:26px}.hero p{margin:0;opacity:.95}
.fake{display:inline-block;background:#fff;color:#C62828;font-weight:700;letter-spacing:.04em;border-radius:20px;padding:3px 12px;font-size:12px;margin-bottom:10px}
.toc{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 4px}
.toc a{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:5px 13px;color:var(--ink);text-decoration:none;font-size:13px}
.toc a:hover{border-color:var(--blue);color:var(--blue)}
section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px 22px;margin-top:18px}
h2{margin:0 0 4px;font-size:20px}h2 small{display:block;color:var(--mut);font-weight:400;font-size:13px;margin-top:2px}
h3{margin:18px 0 6px;font-size:15px}
p{margin:8px 0}ul,ol{margin:8px 0;padding-left:22px}li{margin:3px 0}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));margin-top:12px}
.tile{background:var(--soft);border-radius:10px;padding:12px 14px}.tile b{display:block;font-size:22px}.tile span{color:var(--mut);font-size:12.5px}
.pill{display:inline-block;color:#fff;border-radius:14px;padding:2px 12px;font-size:12.5px;font-weight:600;white-space:nowrap}
.g{background:var(--green)}.a{background:var(--amber)}.r{background:var(--red)}.n{background:var(--gray)}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:8px 0}th,td{border-bottom:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}
th{color:var(--mut);font-weight:600;background:var(--soft)}
.note{background:var(--soft);border-left:4px solid var(--blue);border-radius:6px;padding:9px 13px;margin:12px 0;font-size:14px}
.warn{border-left-color:var(--amber)}
.flow{display:flex;flex-wrap:wrap;gap:10px;align-items:stretch;margin:14px 0}
.step{flex:1 1 180px;background:var(--soft);border:1px solid var(--line);border-radius:12px;padding:12px 14px;position:relative}
.step b{display:block;color:var(--blue)}.step em{display:block;color:var(--mut);font-style:normal;font-size:12.5px;margin-top:4px}
.step:not(:last-child)::after{content:"\\279C";position:absolute;right:-14px;top:42%;color:var(--mut);font-size:16px;background:var(--bg);border-radius:50%}
details{background:var(--soft);border-radius:10px;padding:9px 14px;margin:10px 0}summary{cursor:pointer;font-weight:600}
.try{background:#fff8e6;border:1px dashed var(--amber);border-radius:10px;padding:10px 14px;margin:12px 0;font-size:14px;color:#4a3300}
@media (prefers-color-scheme:dark){.try{background:#2a2310;color:#f1dca6}}
code{background:var(--soft);border-radius:4px;padding:1px 5px;font-size:13px}
.foot{color:var(--mut);font-size:12.5px;margin-top:22px}
a.top{float:right;font-size:12px;color:var(--mut)}
svg text{font:13px "Segoe UI",Arial,sans-serif;fill:var(--ink)}svg .mut{fill:var(--mut)}
@media print{.toc,a.top{display:none}body{background:#fff}section{break-inside:avoid}}
"""


def pill(cls, text):
    return f'<span class="pill {cls}">{e(text)}</span>'


def diagram():
    box = lambda x, y, w, t, sub, c: (f'<rect x="{x}" y="{y}" width="{w}" height="66" rx="10" fill="{c}" opacity=".14" stroke="{c}"/>'
                                      f'<text x="{x + w / 2}" y="{y + 28}" text-anchor="middle" font-weight="600">{t}</text>'
                                      f'<text class="mut" x="{x + w / 2}" y="{y + 49}" text-anchor="middle">{sub}</text>')
    arrow = lambda x1, y1, x2, y2: f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#8a95a3" stroke-width="2" marker-end="url(#ah)"/>'
    return ('<svg viewBox="0 0 900 250" width="100%" role="img" aria-label="Data flow: three exports go through a build script into two files that feed the dashboard">'
            '<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#8a95a3"/></marker></defs>'
            + box(10, 10, 230, "PowerSchool SIS", "CC table (courses by student)", "#1f5fa8")
            + box(10, 92, 230, "Amplify mCLASS", "DIBELS Benchmark (BOY)", "#2E7D32")
            + box(10, 174, 230, "Amplify mCLASS", "DIBELS Progress Monitoring", "#2E7D32")
            + arrow(240, 43, 330, 118) + arrow(240, 125, 330, 125) + arrow(240, 207, 330, 132)
            + box(330, 92, 220, "Build script", "combines, applies the rules", "#B26A00")
            + arrow(550, 118, 640, 70) + arrow(550, 132, 640, 190)
            + box(640, 37, 250, "Student-by-window file", "who is tested, when", "#5E6674")
            + box(640, 157, 250, "Probe file", "every probe and score", "#5E6674")
            + '</svg>')


def build(f):
    status_rows = "".join(f"<tr><td>{pill(c, n)}</td><td>{d}</td></tr>" for c, n, d in [
        ("g", "Met target", "The window has closed and 95% or more of students were tested."),
        ("g", "On track", "The window is open and the tested % is at or above today's checkpoint."),
        ("a", "Behind", "Up to 15 points below today's checkpoint (15 is the default; the Behind points setting changes it)."),
        ("r", "Off track", "More than 15 points below today's checkpoint."),
        ("r", "Missed target", "The window has closed and fewer than 95% of students were tested."),
        ("n", "Not started", "The window has not opened yet, or no checkpoint has passed.")])
    measures = "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in [
        ("Letter Sounds (NWF-CLS)", "The student reads made-up words, which tests knowledge of letter sounds.", "Correct letter sounds in one minute", "K and 1"),
        ("Decoding (NWF-WRC)", "The same made-up words, scored by whole words read correctly.", "Whole words read correctly in one minute", "K and 1"),
        ("Reading Fluency (ORF)", "The student reads a short passage aloud.", "Words read correctly in one minute", "2 to 5"),
        ("Reading Accuracy (ORF-Accu)", "The same passage, scored for accuracy.", "Percent of words read correctly", "2 to 5"),
        ("Word Reading (WRF) and Phonemic Awareness (PSF)", "Real-word reading and sound segmenting. They appear in real exports for some grades.", "Items correct in one minute", "Not in this demo")])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>How This Dashboard Works (Demo)</title><style>{CSS}</style></head><body><div class="wrap" id="top">

<div class="hero"><span class="fake">DEMO: ALL DATA IS FAKE</span>
<h1>How this dashboard works</h1>
<p>A progress monitoring tracker: are students who need extra reading support being checked on schedule? Every student, teacher, score and date shown in this demo was made up.</p></div>
<nav class="toc"><a href="#quick">Quick guide</a><a href="#drill">Drill-down</a><a href="#controls">Controls</a><a href="#status">Statuses</a><a href="#tests">The assessments</a><a href="#real">Use it with real data</a><a href="#glossary">Glossary</a></nav>

<section id="quick"><h2>Quick guide <small>Everything you need in one minute</small></h2>
<ul>
<li><b>What it measures.</b> Whether students who scored <i>Well Below</i> or <i>Below</i> on the beginning-of-year DIBELS benchmark are being progress monitored on schedule.</li>
<li><b>Who is counted.</b> Students currently enrolled in grades K to 5 with one of those two levels, counted under their homeroom teacher.</li>
<li><b>What counts as tested.</b> At least 1 progress monitoring probe dated inside the window.</li>
<li><b>The goal.</b> 95% of students tested by the end of every window. Well Below students have 2-week windows and Below students have 4-week windows.</li>
<li><b>How to use it.</b> Pick a level and window, click a grade, then a teacher, then a student.</li></ul>
<div class="flow"><div class="step"><b>1. Grades</b>See which grades are on track.<em>Click a grade</em></div>
<div class="step"><b>2. Teachers</b>See each teacher's tested %.<em>Click a teacher</em></div>
<div class="step"><b>3. Students</b>See who still needs a probe.<em>Click a student</em></div>
<div class="step"><b>4. Student detail</b>See scores against the aimline.<em>Use Back to return</em></div></div>
<div class="grid"><div class="tile"><b>{f['tracked']}</b><span>fake students tracked</span></div><div class="tile"><b>{f['teachers']}</b><span>fake homeroom teachers</span></div>
<div class="tile"><b>{f['probe_rows']:,}</b><span>fake probe rows, {e(f['p_first'])} to {e(f['p_last'])}</span></div><div class="tile"><b>{e(f['data_as_of'])}</b><span>"data as of" (the demo's today is {e(f['as_of'])})</span></div></div>
</section>

<section id="drill"><h2>How the drill-down works <small>Four pages, one idea: start broad, click down to the student</small></h2>
<h3>1. Grades <a class="top" href="#top">back to top</a></h3>
<p>The first page compares grades. You see tiles for <b>Tested</b>, <b>Not tested</b>, <b>Last window</b> and the <b>Next checkpoint</b>, a row of checkpoint cards for the current window (each with its date and target), and a bar for each grade with its tested % and a status pill. Grades that are off track also get a badge.</p>
<div class="try"><b>Try it in this demo:</b> the current window is <b>{e(f['window'])}</b> ({e(f['start'])} to {e(f['end'])}). {f['tested_cur']} of {f['n_cur']} students ({f['pct']}%) have a probe in it so far. Click any grade bar.</div>
<h3>2. Teachers</h3>
<p>Clicking a grade opens the teachers in that grade, sorted from the lowest tested % to the highest. Each row shows tracked, tested and not tested counts, a bar, and a status pill.</p>
<div class="try"><b>Try it in this demo:</b> {f['n95']} of {f['nt']} teachers have reached 95%. The lowest is <b>{e(f['low_t'])}</b> at {f['low_pct']}% and the highest is {e(f['high_t'])} at {f['high_pct']}%. Click {e(f['low_t'])}.</div>
<h3>3. Students</h3>
<p>Clicking a teacher opens their students. A box lists students <b>not tested</b> in the window, so you know exactly who needs a probe. The list also shows each student's last probe date and aimline pill, and a search box finds a student by name.</p>
<div class="try"><b>Try it in this demo:</b> {e(f['miss_student'])} still needs a probe in {e(f['window'])}. Click the name.</div>
<h3>4. Student detail</h3>
<p>Clicking a student opens a one-page profile:</p>
<ul><li><b>Probe run chart.</b> One panel per measure: dots are scores, the dotted line is the aimline, and the green line is the goal.</li>
<li><b>Window history.</b> Every window with its dates, number of probes, a tested status and an aimline pill.</li>
<li><b>Probe history.</b> Every probe with its date, score, aimline value, how far above (+) or below (-) the aimline it was, the goal and a status.</li></ul>
<p>Use the <b>Back</b> button to return to the list.</p>
<div class="note">Behind the scenes, three click actions connect the pages: <i>grade to teachers</i>, <i>teacher to students</i> and <i>student to detail</i>. Each filters the next page to what you clicked. If a page looks empty, click an item on the page before it.</div></section>

<section id="controls"><h2>The controls <small>Two selectors and one setting</small></h2>
<table><tr><th>Control</th><th>What it does</th></tr>
<tr><td><b>Level</b></td><td>Well Below (2-week windows) or Below (4-week windows). The two groups have different calendars.</td></tr>
<tr><td><b>Window</b></td><td>"Current" shows today's window. Pick 1 to 8 to look back at a closed window, or ahead at one that has not opened.</td></tr>
<tr><td><b>Behind points</b></td><td>How many points under the checkpoint still counts as "Behind" instead of "Off track". Default 15.</td></tr></table>
<p>Closed windows are judged against the final 95% target, not a checkpoint. Windows that have not opened show "Not started".</p></section>

<section id="status"><h2>Statuses and colors <small>The same colors are used on every page</small></h2>
<table><tr><th style="width:150px">Status</th><th>Meaning</th></tr>{status_rows}</table>
<h3>Checkpoints</h3>
<p>Each window has checkpoints along the way, for example 40%, 70%, 90% and 95% of students tested by set dates. Today's checkpoint is the one most recently passed. A grade or teacher is compared with that number, not with the final 95%, until the window closes.</p>
<div class="note warn">The checkpoint percentages in this demo are placeholders. A real school would set its own.</div>
<h3>The aimline pills</h3>
<p>{pill('r', 'Below')} the latest probe was under the aimline. {pill('g', 'At or Above')} it was on or over the line. {pill('n', 'No probe')} nothing was tested in that window. {pill('n', 'Not available')} the platform gave no aimline for that probe.</p></section>

<section id="tests"><h2>About the assessments <small>What each score and level means</small></h2>
<h3>Benchmark: the beginning-of-year level (DIBELS 8, BOY)</h3>
<p>Every student takes the benchmark at the start of the year. The result is a composite level: <b>Well Below</b>, <b>Below</b>, <b>At</b> or <b>Above</b> benchmark. Only Well Below and Below students are expected to be progress monitored, so only they appear on this dashboard. The level stays the same all year, even if the student later improves.</p>
<div class="note">The levels come from the benchmark cut scores that Amplify publishes for each grade and time of year. This dashboard never recalculates them: it reads the level straight from the benchmark export.</div>
<h3>Progress monitoring: short checks between benchmarks</h3>
<p>A probe is a one-minute check. Teachers give probes more often to students who need more support. Which measures a student takes depends on the grade, as below.</p>
<table><tr><th>Measure</th><th>What the student does</th><th>Score</th><th>Grades (demo)</th></tr>{measures}</table>
<h3>Goal and aimline</h3>
<ul><li><b>Goal.</b> The score the student is working toward by the next benchmark.</li>
<li><b>Aimline.</b> A straight line from where the student started to the goal. It shows the score a student should have on any date to stay on pace.</li>
<li><b>Aimline status.</b> Each probe is compared with the aimline on its date: <i>Below</i> or <i>At or Above</i>. Some probes have no aimline yet, shown as "Not available".</li></ul>
<h3>Windows</h3>
<p>The school year is cut into windows. In this demo, Well Below students are expected to be probed in every 2-week window and Below students in every 4-week window. These lengths follow Amplify's progress monitoring fidelity guidance. A student is <b>tested</b> in a window with at least 1 probe in it.</p>
<div class="note warn"><b>Data lag.</b> Probes show up after the app syncs, which can take a few days. The "Data as of" date at the top of the dashboard says how current the numbers are.</div></section>

<section id="real"><h2>Using this with real data <small>Three downloads feed everything</small></h2>
{diagram()}
<table><tr><th>Source</th><th>What to download</th><th>Used for</th></tr>
<tr><td><b>PowerSchool SIS</b></td><td>The <b>CC table</b> (current course enrollments). Use Direct Database Export of the CC table, matched to your currently enrolled K-5 students, as a tab-delimited file with column titles. Fields: <code>[01]Student_Number</code>, <code>[01]Last_Name</code>, <code>[01]First_Name</code>, <code>[01]Grade_Level</code>, <code>Course_Number</code>, <code>[02]Course_Name</code>, <code>Section_Number</code>, <code>SectionID</code>, <code>Expression</code>, <code>[05]LastFirst</code>, <code>DateEnrolled</code>, <code>DateLeft</code>.</td><td>Who counts (currently enrolled), grade, homeroom and homeroom teacher.</td></tr>
<tr><td><b>Amplify mCLASS (DIBELS 8)</b></td><td>The <b>Benchmark</b> export for the <b>beginning of the year</b>: Download Your Data, then Benchmark, current school year, BOY, "Show students enrolled now", your school, Download CSV.</td><td>Each student's level (Well Below, Below, At, Above) and demographics.</td></tr>
<tr><td><b>Amplify mCLASS (DIBELS 8)</b></td><td>The <b>Progress Monitoring</b> export: Download Your Data, then Progress Monitoring, same filters, Download CSV. Pull again whenever you want fresh numbers and keep the older files.</td><td>Every probe: date, measure, score, aimline and goal.</td></tr></table>
<h3>From downloads to dashboard</h3>
<ol><li>Save each export in its own folder. Name files like <code>source_schoolyear_window_pulldate</code> (for example <code>dibels_pm_2026-27_boy-moy_2026-10-26_1338.csv</code>).</li>
<li>Add a small testing calendar (windows and checkpoint targets) in Excel.</li>
<li>Run the build script. It combines every progress monitoring export (a repeated probe is kept once, from the newest file), joins the three sources by student number, and writes the two files the dashboard reads.</li>
<li>Check the output against the raw exports, refresh the Tableau data sources, and republish.</li></ol>
<div class="note"><b>Privacy.</b> Real student data should stay inside your school's systems. This public demo uses fake records only, in exactly the same format as the real files.</div></section>

<section id="glossary"><h2>Glossary</h2>
<table><tr><td><b>Probe</b></td><td>One short progress monitoring check, usually one minute per measure.</td></tr>
<tr><td><b>Window</b></td><td>A 2-week or 4-week stretch in which every tracked student should have a probe.</td></tr>
<tr><td><b>Tested</b></td><td>At least 1 probe dated inside the window.</td></tr>
<tr><td><b>Tracked</b></td><td>Enrolled in K-5 and Well Below or Below on the beginning-of-year benchmark.</td></tr>
<tr><td><b>Checkpoint</b></td><td>A dated target for the tested % partway through a window.</td></tr>
<tr><td><b>Aimline</b></td><td>The expected score path from the starting score to the goal.</td></tr>
<tr><td><b>Data as of</b></td><td>The date of the newest probe in the data.</td></tr></table>
<p class="foot">All names, ids, scores and dates in this demo are fake. This guide is independent and is not affiliated with or endorsed by Amplify or PowerSchool. DIBELS, mCLASS and PowerSchool are trademarks of their owners.</p></section>
</div></body></html>"""


def main():
    html = build(facts())
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT} ({len(html):,} characters)")
    # A copy for GitHub Pages: Settings > Pages > branch main, folder /docs serves docs/index.html as a small web page.
    site = settings.ROOT / "docs"
    (site / "index.html").write_text(html, encoding="utf-8")
    (site / ".nojekyll").write_text("", encoding="utf-8")        # serve the files as they are, without GitHub's Jekyll processing
    print(f"Wrote {site / 'index.html'} for GitHub Pages")


if __name__ == "__main__":
    main()
