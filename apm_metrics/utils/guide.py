"""Builds dashboard_guide.html: a plain-language page for leaders and teachers explaining how to use the
dashboard, how the numbers are worked out, and how teachers are monitored. Dates and targets come straight
from testing_calendar.xlsx, so the page is always current. Self-contained: link to it from Tableau."""

import html

import pandas as pd

from apm_metrics.utils.html_style import STYLE

e = html.escape


def _d(ts) -> str:
    ts = pd.Timestamp(ts)
    return f"{ts.strftime('%b')} {ts.day}"


def _bars() -> str:
    rows = [("Kindergarten", 12, "r", "Off track"), ("Grade 1", 38, "a", "Behind"), ("Grade 2", 71, "g", "On track")]
    out = ""
    for name, v, c, tag in rows:
        out += (f'<div class="row"><span>{name}</span><div class="bar"><i class="{c}" style="width:{v}%"></i>'
                f'<s style="left:70%"></s><u></u></div><b>{v}%</b><span><span class="chip {c}">{tag}</span></span></div>')
    return f'<div class="bars card">{out}<p class="cap">Example only. Dashed amber line = where a grade should be today (the current checkpoint). Black line = 95% goal.</p></div>'


def _windows_table(windows: pd.DataFrame) -> str:
    out = ""
    for level, cadence in (("Well Below", "every 2 weeks"), ("Below", "every 4 weeks")):
        w = windows[windows.level == level].sort_values("window_id")
        rows = "".join(f"<tr><td>{r.window_id}</td><td>{_d(r.start_date)} to {_d(r.end_date)}</td></tr>" for r in w.itertuples())
        out += (f'<div class="card"><h3 style="margin-top:0">{level} students: {cadence}</h3><div class="tw"><table>'
                f'<thead><tr><th>Window</th><th>Dates</th></tr></thead><tbody>{rows}</tbody></table></div></div>')
    return f'<div class="grid">{out}</div>'


