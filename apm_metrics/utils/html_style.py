"""Shared look for the generated HTML pages (data dictionary, dashboard guide). Self-contained: no external files."""

STYLE = """
:root{--bg:#faf9f6;--card:#ffffff;--ink:#1f2328;--muted:#5e6674;--line:#e6e3dc;--amber:#B26A00;--amber-soft:#fbf1e1;
--green:#2E7D32;--red:#C62828;--gray:#5E6674;--green-soft:#e8f3e9;--red-soft:#fbeaea;--gray-soft:#eef0f3}
@media(prefers-color-scheme:dark){:root{--bg:#16181c;--card:#1f2227;--ink:#eceae4;--muted:#a3aab5;--line:#33373e;--amber:#e09a2f;
--amber-soft:#3a2d14;--green:#6cc070;--red:#ef7b7b;--gray:#a3aab5;--green-soft:#1c3320;--red-soft:#3d1d1d;--gray-soft:#2a2e35}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header.hero{background:linear-gradient(135deg,#B26A00 0%,#8f5400 100%);color:#fff;padding:44px 20px 38px}
header.hero .in{max-width:980px;margin:0 auto}
header.hero h1{margin:0 0 6px;font-size:clamp(26px,4.5vw,38px);line-height:1.2;font-weight:700;letter-spacing:-.01em}
header.hero p{margin:0;opacity:.92;font-size:17px;max-width:680px}
header.hero .meta{margin-top:16px;font-size:13px;opacity:.85}
nav.top{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line)}
nav.top .in{max-width:980px;margin:0 auto;display:flex;gap:2px;overflow-x:auto;padding:0 12px}
nav.top a{color:var(--muted);text-decoration:none;font-size:14px;font-weight:600;padding:13px 12px;white-space:nowrap;border-bottom:3px solid transparent}
nav.top a:hover{color:var(--amber);border-bottom-color:var(--amber)}
main{max-width:980px;margin:0 auto;padding:10px 20px 70px}
section{padding-top:34px;scroll-margin-top:52px}
h2{font-size:26px;line-height:1.25;margin:0 0 6px;letter-spacing:-.01em}
h2 .n{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:50%;background:var(--amber);color:#fff;font-size:15px;margin-right:10px;vertical-align:3px}
h3{font-size:18px;margin:22px 0 6px}
p.lead{color:var(--muted);margin:0 0 16px;font-size:17px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:14px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px}
.grid .card{margin:0}
.step{display:flex;gap:14px;align-items:flex-start;margin:12px 0}
.step .b{flex:none;width:34px;height:34px;border-radius:50%;background:var(--amber-soft);color:var(--amber);font-weight:700;display:flex;align-items:center;justify-content:center}
.step p{margin:0}
.chip{display:inline-block;font-size:12.5px;font-weight:700;color:#fff;padding:3px 11px;border-radius:999px;white-space:nowrap}
.g{background:var(--green)}.a{background:var(--amber)}.r{background:var(--red)}.n{background:var(--gray)}
.cp{border:1px solid var(--line);border-radius:10px;padding:8px 10px;text-align:center;font-size:13px;background:var(--card)}
.cp b{display:block;font-size:15px}.cp.cur{border:2px solid var(--amber)}.cp.done{background:var(--gray-soft)}
table{width:100%;border-collapse:collapse;font-size:14.5px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);background:var(--bg);position:sticky;top:0}
td code,p code,li code{background:var(--gray-soft);padding:1px 6px;border-radius:5px;font-size:13px}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--card)}
.tw table{min-width:640px}
.bars .row{display:grid;grid-template-columns:96px 1fr 44px 92px;gap:10px;align-items:center;font-size:14px;margin:8px 0}
.bars .bar{height:16px;background:var(--gray-soft);border-radius:4px;position:relative}
.bars .bar i{display:block;height:100%;border-radius:4px}
.bars .bar s{position:absolute;top:-3px;bottom:-3px;border-left:2px dashed var(--amber)}
.bars .bar u{position:absolute;top:-3px;bottom:-3px;left:95%;width:2px;background:var(--ink)}
.note{background:var(--amber-soft);border-left:4px solid var(--amber);border-radius:0 10px 10px 0;padding:12px 16px;margin:14px 0;font-size:15px}
.cap{font-size:13px;color:var(--muted);margin-top:6px}
ul.tight{margin:6px 0 6px 20px;padding:0}ul.tight li{margin:4px 0}
details{border:1px solid var(--line);border-radius:12px;background:var(--card);padding:2px 16px;margin:10px 0}
summary{cursor:pointer;font-weight:600;padding:12px 0}details p{margin:0 0 14px;color:var(--ink)}
input.search{width:100%;padding:11px 14px;font-size:16px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);margin:6px 0 14px}
footer{max-width:980px;margin:0 auto;padding:0 20px 40px;color:var(--muted);font-size:13px}
@media print{nav.top{display:none}header.hero{background:#B26A00}}
"""