def _checkpoints(windows, checkpoints, as_of) -> str:
    out = ""
    for level in ("Well Below", "Below"):
        w = windows[windows.level == level].sort_values("window_id")
        cur = w[(w.start_date <= as_of) & (w.end_date >= as_of)]
        pick = cur.iloc[0] if len(cur) else w.iloc[0]
        cps = checkpoints[(checkpoints.level == level) & (checkpoints.window_id == pick.window_id)].sort_values("checkpoint_date")
        cards = f'<div class="cp {"done" if pick.start_date <= as_of else ""}"><b>{_d(pick.start_date)}</b>Window opens</div>'
        current = cps[cps.checkpoint_date <= as_of].tail(1)["checkpoint_date"]
        for c in cps.itertuples():
            cls = "cur" if len(current) and c.checkpoint_date == current.iloc[0] and pick.end_date >= as_of else ("done" if c.checkpoint_date <= as_of else "")
            cards += f'<div class="cp {cls}"><b>{_d(c.checkpoint_date)}</b>{c.target_pct_tested}% tested<br><span class="cap">{e(str(c.label))}</span></div>'
        out += (f'<h3>{level}, {e(pick.window_label)} ({_d(pick.start_date)} to {_d(pick.end_date)})</h3>'
                f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px">{cards}</div>')
    return out


def write(out_dir, windows, checkpoints, settings, as_of, last_probe, school_name="Your School") -> None:
    behind = int(settings.get("behind_points", 15)); final = int(settings.get("final_target_pct", 95))
    minp = int(settings.get("tested_rule_min_probes", 1))
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DIBELS progress monitoring dashboard: how it works</title><style>{STYLE}</style></head><body>
<header class="hero"><div class="in"><h1>DIBELS progress monitoring dashboard</h1>
<p>How to use it, how the numbers work, and how we check that students who need extra support are being monitored on schedule.</p>
<div class="meta">{e(school_name)} | Grades K-5 | Calendar as of {e(as_of.strftime('%B %d, %Y'))} | Data through {e(pd.Timestamp(last_probe).strftime('%B %d, %Y'))}</div></div></header>
<nav class="top"><div class="in"><a href="#why">Why</a><a href="#use">Using it</a><a href="#who">Who's counted</a><a href="#tested">Tested</a>
<a href="#schedule">Schedule</a><a href="#status">Status</a><a href="#teachers">Teachers</a><a href="#faq">FAQ</a></div></nav><main>

<section id="why"><h2><span class="n">1</span>What this dashboard is for</h2>
<p class="lead">Students who are Below or Well Below benchmark in reading need frequent progress monitoring so we can see whether
instruction is working. This dashboard shows, window by window, how many of those students have been monitored, so we can
catch gaps while there is still time to close them.</p>
<div class="grid"><div class="card"><b>It measures</b><p>Whether a progress monitoring probe was given on schedule.</p></div>
<div class="card"><b>It does not measure</b><p>How well a student scored, or the quality of instruction.</p></div>
<div class="card"><b>The goal</b><p>{final}% of tracked students monitored by the end of every window.</p></div></div></section>

<section id="use"><h2><span class="n">2</span>Using the dashboard</h2>
<p class="lead">Four pages. Each opens on the current window.</p>
<div class="step"><div class="b">1</div><p><b>Pick a level at the top.</b> Choose <b>Well Below</b> or <b>Below</b>. They follow different schedules, so they are shown separately.</p></div>
<div class="step"><div class="b">2</div><p><b>Read the grade page.</b> Each bar is the share of students tested in this window. The colour tells you if the grade is on pace.</p></div>
{_bars()}
<div class="step"><div class="b">3</div><p><b>Click a grade</b> to see its teachers, worst first. Each row shows how many students are tracked, tested and not yet tested.</p></div>
<div class="step"><div class="b">4</div><p><b>Click a teacher</b> to open the list of students who have not been tested yet: name, ID, level and the date of their last probe.</p></div>
<div class="step"><div class="b">5</div><p><b>Heat grid.</b> Shows every teacher across every window, so you can see who is consistently on pace and who falls behind.</p></div>
<div class="note">Use the <b>Window</b> menu to look back at earlier windows. Past windows are recalculated from the latest data, so they can shift slightly if students enroll or leave.</div></section>

<section id="who"><h2><span class="n">3</span>Who is counted</h2>
<p class="lead">A student counts when all of these are true.</p>
<ul class="tight"><li>They are <b>currently enrolled</b> in grades K-5 (from PowerSchool).</li>
<li>Their fall (BOY) benchmark level is <b>Well Below</b> or <b>Below</b>. Students At or Above benchmark are not expected to be monitored.</li>
<li>They are counted under their <b>current homeroom teacher</b>.</li></ul>
<p>Students who transferred out are not counted against any teacher. Students who have no benchmark yet, or an unfinished one, are not counted until they have a level. Pre-K has no progress monitoring.</p></section>

<section id="tested"><h2><span class="n">4</span>What counts as tested</h2>
<p class="lead">A student is <b>tested</b> in a window when they have at least <b>{minp} progress monitoring probe</b> dated inside that window.</p>
<div class="card"><p>A <b>probe</b> is one scored progress monitoring check. Several scores from the same sitting (for example Decoding and Letter Sounds) count as one probe. Percent tested = students tested / students tracked.</p></div></section>

<section id="schedule"><h2><span class="n">5</span>Windows and checkpoints</h2>
<p class="lead">Time is split into <b>windows</b>. Each window has a deadline and a few <b>checkpoints</b> along the way.</p>
{_windows_table(windows)}
<h3>Checkpoints in the current window</h3>
<p>A checkpoint is the share of students that should be tested <i>by that date</i>. It rises through the window and ends at {final}%.</p>
{_checkpoints(windows, checkpoints, as_of)}
<p class="cap">The card with the amber outline is the current checkpoint: the target the dashboard compares everyone to today.</p></section>

<section id="status"><h2><span class="n">6</span>Status colours</h2>
<p class="lead">Status compares the percent tested to the current checkpoint.</p>
<div class="tw"><table><thead><tr><th>Status</th><th>Meaning</th></tr></thead><tbody>
<tr><td><span class="chip g">On track</span></td><td>At or above the current checkpoint.</td></tr>
<tr><td><span class="chip a">Behind</span></td><td>Below the checkpoint by up to {behind} points.</td></tr>
<tr><td><span class="chip r">Off track</span></td><td>Below the checkpoint by more than {behind} points.</td></tr>
<tr><td><span class="chip n">Not started</span></td><td>The window just opened and no checkpoint has passed.</td></tr>
<tr><td><span class="chip g">Met target</span> / <span class="chip r">Missed target</span></td><td>After a window closes: {final}% or more, or less than {final}%.</td></tr></tbody></table></div></section>

<section id="teachers"><h2><span class="n">7</span>How teachers are monitored</h2>
<p class="lead">The dashboard gives every teacher a clear, fair picture of where their students stand.</p>
<ul class="tight"><li>Each teacher's percent is the share of <i>their own</i> tracked students who have been tested in the window.</li>
<li>Every teacher is compared to the <b>same checkpoint</b> on the same date, so no one is judged before the window has had time to run.</li>
<li>The student list shows exactly who still needs a probe, so the fix is specific.</li>
<li>Results are kept for each window, so leaders can see a pattern over the year, not only one bad week.</li></ul>
<div class="note">The dashboard shows what has happened. What leaders do with it (coaching, reminders, support) is decided by leadership.</div></section>

<section id="faq"><h2><span class="n">8</span>Questions</h2>
<details><summary>A student I expected to see isn't on my list.</summary><p>Common reasons: the student transferred out, is At or Above benchmark, has no benchmark result yet, has a benchmark that isn't finished, or is in a different homeroom now. Ask the data team to check.</p></details>
<details><summary>I tested a student but they show as not tested.</summary><p>The dashboard only knows about probes in the latest DIBELS export. Check the "Data through" date at the top of the page; probes after that date appear after the next update.</p></details>
<details><summary>Why does a window start at 0%?</summary><p>At the start nothing has been tested yet. No target applies until the first checkpoint, so the status shows "Not started".</p></details>
<details><summary>Why do Below students have fewer windows?</summary><p>Well Below students are monitored every 2 weeks and Below students every 4 weeks, so a Below window is twice as long.</p></details>
<details><summary>Is a student counted if they were tested more than once?</summary><p>Yes, and they only count once. At least {minp} probe in the window is enough for "tested".</p></details>
<details><summary>Who do I ask about the numbers?</summary><p>The data team.</p></details></section>
</main><footer>This page is rebuilt automatically with each data update, so the dates and targets above are always current.</footer></body></html>"""
    (out_dir / "dashboard_guide.html").write_text(page, encoding="utf-8")
