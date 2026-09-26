"""The explorer page: one self-contained HTML file.

Open ``results/explorer.html`` straight from disk.  All data is embedded,
gzip-compressed and base64-encoded, and unpacked in the browser with
``DecompressionStream``; sorting, filtering, the roll-ups and each strategy's
profile are computed client-side.

Layout: a one-screen app.  The strategy table fills the window with a frozen
header and frozen ID / name columns, scrolls smoothly through every row
(virtualised, no pages), and a docked inspector on the right shows the
selected strategy.  Arrow keys move the selection; "/" focuses search.
"""
from __future__ import annotations

import base64
import gzip
import json
import math


def _clean(x):
    if isinstance(x, float):
        return None if (math.isnan(x) or math.isinf(x)) else x
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if hasattr(x, "item"):          # numpy scalar
        return _clean(x.item())
    return x


def render(payload: dict, *, standalone: bool = True) -> str:
    """HTML for the explorer.  ``standalone=False`` omits the document
    skeleton (doctype/html/head/body) for hosts that add their own."""
    raw = json.dumps(_clean(payload), separators=(",", ":"), allow_nan=False).encode()
    blob = base64.b64encode(gzip.compress(raw, 9)).decode()
    body = TEMPLATE.replace("__DATA__", blob)
    if not standalone:
        return body
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            "</head>\n<body>\n" + body + "\n</body>\n</html>\n")


TEMPLATE = r"""<title>Confluence Trade Explorer</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700&family=IBM+Plex+Mono:wght@500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
/* A single dark look, on purpose: it follows the navy terminal style the
   explorer was asked to match.  Every surface and ink is painted explicitly. */
:root{
  color-scheme:dark;
  --ground:#09131f; --panel:#0e1b2c; --panel-2:#0c1827; --raised:#132338; --hover:#17304f; --sel:#1b3b66;
  --line:#1b2e47; --line-2:#284567;
  --ink:#e6edf7; --ink-2:#a6b5ca; --ink-3:#7489a6;
  --accent:#3d8bfd; --accent-ink:#ffffff; --accent-wash:rgba(61,139,253,.16);
  --gain:#35c97c; --loss:#f3606f; --warn:#e8b34d;
  --band-3y:rgba(61,139,253,.07); --band-6m:rgba(61,139,253,.16);
  --f-ui:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
  --f-display:"Archivo","IBM Plex Sans",system-ui,"Segoe UI",sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --insp-w:clamp(400px,28vw,500px);
}
*{box-sizing:border-box}
[hidden]{display:none!important}
html,body{height:100%;margin:0;background:var(--ground);color:var(--ink)}
body{font:13px/1.45 var(--f-ui);overflow:hidden}
button,input,select{font:inherit;color:inherit}
:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
.app{height:100%;display:flex;flex-direction:column;padding-inline:16px;padding-block:10px 12px;gap:10px;min-width:0}

/* ---------------------------------------------------------------- top bar */
.bar{display:flex;align-items:center;gap:10px 20px;flex-wrap:wrap}
.brand{font:700 19px/1 var(--f-display);letter-spacing:.2px;white-space:nowrap}
.tabs{display:flex;gap:6px;flex-wrap:wrap}
.tab{background:transparent;border:1px solid var(--line-2);border-radius:999px;padding:5px 14px;cursor:pointer;color:var(--ink-2);white-space:nowrap}
.tab:hover{color:var(--ink);border-color:var(--accent)}
.tab[aria-selected="true"]{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.meta{color:var(--ink-3);font-size:12px;flex:1 1 320px;text-align:right}

/* ---------------------------------------------------------------- toolbar */
.toolbar{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:flex-end}
.fld{display:flex;flex-direction:column;gap:3px;min-width:0}
.fld > span{font-size:10.5px;letter-spacing:.7px;text-transform:uppercase;color:var(--ink-3)}
.fld input,.fld select{height:30px;background:var(--panel);border:1px solid var(--line-2);border-radius:6px;padding:0 8px;min-width:0}
.fld input:hover,.fld select:hover{border-color:#34557d}
.fld.search input{width:210px}
.fld.num input{width:78px}
.fld select{max-width:220px}
.btn{height:30px;border-radius:6px;border:1px solid var(--line-2);background:var(--raised);color:var(--ink);padding:0 12px;cursor:pointer;white-space:nowrap}
.btn:hover{border-color:var(--accent)}
.seg{display:flex;border:1px solid var(--line-2);border-radius:6px;overflow:hidden;height:30px}
.seg button{background:var(--panel);border:0;border-right:1px solid var(--line-2);padding:0 10px;cursor:pointer;color:var(--ink-2)}
.seg button:last-child{border-right:0}
.seg button[aria-pressed="true"]{background:var(--accent-wash);color:var(--ink)}
.count{color:var(--ink-2);font-size:12px;padding-bottom:7px;white-space:nowrap}
.count b{color:var(--ink);font-weight:600}
.more-toggle{display:none}

/* ---------------------------------------------------------------- split view */
.split{flex:1;min-height:0;display:grid;grid-template-columns:minmax(0,1fr) var(--insp-w);gap:12px}
.pane{min-height:0;min-width:0;display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.gwrap{flex:1;min-height:0;overflow:auto;position:relative;overscroll-behavior:contain}
.gfoot{display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap;padding:6px 12px;border-top:1px solid var(--line);color:var(--ink-3);font-size:11.5px}
.keys kbd{font:500 10.5px/1 var(--f-mono);border:1px solid var(--line-2);border-bottom-width:2px;border-radius:4px;padding:2px 5px;color:var(--ink-2);background:var(--raised)}
.boot{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--ink-2);font-size:14px;padding:16px;text-align:center}

table.grid{table-layout:fixed;border-collapse:separate;border-spacing:0;width:max-content;min-width:100%}
.grid th,.grid td{padding:0 10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:right;font-variant-numeric:tabular-nums}
.grid th{position:sticky;top:0;z-index:3;height:36px;background:var(--raised);color:var(--ink-3);font-size:10.5px;letter-spacing:.6px;text-transform:uppercase;font-weight:600;border-bottom:1px solid var(--line-2);cursor:pointer;user-select:none}
.grid th:hover{color:var(--ink)}
.grid th[aria-sort]{color:var(--ink)}
.grid th .arr{color:var(--accent);margin-left:3px}
.grid td{height:32px;border-bottom:1px solid var(--line);background:var(--panel);color:var(--ink)}
.grid tr.alt td{background:var(--panel-2)}
.grid tbody tr:hover td{background:var(--hover)}
.grid tr.sel td{background:var(--sel)}
.grid tr.sel td.rk{box-shadow:inset 3px 0 0 var(--accent)}
.grid tr.ctrl td{color:var(--ink-2)}
.grid .l{text-align:left}
.grid .fz{position:sticky;z-index:2}
.grid th.fz{z-index:4}
.grid .fzl{box-shadow:1px 0 0 var(--line-2)}
.grid td.id{font:500 12px var(--f-mono);color:var(--ink-2)}
.grid td.rk{color:var(--ink-3)}
.grid tr.spacer td{height:auto;padding:0;border:0;background:transparent}
.grid tbody tr{cursor:pointer}
.tag{display:inline-block;font-size:10px;letter-spacing:.5px;padding:0 6px;border-radius:999px;border:1px solid var(--warn);color:var(--warn);margin-right:6px}
.pos{color:var(--gain)} .neg{color:var(--loss)} .mut{color:var(--ink-3)}
.p-hi{color:var(--gain);font-weight:600} .p-mid{color:#9fe2bd}

/* phone list */
.cards{display:none}
.card{position:absolute;left:0;right:0;padding:10px 12px;border-bottom:1px solid var(--line);cursor:pointer}
.card:hover{background:var(--hover)}
.card.sel{background:var(--sel)}
.card .t1{display:flex;justify-content:space-between;gap:8px;color:var(--ink-3);font-size:11.5px}
.card .t1 .id{font:500 11.5px var(--f-mono);color:var(--ink-2)}
.card .t2{font-weight:600;margin:2px 0 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.card .t3{display:flex;gap:12px;font-size:12px;font-variant-numeric:tabular-nums;color:var(--ink-2);flex-wrap:wrap}
.card .t3 b{font-weight:600}

/* ---------------------------------------------------------------- inspector */
.insp{overflow:auto;overscroll-behavior:contain;flex:1;min-height:0}
.ihead{position:sticky;top:0;z-index:2;background:var(--panel);padding:12px 16px 10px;border-bottom:1px solid var(--line)}
.ihead .row1{display:flex;align-items:center;gap:8px}
.ihead .sid{font:500 13px var(--f-mono);color:var(--ink-2)}
.ihead .nav{margin-left:auto;display:flex;gap:6px}
.ihead .nav button{min-width:30px;height:28px;padding:0 8px;border-radius:6px;border:1px solid var(--line-2);background:var(--raised);color:var(--ink);cursor:pointer}
.ihead .nav button:hover{border-color:var(--accent)}
.ihead .nav .close{display:none}
.ihead h2{font:700 17px/1.25 var(--f-display);margin:6px 0 2px;text-wrap:balance}
.ihead .sub{color:var(--ink-2);font-size:12.5px}
.pills{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.pill{font-size:11.5px;padding:2px 9px;border-radius:999px;border:1px solid var(--line-2);color:var(--ink-2);display:inline-flex;align-items:center;gap:6px}
.pill i{width:7px;height:7px;border-radius:50%;display:inline-block}
.pill.good{border-color:rgba(53,201,124,.55);color:#c3f0d8} .pill.good i{background:var(--gain)}
.pill.bad{border-color:rgba(243,96,111,.55);color:#fbd0d5} .pill.bad i{background:var(--loss)}
.pill.warn{border-color:rgba(232,179,77,.6);color:#f5e0b3} .pill.warn i{background:var(--warn)}
.ibody{padding:14px 16px 20px;display:flex;flex-direction:column;gap:18px}
.thesis{color:var(--ink-2);margin:0}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:8px;overflow:hidden}
.tile{background:var(--panel-2);padding:9px 11px;min-width:0}
.tile .k{font-size:11px;color:var(--ink-3)}
.tile .v{font-size:18px;font-weight:600;margin-top:1px}
.tile .d{font-size:11px;color:var(--ink-3);font-variant-numeric:tabular-nums}
.sec h3{font:600 11px/1.2 var(--f-ui);letter-spacing:.8px;text-transform:uppercase;color:var(--ink-3);margin:0 0 8px;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
.sec h3 em{font-style:normal;text-transform:none;letter-spacing:0;font-weight:400}
.chart{position:relative}
.chart svg{display:block;width:100%;height:auto;overflow:visible}
.chart text{fill:var(--ink-3);font:10.5px var(--f-ui);font-variant-numeric:tabular-nums}
.chart text.lab{fill:var(--ink-2)}
.tip{position:absolute;pointer-events:none;background:var(--raised);border:1px solid var(--line-2);border-radius:6px;padding:5px 8px;font-size:12px;white-space:nowrap;box-shadow:0 6px 18px rgba(0,0,0,.35);transform:translate(-50%,-120%);display:none}
.tip b{font-weight:600}
.tip span{color:var(--ink-3);margin-left:6px}
table.mini{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
.mini th,.mini td{padding:5px 6px;text-align:right;border-bottom:1px solid var(--line)}
.mini th{color:var(--ink-3);font-weight:500;font-size:11px;white-space:nowrap}
.mini .l{text-align:left}
.kv{display:grid;grid-template-columns:1fr auto;gap:5px 16px;margin:0;font-variant-numeric:tabular-nums}
.kv dt{color:var(--ink-3)} .kv dd{margin:0;text-align:right}
.rules{margin:0;padding-left:18px;color:var(--ink-2)}
.rules li{margin:3px 0}
.rules b{color:var(--ink);font-weight:600}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}

/* ---------------------------------------------------------------- other views */
.view{flex:1;min-height:0;display:flex;flex-direction:column}
.scroll{overflow:auto}
.famwrap{flex:1;min-height:0;overflow:auto;background:var(--panel);border:1px solid var(--line);border-radius:10px}
table.fam{border-collapse:separate;border-spacing:0;width:100%;min-width:1040px;font-variant-numeric:tabular-nums}
.fam th,.fam td{padding:8px 12px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
.fam th{position:sticky;top:0;background:var(--raised);color:var(--ink-3);font-size:10.5px;letter-spacing:.6px;text-transform:uppercase;font-weight:600;cursor:pointer;z-index:1}
.fam th[aria-sort]{color:var(--ink)}
.fam .l{text-align:left}
.fam tbody tr{cursor:pointer}
.fam tbody tr:hover td{background:var(--hover)}
.fam .fname{font-weight:600}
.fam .flegs{color:var(--ink-3);font-size:12px}
.dimgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,540px),1fr));gap:12px;padding-bottom:8px}
.dcard{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;overflow-x:auto}
.dcard h3{margin:0 0 6px;font:700 14px var(--f-display)}
.dnote{color:var(--ink-2);margin:0 0 10px;max-width:90ch}
.div-track{position:relative;height:10px;width:130px;display:inline-block;vertical-align:middle}
.div-track::before{content:"";position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;background:var(--line-2)}
.div-bar{position:absolute;top:1px;height:8px;border-radius:2px}
.lessons{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,440px),1fr));gap:12px;padding-bottom:8px}
.lcard{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:6px}
.lcard .kind{font-size:10.5px;letter-spacing:.7px;text-transform:uppercase;display:flex;align-items:center;gap:6px}
.lcard .kind i{width:8px;height:8px;border-radius:50%}
.lcard h3{margin:0;font:700 15px/1.3 var(--f-display);text-wrap:balance}
.lcard p{margin:0;color:var(--ink-2);max-width:75ch}
.doc{max-width:980px;padding-bottom:24px}
.doc h2{font:700 16px var(--f-display);margin:22px 0 8px}
.doc p,.doc li{color:var(--ink-2);max-width:80ch}
.doc .tw{overflow-x:auto}
.doc table{border-collapse:collapse;margin:6px 0 12px;width:100%}
.doc td,.doc th{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.doc th{color:var(--ink-3);font-weight:500;font-size:12px}
.doc td:first-child{white-space:nowrap;color:var(--ink);font-weight:600}
.doc code{font:12px var(--f-mono);background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:1px 5px}

/* ---------------------------------------------------------------- responsive */
@media (max-width:1280px){ .fld.search input{width:170px} }
@media (max-width:1060px){
  .split{grid-template-columns:minmax(0,1fr)}
  .insp-pane{position:fixed;top:0;right:0;bottom:0;width:min(520px,100%);z-index:20;border-radius:0;border-width:0 0 0 1px;box-shadow:-20px 0 50px rgba(0,0,0,.5);padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
  .insp-pane[data-open="false"]{display:none}
  .ihead .nav .close{display:inline-block}
  .meta{text-align:left}
}
@media (max-width:760px){
  .app{padding-block:8px}
  .brand{font-size:17px}
  .meta{display:none}
  .tab{padding:4px 10px;font-size:12px}
  .more-toggle{display:inline-block}
  .toolbar .opt{display:none}
  .toolbar.open .opt{display:flex}
  .fld.search{flex:1 1 160px} .fld.search input{width:100%}
  .grid{display:none}
  .cards{display:block;position:relative}
  .gfoot .keys{display:none}
  .two{grid-template-columns:1fr}
  .insp-pane{width:100%;border-left:0}
  .tiles{grid-template-columns:repeat(2,1fr)}
}
</style>

<div class="app">
  <header class="bar">
    <div class="brand">Confluence Trade Explorer</div>
    <nav class="tabs" role="tablist" aria-label="Views">
      <button class="tab" role="tab" data-view="strategies" aria-selected="true" id="t-strategies">All strategies</button>
      <button class="tab" role="tab" data-view="families" aria-selected="false" id="t-families">Families</button>
      <button class="tab" role="tab" data-view="dimensions" aria-selected="false" id="t-dimensions">Groups &amp; dimensions</button>
      <button class="tab" role="tab" data-view="lessons" aria-selected="false" id="t-lessons">Lessons</button>
      <button class="tab" role="tab" data-view="guide" aria-selected="false" id="t-guide">How to read</button>
    </nav>
    <div class="meta" id="meta"></div>
  </header>

  <main class="view" id="v-strategies">
    <div class="toolbar" id="toolbar">
      <label class="fld search"><span>Search</span><input id="q" type="search" placeholder="ID, name, family…" autocomplete="off"></label>
      <button class="btn more-toggle" id="moreBtn" type="button" aria-expanded="false">Filters</button>
      <label class="fld opt"><span>Market</span><select id="fMkt"></select></label>
      <label class="fld opt"><span>Timeframe</span><select id="fTf"></select></label>
      <label class="fld opt"><span>Group</span><select id="fGrp"></select></label>
      <label class="fld opt"><span>Family</span><select id="fFam"></select></label>
      <label class="fld opt"><span>Session</span><select id="fSes"></select></label>
      <label class="fld opt"><span>Entry</span><select id="fEnt"></select></label>
      <label class="fld opt"><span>Stop</span><select id="fStp"></select></label>
      <label class="fld opt"><span>Target</span><select id="fTgt"></select></label>
      <label class="fld num opt"><span>Min trades</span><input id="fMin" type="number" min="0" step="10" value="30"></label>
      <label class="fld num opt"><span>Max / week</span><input id="fMaxW" type="number" min="0" step="0.5" placeholder="any"></label>
      <label class="fld opt"><span>Show</span><select id="fOnly">
        <option value="all">everything</option>
        <option value="noctrl">hide random controls</option>
        <option value="ctrl">random controls only</option>
        <option value="net">net-profitable over 8 years</option>
        <option value="allwin">profitable 8y, 3y and 6m</option>
        <option value="beat">edge clears the luck bar</option>
        <option value="prop">P(pass eval) at least 50%</option>
        <option value="active">at least 1 trade a week</option>
      </select></label>
      <label class="fld opt"><span>Sort by</span><select id="fSort"></select></label>
      <div class="fld opt"><span>Columns</span><div class="seg" id="preset" role="group" aria-label="Column set"></div></div>
      <button class="btn opt" id="reset" type="button">Reset</button>
      <div class="count" id="count"></div>
    </div>
    <div class="split" id="split">
      <section class="pane" aria-label="Strategies">
        <div class="gwrap" id="gwrap" tabindex="0" aria-label="Strategy table; arrow keys move the selection">
          <div class="boot" id="boot">Unpacking strategies…</div>
          <table class="grid" id="grid"><colgroup id="gcols"></colgroup><thead id="ghead"></thead><tbody id="gbody"></tbody></table>
          <div class="cards" id="cards"></div>
        </div>
        <div class="gfoot"><span id="foot"></span><span class="keys"><kbd>↑</kbd> <kbd>↓</kbd> move · <kbd>PgUp</kbd> <kbd>PgDn</kbd> jump · <kbd>/</kbd> search · click a header to sort</span></div>
      </section>
      <aside class="pane insp-pane" id="inspPane" data-open="false" aria-label="Strategy detail">
        <div class="insp" id="insp"></div>
      </aside>
    </div>
  </main>

  <main class="view" id="v-families" hidden><div class="famwrap"><table class="fam" id="famTbl"><thead></thead><tbody></tbody></table></div></main>
  <main class="view scroll" id="v-dimensions" hidden><p class="dnote" id="dimNote"></p><div class="dimgrid" id="dims"></div></main>
  <main class="view scroll" id="v-lessons" hidden><div class="lessons" id="lessons"></div></main>
  <main class="view scroll" id="v-guide" hidden><div class="doc" id="guide"></div></main>
</div>

<script id="data" type="text/plain">__DATA__</script>
<script>
(function(){
"use strict";
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const MINUS = "−";
const num = (v, d = 2) => v == null ? "–" : (v < 0 ? MINUS : "") + Math.abs(v).toLocaleString("en-US", {minimumFractionDigits: d, maximumFractionDigits: d});
const sgn = (v, d = 3, suf = "") => v == null ? "–" : (v > 0 ? "+" : v < 0 ? MINUS : "") + Math.abs(v).toFixed(d) + suf;
const usd = v => v == null ? "–" : (v < 0 ? MINUS + "$" : "$") + Math.abs(Math.round(v)).toLocaleString("en-US");
const usdS = v => v == null ? "–" : (v > 0 ? "+$" : v < 0 ? MINUS + "$" : "$") + Math.abs(Math.round(v)).toLocaleString("en-US");
const pc = (v, d = 0) => v == null ? "–" : (100 * v).toFixed(d) + "%";
const tone = v => v == null ? "mut" : v > 0 ? "pos" : v < 0 ? "neg" : "mut";
const store = {get(k){try{return localStorage.getItem(k)}catch(e){return null}}, set(k,v){try{localStorage.setItem(k,v)}catch(e){}}};

async function unpack(){
  const bin = atob($("data").textContent.trim()), bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
  return JSON.parse(await new Response(stream).text());
}
unpack().then(start).catch(err => {
  $("boot").textContent = "This browser could not unpack the data. Open the file in a current Chrome, Edge, Safari or Firefox.";
  console.error(err);
});

function start(D){
$("boot").remove();
const C = {}; D.cols.forEach((c, i) => C[c] = i);
const R = D.rows, P = D.prof, N = R.length, MIN_T = 30;
const CTRL = D.groups.indexOf("Control");
const famName = n => D.fams[n].name;

// ------------------------------------------------------------------ header
const nCtrl = R.filter(r => r[C.grp] === CTRL).length;
const totTrades = R.reduce((a, r) => a + r[C.trades], 0);
$("meta").textContent = `${N.toLocaleString()} strategies (${nCtrl.toLocaleString()} random controls) · ${(totTrades / 1e6).toFixed(1)}M trades · ${D.meta.start} → ${D.meta.end} · score weights 8y ${D.weights["8y"]} · 3y ${D.weights["3y"]} · 6m ${D.weights["6m"]}`;
$("t-families").textContent = `Families (${Object.keys(D.fams).length})`;

// ------------------------------------------------------------------ columns
const COLS = {
  rank:{h:"#", w:46, sort:false, cls:"rk"},
  id:{h:"ID", w:78, l:1, cls:"id"},
  name:{h:"Strategy", w:250, l:1},
  mkt:{h:"Market", w:74, l:1},
  tf:{h:"TF", w:48, l:1, f:v => v + "m"},
  ses:{h:"Session", w:78, l:1},
  trades:{h:"Trades", w:70, f:v => v.toLocaleString()},
  pw:{h:"/ week", w:64, f:v => num(v, 2), tip:"trades per calendar week"},
  win:{h:"Win %", w:62, f:v => pc(v), tip:"share of trades with positive net R"},
  rr:{h:"Avg RR", w:64, f:v => num(v, 2), tip:"average winner ÷ average loser, net R"},
  net:{h:"Net R/tr", w:82, f:v => sgn(v, 3), c:1, tip:"net R per trade after costs, 8 years (1R = the amount risked)"},
  gross:{h:"Gross R/tr", w:86, f:v => sgn(v, 3), c:1, tip:"R per trade before costs"},
  tot:{h:"Total R", w:74, f:v => v == null ? "–" : (v < 0 ? MINUS : "") + Math.abs(Math.round(v)).toLocaleString(), c:1, tip:"sum of net R over 8 years"},
  usd:{h:"$ @ $250", w:92, f:usd, c:1, tip:"total net R × $250 risked per trade"},
  dd:{h:"Max DD", w:70, f:v => num(v, 1), tip:"largest peak-to-trough fall of cumulative net R, in R"},
  cost:{h:"Cost R", w:66, f:v => num(v, 3), tip:"average round-trip cost per trade (commission, spread, slippage) in R"},
  r12:{h:"12M R", w:84, f:(v, r) => `${v == null ? "–" : num(v, 1)} (${r[C.n12]})`, c:1, tip:"net R in the last 12 months (trades)"},
  e3y:{h:"3Y R/tr", w:98, f:(v, r) => `${sgn(v, 3)} (${r[C.n3y]})`, c:1, tip:"net R per trade over the last 3 years (trades)"},
  e6:{h:"6M R/tr", w:98, f:(v, r) => `${sgn(v, 3)} (${r[C.n6]})`, c:1, tip:"net R per trade over the last 6 months (trades); no rule was fitted to any window, but this window is part of the score"},
  score:{h:"Score", w:74, f:v => sgn(v, 3), c:1, tip:"0.25·E(8y) + 0.35·E(3y) + 0.40·E(6m), with E = net R ÷ (trades + 30)"},
  spre:{h:"Score −6M", w:88, f:v => sgn(v, 3), c:1, tip:"the score as it stood six months ago (last 6 months removed)"},
  uday:{h:"$/day", w:72, f:usdS, c:1, tip:"average net $ per trading day at $250 risk, counting every day"},
  dp10:{h:"$/day P10–P90", w:160, f:(v, r) => `${usdS(v)} … ${usdS(r[C.dp90])}`, tip:"10th to 90th percentile of daily P&L on days it traded"},
  yp:{h:"Years +", w:68, f:(v, r) => `${v}/${r[C.yn]}`, tip:"calendar years with positive net R / years with trades"},
  edge:{h:"Edge", w:74, f:v => sgn(v, 3), c:1, tip:"gross R/trade minus the median of random controls in the same market with the same exit"},
  et:{h:"Edge t", w:66, f:v => num(v, 2), c:1, tip:"edge ÷ its standard error; above the luck bar the edge is unlikely to be chance"},
  t:{h:"t-stat", w:62, f:v => num(v, 2), c:1, tip:"t-statistic of net R per trade"},
  pf:{h:"PF", w:56, f:v => num(v, 2), tip:"profit factor: gross wins ÷ gross losses"},
  pp:{h:"P(pass)", w:72, f:v => pc(v, 1), p:1, tip:"Monte Carlo odds of passing a 50K-style evaluation"},
  ppay:{h:"P(payout)", w:80, f:v => pc(v, 1), p:1, tip:"odds of passing and then reaching a first payout"},
};
const FROZEN = ["rank", "id", "name"];
const PRESETS = {
  Core:["rank","id","name","mkt","tf","ses","trades","win","net","e3y","e6","score","uday","pp"],
  Costs:["rank","id","name","mkt","tf","ses","trades","win","rr","net","gross","cost","tot","usd","dd","pf","t","edge","et"],
  Recency:["rank","id","name","mkt","tf","ses","trades","net","r12","e3y","e6","score","spre","yp","uday","dp10"],
  Prop:["rank","id","name","mkt","tf","ses","pw","win","net","uday","dp10","dd","yp","pp","ppay"],
  All:["rank","id","name","mkt","tf","ses","trades","pw","win","rr","net","gross","tot","usd","dd","cost","r12","e3y","e6","score","spre","uday","dp10","yp","edge","et","t","pf","pp","ppay"],
};
Object.entries(COLS).forEach(([k, c]) => { c.k = k; c.i = C[k]; });
let preset = PRESETS[store.get("cte.preset")] ? store.get("cte.preset") : "Core";

// ------------------------------------------------------------------ filters
function fill(el, items, label = x => x, any = "any"){
  el.innerHTML = (any ? `<option value="">${any}</option>` : "") + items.map(v => `<option value="${esc(v)}">${esc(label(v))}</option>`).join("");
}
fill($("fMkt"), Object.keys(D.markets), k => `${k} · ${D.markets[k].name}`);
fill($("fTf"), [...new Set(R.map(r => r[C.tf]))].sort((a, b) => a - b), v => v + "m");
fill($("fGrp"), D.groups.map((g, i) => i), i => D.groups[i]);
fill($("fFam"), Object.keys(D.fams).map(Number).sort((a, b) => a - b), n => `${D.fams[n].fid} · ${D.fams[n].name}`);
fill($("fSes"), Object.keys(D.sessions));
fill($("fEnt"), Object.keys(D.text.entry));
fill($("fStp"), Object.keys(D.text.stop));
fill($("fTgt"), Object.keys(D.text.target));
fill($("fSort"), PRESETS.All.filter(k => k !== "rank"), k => COLS[k].h, "");
$("preset").innerHTML = Object.keys(PRESETS).map(p => `<button type="button" data-p="${p}" aria-pressed="${p === preset}">${p}</button>`).join("");

const state = {sort: "score", dir: -1, view: [], sel: -1};
const hay = R.map(r => `${r[C.id]} ${r[C.name]} ${famName(r[C.fam])} ${r[C.mkt]} ${r[C.ses]} ${D.groups[r[C.grp]]} ${r[C.tf]}m ${r[C.tgt]} ${r[C.ent]}`.toLowerCase());

function apply(keepSel = true){
  const q = $("q").value.trim().toLowerCase(), mk = $("fMkt").value, tf = $("fTf").value, gr = $("fGrp").value,
        fa = $("fFam").value, se = $("fSes").value, en = $("fEnt").value, st = $("fStp").value, tg = $("fTgt").value,
        mn = +$("fMin").value || 0, mw = $("fMaxW").value === "" ? null : +$("fMaxW").value, only = $("fOnly").value;
  const out = [];
  for (let i = 0; i < N; i++){
    const r = R[i];
    if (q && !hay[i].includes(q)) continue;
    if (mk && r[C.mkt] !== mk) continue;
    if (tf && r[C.tf] != +tf) continue;
    if (gr !== "" && r[C.grp] != +gr) continue;
    if (fa && r[C.fam] != +fa) continue;
    if (se && r[C.ses] !== se) continue;
    if (en && r[C.ent] !== en) continue;
    if (st && r[C.stp] !== st) continue;
    if (tg && r[C.tgt] !== tg) continue;
    if (r[C.trades] < mn) continue;
    if (mw != null && r[C.pw] > mw) continue;
    const isC = r[C.grp] === CTRL;
    if (only === "noctrl" && isC) continue;
    if (only === "ctrl" && !isC) continue;
    if (only === "net" && !(r[C.tot] > 0)) continue;
    if (only === "allwin" && !(r[C.tot] > 0 && (r[C.e3y] || 0) > 0 && (r[C.e6] || 0) > 0)) continue;
    if (only === "beat" && !(r[C.edge] > 0 && r[C.et] > D.t95 && r[C.trades] >= MIN_T)) continue;
    if (only === "prop" && !(r[C.pp] >= 0.5)) continue;
    if (only === "active" && !(r[C.pw] >= 1)) continue;
    out.push(i);
  }
  state.view = out;
  sortView();
  const keep = keepSel && state.sel >= 0 && out.indexOf(state.sel) >= 0;
  $("count").innerHTML = `<b>${out.length.toLocaleString()}</b> of ${N.toLocaleString()} strategies`;
  gwrap.scrollTop = 0;
  select(keep ? state.sel : (out.length ? out[0] : -1));
  if (keep) ensureVisible(); else renderList();
}
function sortView(){
  const col = COLS[state.sort], i = col.i, d = state.dir;
  state.view.sort((a, b) => {
    const x = R[a][i], y = R[b][i];
    if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1;
    if (typeof x === "string") return d * x.localeCompare(y);
    return d * (x - y);
  });
  $("fSort").value = state.sort;
}

// ------------------------------------------------------------------ table (virtualised)
const gwrap = $("gwrap"), gbody = $("gbody"), cardsEl = $("cards");
let rowH = 33;
const cardH = 84, HEAD_H = 36;
const mobile = matchMedia("(max-width:760px)");
const narrow = matchMedia("(max-width:1060px)");
const cols = () => PRESETS[preset].map(k => COLS[k]);
function head(){
  const cs = cols(); let left = 0;
  $("gcols").innerHTML = cs.map(c => `<col style="width:${c.w}px">`).join("");
  $("ghead").innerHTML = "<tr>" + cs.map(c => {
    const fz = FROZEN.includes(c.k), st = fz ? ` style="left:${left}px"` : "";
    if (fz) left += c.w;
    const on = state.sort === c.k;
    const cl = [c.l ? "l" : "", fz ? "fz" : "", c.k === "name" ? "fzl" : ""].join(" ");
    return `<th class="${cl}"${st} data-k="${c.k}" title="${esc(c.tip || "")}"${on ? ` aria-sort="${state.dir < 0 ? "descending" : "ascending"}"` : ""}>${esc(c.h)}${on ? `<span class="arr">${state.dir < 0 ? "▼" : "▲"}</span>` : ""}</th>`;
  }).join("") + "</tr>";
}
const pclass = v => v == null ? "mut" : v >= 0.5 ? "p-hi" : v >= 0.2 ? "p-mid" : v > 0 ? "" : "mut";
const fullName = r => `${r[C.name]} · ${r[C.mkt]} ${r[C.tf]}m ${r[C.ses]} · ${r[C.ent]} entry, ${r[C.stp]} stop, ${r[C.tgt]}`;
function cellsFor(ri, pos){
  const r = R[ri]; let left = 0;
  return cols().map(c => {
    const v = c.k === "rank" ? pos + 1 : r[c.i];
    const txt = c.f ? c.f(v, r) : v;
    let cl = (c.l ? "l " : "") + (c.cls ? c.cls + " " : "") + (c.c ? tone(v) + " " : "") + (c.p ? pclass(v) + " " : "");
    let st = "";
    if (FROZEN.includes(c.k)){ cl += "fz "; st = ` style="left:${left}px"`; left += c.w; }
    if (c.k === "name"){
      const tag = r[C.grp] === CTRL ? `<span class="tag">CTRL</span>` : "";
      return `<td class="${cl}fzl"${st} title="${esc(fullName(r))}">${tag}${esc(txt)}</td>`;
    }
    return `<td class="${cl}"${st}>${esc(txt)}</td>`;
  }).join("");
}
const renderList = () => mobile.matches ? renderCards() : renderGrid();
function renderGrid(){
  const v = state.view, n = v.length, cs = cols().length;
  const top = Math.max(0, gwrap.scrollTop - HEAD_H), vh = gwrap.clientHeight;
  const s = Math.max(0, Math.floor(top / rowH) - 10), e = Math.min(n, Math.ceil((top + vh) / rowH) + 10);
  let h = `<tr class="spacer"><td colspan="${cs}" style="height:${s * rowH}px"></td></tr>`;
  for (let p = s; p < e; p++){
    const ri = v[p], r = R[ri];
    h += `<tr data-i="${ri}" class="${p % 2 ? "alt " : ""}${ri === state.sel ? "sel " : ""}${r[C.grp] === CTRL ? "ctrl" : ""}">${cellsFor(ri, p)}</tr>`;
  }
  h += `<tr class="spacer"><td colspan="${cs}" style="height:${(n - e) * rowH}px"></td></tr>`;
  gbody.innerHTML = h;
  const first = gbody.querySelector("tr[data-i]");
  if (first){ const hh = first.getBoundingClientRect().height; if (hh > 10 && Math.abs(hh - rowH) > 0.5){ rowH = hh; return renderGrid(); } }
  $("foot").textContent = n ? `rows ${(s + 1).toLocaleString()}–${e.toLocaleString()} of ${n.toLocaleString()} · sorted by ${COLS[state.sort].h}, ${state.dir < 0 ? "high to low" : "low to high"}` : "No strategy matches these filters. Loosen one, or press Reset.";
}
function renderCards(){
  const v = state.view, n = v.length;
  cardsEl.style.height = (n * cardH) + "px";
  const top = gwrap.scrollTop, vh = gwrap.clientHeight;
  const s = Math.max(0, Math.floor(top / cardH) - 6), e = Math.min(n, Math.ceil((top + vh) / cardH) + 6);
  let h = "";
  for (let p = s; p < e; p++){
    const ri = v[p], r = R[ri];
    h += `<div class="card ${ri === state.sel ? "sel" : ""}" data-i="${ri}" style="top:${p * cardH}px;height:${cardH}px">
      <div class="t1"><span><span class="id">${esc(r[C.id])}</span> · ${esc(r[C.mkt])} ${r[C.tf]}m · ${esc(r[C.ses])}</span><span>#${p + 1}</span></div>
      <div class="t2">${r[C.grp] === CTRL ? '<span class="tag">CTRL</span>' : ""}${esc(r[C.name])}</div>
      <div class="t3"><span>Net <b class="${tone(r[C.net])}">${sgn(r[C.net], 3)}R</b></span><span>Win <b>${pc(r[C.win])}</b></span><span>Trades <b>${r[C.trades].toLocaleString()}</b></span><span>Score <b class="${tone(r[C.score])}">${sgn(r[C.score], 3)}</b></span></div></div>`;
  }
  cardsEl.innerHTML = h;
  $("foot").textContent = n ? `${n.toLocaleString()} strategies · sorted by ${COLS[state.sort].h}` : "No strategy matches these filters.";
}
let raf = 0;
gwrap.addEventListener("scroll", () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; renderList(); }); }, {passive: true});
let rz = 0;
window.addEventListener("resize", () => { clearTimeout(rz); rz = setTimeout(() => { renderList(); renderInspector(); }, 120); });

$("ghead").addEventListener("click", e => {
  const th = e.target.closest("th"); if (!th) return;
  const k = th.dataset.k, c = COLS[k]; if (!c || c.sort === false) return;
  if (state.sort === k) state.dir *= -1; else { state.sort = k; state.dir = c.l ? 1 : -1; }
  sortView(); head(); gwrap.scrollTop = 0; renderList(); renderInspector();
});
$("fSort").addEventListener("change", e => { state.sort = e.target.value; state.dir = COLS[state.sort].l ? 1 : -1; sortView(); head(); gwrap.scrollTop = 0; renderList(); renderInspector(); });
gwrap.addEventListener("click", e => { const el = e.target.closest("[data-i]"); if (el) select(+el.dataset.i, true); });
$("preset").addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  preset = b.dataset.p; store.set("cte.preset", preset);
  $("preset").querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b));
  head(); renderList();
});
["q", "fMin", "fMaxW"].forEach(id => $(id).addEventListener("input", () => apply()));
["fMkt","fTf","fGrp","fFam","fSes","fEnt","fStp","fTgt","fOnly"].forEach(id => $(id).addEventListener("change", () => apply()));
$("reset").addEventListener("click", () => resetFilters());
function resetFilters(){
  $("q").value = ""; ["fMkt","fTf","fGrp","fFam","fSes","fEnt","fStp","fTgt"].forEach(id => $(id).value = "");
  $("fMin").value = 30; $("fMaxW").value = ""; $("fOnly").value = "all"; state.sort = "score"; state.dir = -1; head(); apply(false);
}
$("moreBtn").addEventListener("click", () => { const t = $("toolbar").classList.toggle("open"); $("moreBtn").setAttribute("aria-expanded", t); });

// ------------------------------------------------------------------ selection & keyboard
function select(ri, open = false){
  state.sel = ri;
  gwrap.querySelectorAll(".sel").forEach(t => t.classList.remove("sel"));
  const el = gwrap.querySelector(`[data-i="${ri}"]`); if (el) el.classList.add("sel");
  renderInspector();
  if (open && narrow.matches) $("inspPane").dataset.open = "true";
}
function ensureVisible(){
  const p = state.view.indexOf(state.sel); if (p < 0) return renderList();
  const h = mobile.matches ? cardH : rowH, off = mobile.matches ? 0 : HEAD_H;
  const y = p * h, top = gwrap.scrollTop, vh = gwrap.clientHeight - off;
  if (y < top) gwrap.scrollTop = y;
  else if (y + h > top + vh) gwrap.scrollTop = y + h - vh;
  renderList();
}
function step(d){
  const v = state.view; if (!v.length) return;
  let p = v.indexOf(state.sel); p = Math.max(0, Math.min(v.length - 1, (p < 0 ? 0 : p) + d));
  select(v[p]); ensureVisible();
}
document.addEventListener("keydown", e => {
  const typing = /INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName);
  if (e.key === "/" && !typing){ e.preventDefault(); $("q").focus(); $("q").select(); return; }
  if (e.key === "Escape"){ if (typing) document.activeElement.blur(); $("inspPane").dataset.open = "false"; return; }
  if (typing || $("v-strategies").hidden) return;
  const map = {ArrowDown:1, ArrowUp:-1, j:1, k:-1, PageDown:20, PageUp:-20, Home:-1e9, End:1e9};
  if (e.key in map){ e.preventDefault(); step(map[e.key]); }
  else if (e.key === "Enter" && narrow.matches){ $("inspPane").dataset.open = "true"; }
});

// ------------------------------------------------------------------ inspector
function tdm(x){ const t = (x + 18 * 60) % 1440; return String(Math.floor(t / 60)).padStart(2, "0") + ":" + String(t % 60).padStart(2, "0"); }
function niceTicks(lo, hi, n = 4){
  const span = hi - lo || 1, raw = span / n, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const s = [1, 2, 2.5, 5, 10].map(m => m * mag).find(x => span / x <= n) || 10 * mag;
  const out = []; for (let v = Math.floor(lo / s) * s; v <= hi + s * 1e-6; v += s) out.push(+v.toFixed(10));
  if (out[out.length - 1] < hi) out.push(+(out[out.length - 1] + s).toFixed(10));
  return out;
}
const tile = (k, v, cls, d) => `<div class="tile"><div class="k">${esc(k)}</div><div class="v ${cls}">${esc(v)}</div><div class="d">${esc(d)}</div></div>`;
function renderInspector(){
  const box = $("insp"), ri = state.sel;
  if (ri < 0){ box.innerHTML = `<div class="ibody"><p class="thesis">No strategy matches these filters. Loosen one, or press Reset.</p></div>`; return; }
  const r = R[ri], p = P[ri], f = D.fams[r[C.fam]], isC = r[C.grp] === CTRL, mk = D.markets[r[C.mkt]];
  const pills = [];
  if (isC) pills.push(["warn", "Random control"]);
  if (r[C.trades] < MIN_T) pills.push(["warn", "Fewer than 30 trades"]);
  if (r[C.edge] > 0 && r[C.et] > D.t95 && r[C.trades] >= MIN_T) pills.push(["good", "Edge clears the luck bar"]);
  else if (!isC) pills.push(["bad", "Edge within luck"]);
  if (r[C.tot] > 0 && (r[C.e3y] || 0) > 0 && (r[C.e6] || 0) > 0) pills.push(["good", "Profitable 8y · 3y · 6m"]);
  else if (r[C.tot] > 0) pills.push(["warn", "Profitable over 8y, not in every window"]);
  else pills.push(["bad", "Net loser over 8 years"]);
  const rules = [];
  if (isC) rules.push(`<b>signal</b> — random, about one every two sessions, long or short on a coin flip`);
  else p.lg.forEach(c => rules.push(`<b>${esc(D.legs[c].kind)}</b> — ${esc(D.legs[c].text)}`));
  rules.push(`<b>entry</b> — ${esc(D.text.entry[r[C.ent]])}`);
  rules.push(`<b>stop</b> — ${esc(D.text.stop[r[C.stp]])}, never tighter than 0.3 ATR`);
  rules.push(`<b>target</b> — ${esc(D.text.target[r[C.tgt]])}`);
  const sv = D.sessions[r[C.ses]];
  rules.push(`<b>session</b> — ${esc(r[C.ses])}: entries ${tdm(sv[0])}–${tdm(sv[1])} ET, flat by ${tdm(sv[2])} ET, at most 4 trades a day. Shorts mirror every rule.`);
  const w = D.weights, sh = D.shrink;
  const e8 = r[C.tot] / (r[C.trades] + sh), e3 = (p.r3 || 0) / (r[C.n3y] + sh), e6 = (p.r6 || 0) / (r[C.n6] + sh);
  const wins = [["8 years", r[C.trades], r[C.net], r[C.tot]], ["3 years", r[C.n3y], r[C.e3y], p.r3], ["12 months", r[C.n12], r[C.n12] ? r[C.r12] / r[C.n12] : null, r[C.r12]], ["6 months", r[C.n6], r[C.e6], p.r6]];
  const ex = p.ex || [0, 0, 0, 0], side = p.side || [0, 0, 0, 0];
  const pos = state.view.indexOf(ri);
  box.innerHTML = `
  <div class="ihead">
    <div class="row1"><span class="sid">${esc(r[C.id])}</span><span class="mut">${pos >= 0 ? `#${(pos + 1).toLocaleString()} of ${state.view.length.toLocaleString()}` : ""}</span>
      <span class="nav"><button type="button" id="iPrev" title="Previous (↑)" aria-label="Previous strategy">↑</button><button type="button" id="iNext" title="Next (↓)" aria-label="Next strategy">↓</button><button type="button" class="close" id="iClose">Close</button></span></div>
    <h2>${esc(r[C.name])}</h2>
    <div class="sub">${esc(r[C.mkt])} · ${esc(mk.name)} · ${r[C.tf]}m · ${esc(r[C.ses])} · ${esc(r[C.ent])} entry, ${esc(r[C.stp])} stop, ${esc(r[C.tgt])}</div>
    <div class="pills">${pills.map(([k, t]) => `<span class="pill ${k}"><i></i>${esc(t)}</span>`).join("")}</div>
  </div>
  <div class="ibody">
    <p class="thesis">${esc(f.thesis)}</p>
    <div class="tiles">
      ${tile("Net R per trade", sgn(r[C.net], 3), tone(r[C.net]), `gross ${sgn(r[C.gross], 3)} · cost ${num(r[C.cost], 3)}`)}
      ${tile("Win rate", pc(r[C.win]), "", `avg RR ${num(r[C.rr], 2)} · PF ${num(r[C.pf], 2)}`)}
      ${tile("Trades", r[C.trades].toLocaleString(), "", `${num(r[C.pw], 2)} a week`)}
      ${tile("Avg $ per day", usdS(r[C.uday]), tone(r[C.uday]), `3y ${usdS(p.u3)} · 6m ${usdS(p.u6)}`)}
      ${tile("Max drawdown", num(r[C.dd], 1) + "R", "", `${usd(-r[C.dd] * D.risk)} at $250 risk`)}
      ${tile("Score", sgn(r[C.score], 3), tone(r[C.score]), `six months ago ${sgn(r[C.spre], 3)}`)}
    </div>
    <div class="sec"><h3>Equity, cumulative net R <em>shaded: last 3 years, last 6 months</em></h3><div class="chart" id="eqChart"></div></div>
    <div class="two">
      <div class="sec"><h3>Windows</h3>
        <table class="mini"><tr><th class="l">window</th><th>trades</th><th>R/trade</th><th>total R</th></tr>
        ${wins.map(x => `<tr><td class="l">${x[0]}</td><td>${x[1].toLocaleString()}</td><td class="${tone(x[2])}">${sgn(x[2], 3)}</td><td class="${tone(x[3])}">${x[3] == null ? "–" : num(x[3], 1)}</td></tr>`).join("")}</table></div>
      <div class="sec"><h3>Score build-up</h3><dl class="kv">
        <dt>${w["8y"]} × E(8y)</dt><dd class="${tone(e8)}">${sgn(w["8y"] * e8, 4)}</dd>
        <dt>${w["3y"]} × E(3y)</dt><dd class="${tone(e3)}">${sgn(w["3y"] * e3, 4)}</dd>
        <dt>${w["6m"]} × E(6m)</dt><dd class="${tone(e6)}">${sgn(w["6m"] * e6, 4)}</dd>
        <dt><b>score</b></dt><dd class="${tone(r[C.score])}"><b>${sgn(r[C.score], 4)}</b></dd>
        <dt>edge vs random</dt><dd class="${tone(r[C.edge])}">${sgn(r[C.edge], 3)}R</dd>
        <dt>edge t · luck bar ${D.t95.toFixed(2)}</dt><dd class="${r[C.et] > D.t95 ? "pos" : "mut"}">${num(r[C.et], 2)}</dd></dl></div>
    </div>
    <div class="sec"><h3>Net R by calendar year <em>trades in brackets</em></h3><div class="chart" id="yrChart"></div></div>
    <div class="sec"><h3>Profit per day at $250 risk <em>days it traded</em></h3><div class="chart" id="dayChart"></div>
      <dl class="kv" style="margin-top:10px"><dt>days traded · green days</dt><dd>${(p.ad || 0).toLocaleString()} · ${pc(r[C.green])}</dd>
      <dt>typical range, P10 … P90</dt><dd>${usdS(r[C.dp10])} … ${usdS(r[C.dp90])}</dd>
      <dt>worst · best day</dt><dd><span class="neg">${usdS(p.dmin)}</span> · <span class="pos">${usdS(p.dmax)}</span></dd></dl></div>
    <div class="sec"><h3>Rules <em>long side</em></h3><ol class="rules">${rules.map(x => `<li>${x}</li>`).join("")}</ol></div>
    <div class="two">
      <div class="sec"><h3>Prop evaluation</h3><dl class="kv">
        <dt>P(pass eval)</dt><dd class="${pclass(r[C.pp])}">${pc(r[C.pp], 1)}</dd>
        <dt>P(pass + payout)</dt><dd class="${pclass(r[C.ppay])}">${pc(r[C.ppay], 1)}</dd>
        <dt>median days to pass</dt><dd>${p.pd == null ? "–" : num(p.pd, 0)}</dd>
        <dt>target · trailing DD</dt><dd>$${D.prop.target.toLocaleString()} · $${D.prop.mll.toLocaleString()}</dd></dl></div>
      <div class="sec"><h3>Exits and sides</h3><dl class="kv">
        <dt>stop · target</dt><dd>${ex[0].toLocaleString()} · ${ex[1].toLocaleString()}</dd>
        <dt>trail · time</dt><dd>${ex[2].toLocaleString()} · ${ex[3].toLocaleString()}</dd>
        <dt>longs, net R</dt><dd>${side[0]} · <span class="${tone(side[1])}">${sgn(side[1], 1)}</span></dd>
        <dt>shorts, net R</dt><dd>${side[2]} · <span class="${tone(side[3])}">${sgn(side[3], 1)}</span></dd>
        <dt>best · worst trade</dt><dd>${sgn(p.best, 2)} · ${sgn(p.worst, 2)}</dd>
        <dt>longest losing run</dt><dd>${p.stk} trades</dd></dl></div>
    </div>
    <div class="sec"><h3>Last trades</h3><table class="mini"><tr><th class="l">day</th><th class="l">side</th><th class="l">exit</th><th>net R</th></tr>
      ${(p.last || []).slice().reverse().map(t => `<tr><td class="l">${esc(t[0])}</td><td class="l">${t[1] > 0 ? "long" : "short"}</td><td class="l">${["stop", "target", "trail", "time"][t[3]]}</td><td class="${tone(t[2])}">${sgn(t[2], 2)}</td></tr>`).join("") || `<tr><td class="l" colspan="4">No trades</td></tr>`}</table></div>
  </div>`;
  $("iPrev").onclick = () => step(-1);
  $("iNext").onclick = () => step(1);
  $("iClose").onclick = () => { $("inspPane").dataset.open = "false"; };
  drawEquity($("eqChart"), p.eq || []);
  drawYears($("yrChart"), Object.entries(p.yrs || {}));
  drawDays($("dayChart"), p);
}

// ------------------------------------------------------------------ charts
function drawEquity(host, eq){
  if (!eq.length){ host.innerHTML = `<p class="mut">No trades.</p>`; return; }
  const W = Math.max(280, host.clientWidth || 440), H = 200, pl = 46, pr = 50, pt = 18, pb = 22, n = eq.length;
  const ticks = niceTicks(Math.min(0, ...eq), Math.max(0, ...eq), 4), y0 = ticks[0], y1 = ticks[ticks.length - 1];
  const x = i => pl + (W - pl - pr) * i / Math.max(n - 1, 1), y = v => pt + (H - pt - pb) * (1 - (v - y0) / ((y1 - y0) || 1));
  const i3 = Math.max(0, n - 36), i6 = Math.max(0, n - 6), last = eq[n - 1];
  const line = eq.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const area = `${line}L${x(n - 1).toFixed(1)},${y(0).toFixed(1)}L${x(0).toFixed(1)},${y(0).toFixed(1)}Z`;
  const col = last >= 0 ? "var(--gain)" : "var(--loss)";
  let g = `<rect x="${x(i3)}" y="${pt}" width="${x(n - 1) - x(i3)}" height="${H - pt - pb}" fill="var(--band-3y)"/>`
        + `<rect x="${x(i6)}" y="${pt}" width="${x(n - 1) - x(i6)}" height="${H - pt - pb}" fill="var(--band-6m)"/>`
        + `<text x="${x(i3) + 4}" y="${pt - 6}">last 3Y</text><text x="${x(i6) + 4}" y="${pt - 6}">6M</text>`;
  ticks.forEach(t => { g += `<line x1="${pl}" x2="${W - pr}" y1="${y(t)}" y2="${y(t)}" stroke="${t === 0 ? "var(--ink-3)" : "var(--line)"}" stroke-width="1"/><text x="${pl - 6}" y="${y(t) + 3.5}" text-anchor="end">${num(t, Math.abs(y1 - y0) < 8 ? 1 : 0)}R</text>`; });
  for (let k = 0; k < n; k++){ const m = D.months[k] || ""; if (m.endsWith("-01")) g += `<text x="${x(k)}" y="${H - 6}" text-anchor="middle">${m.slice(0, 4)}</text>`; }
  g += `<path d="${area}" fill="${col}" fill-opacity=".10"/><path d="${line}" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
  g += `<circle cx="${x(n - 1)}" cy="${y(last)}" r="4" fill="${col}" stroke="var(--panel)" stroke-width="2"/><text class="lab" x="${x(n - 1) + 8}" y="${y(last) + 3.5}">${sgn(last, 0)}R</text>`;
  g += `<line class="cx" y1="${pt}" y2="${H - pb}" stroke="var(--ink-2)" stroke-width="1" visibility="hidden"/><circle class="cd" r="4" fill="${col}" stroke="var(--panel)" stroke-width="2" visibility="hidden"/>`;
  g += `<rect class="hit" x="${pl}" y="0" width="${W - pl - pr}" height="${H}" fill="transparent"/>`;
  host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Cumulative net R by month, ending at ${sgn(last, 1)}R">${g}</svg><div class="tip"></div>`;
  const svg = host.querySelector("svg"), tip = host.querySelector(".tip"), cx = svg.querySelector(".cx"), dot = svg.querySelector(".cd");
  const hit = svg.querySelector(".hit");
  hit.addEventListener("pointermove", ev => {
    const b = svg.getBoundingClientRect(), px = (ev.clientX - b.left) * W / b.width;
    const i = Math.max(0, Math.min(n - 1, Math.round((px - pl) / ((W - pl - pr) / Math.max(n - 1, 1)))));
    cx.setAttribute("x1", x(i)); cx.setAttribute("x2", x(i)); cx.setAttribute("visibility", "visible");
    dot.setAttribute("cx", x(i)); dot.setAttribute("cy", y(eq[i])); dot.setAttribute("visibility", "visible");
    tip.style.display = "block"; tip.style.left = (x(i) * b.width / W) + "px"; tip.style.top = (y(eq[i]) * b.height / H) + "px";
    tip.textContent = "";
    const bb = document.createElement("b"); bb.textContent = sgn(eq[i], 1) + "R";
    const sp = document.createElement("span"); sp.textContent = D.months[i] || "";
    tip.append(bb, sp);
  });
  hit.addEventListener("pointerleave", () => { cx.setAttribute("visibility", "hidden"); dot.setAttribute("visibility", "hidden"); tip.style.display = "none"; });
}
function barPath(x, yb, ye, w, rad){
  const h = Math.abs(ye - yb), r = Math.min(rad, h, w / 2);
  if (h < 0.5) return `M${x},${yb}h${w}v0.5h${-w}Z`;
  const up = ye < yb, s = up ? 1 : -1;
  return `M${x},${yb}V${ye + s * r}Q${x},${ye} ${x + r},${ye}H${x + w - r}Q${x + w},${ye} ${x + w},${ye + s * r}V${yb}Z`;
}
function drawYears(host, yrs){
  if (!yrs.length){ host.innerHTML = ""; return; }
  const W = Math.max(280, host.clientWidth || 440), H = 160, pt = 16, pb = 34, n = yrs.length, band = (W - 16) / n;
  const vals = yrs.map(y => y[1][1]), mx = Math.max(1, ...vals.map(Math.abs));
  const z = pt + (H - pt - pb) / 2, s = (H - pt - pb) / 2 / mx, bw = Math.min(24, band * 0.6);
  let g = `<line x1="8" x2="${W - 8}" y1="${z}" y2="${z}" stroke="var(--ink-3)" stroke-width="1"/>`;
  yrs.forEach((yv, i) => {
    const v = yv[1][1], cnt = yv[1][0], xx = 8 + i * band + (band - bw) / 2, ye = z - v * s, cxm = xx + bw / 2;
    g += `<path d="${barPath(xx, z, ye, bw, 4)}" fill="${v >= 0 ? "var(--gain)" : "var(--loss)"}" fill-opacity="${cnt ? 0.9 : 0.25}"><title>${yv[0]}: ${sgn(v, 1)}R on ${cnt} trades</title></path>`;
    if (cnt) g += `<text class="lab" x="${cxm}" y="${v >= 0 ? ye - 4 : ye + 12}" text-anchor="middle">${sgn(v, Math.abs(v) < 10 ? 1 : 0)}</text>`;
    g += `<text x="${cxm}" y="${H - 18}" text-anchor="middle">${yv[0]}</text><text x="${cxm}" y="${H - 5}" text-anchor="middle">(${cnt})</text>`;
  });
  host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Net R by calendar year">${g}</svg>`;
}
function drawDays(host, p){
  const q = p.dq; if (!q || !q.length){ host.innerHTML = `<p class="mut">No trades.</p>`; return; }
  const W = Math.max(280, host.clientWidth || 440), H = 66, pl = 14, pr = 14;
  const lo = Math.min(q[0], 0), hi = Math.max(q[6], 0), X = v => pl + (W - pl - pr) * (v - lo) / ((hi - lo) || 1), ym = 28;
  const g = `<line x1="${X(q[0])}" x2="${X(q[6])}" y1="${ym}" y2="${ym}" stroke="var(--ink-3)" stroke-width="1.5"/>`
    + `<line x1="${X(q[0])}" x2="${X(q[0])}" y1="${ym - 6}" y2="${ym + 6}" stroke="var(--ink-3)"/><line x1="${X(q[6])}" x2="${X(q[6])}" y1="${ym - 6}" y2="${ym + 6}" stroke="var(--ink-3)"/>`
    + `<rect x="${X(q[2])}" y="${ym - 9}" width="${Math.max(X(q[4]) - X(q[2]), 2)}" height="18" rx="3" fill="var(--accent)" fill-opacity=".35"/>`
    + `<line x1="${X(q[3])}" x2="${X(q[3])}" y1="${ym - 11}" y2="${ym + 11}" stroke="var(--ink)" stroke-width="2"/>`
    + `<line x1="${X(0)}" x2="${X(0)}" y1="${ym - 16}" y2="${ym + 16}" stroke="var(--loss)" stroke-width="1"/>`
    + `<text x="${X(q[0])}" y="10" text-anchor="start">P5 ${usdS(q[0])}</text><text x="${X(q[6])}" y="10" text-anchor="end">P95 ${usdS(q[6])}</text>`
    + `<text x="${X(q[3])}" y="${ym + 26}" text-anchor="middle" class="lab">median ${usdS(q[3])}</text>`;
  host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Distribution of daily profit: P5 ${usdS(q[0])}, median ${usdS(q[3])}, P95 ${usdS(q[6])}">${g}</svg>`;
}

// ------------------------------------------------------------------ views
const VIEWS = ["strategies", "families", "dimensions", "lessons", "guide"];
function show(v){
  VIEWS.forEach(x => { $("v-" + x).hidden = x !== v; $("t-" + x).setAttribute("aria-selected", x === v); });
  if (v === "families") renderFamilies();
  if (v === "dimensions") renderDims();
  if (v === "strategies"){ renderList(); renderInspector(); }
  try { history.replaceState(null, "", "#" + v); } catch (e) {}
}
document.querySelectorAll(".tab").forEach(b => b.addEventListener("click", () => show(b.dataset.view)));

function median(a){ const v = a.filter(x => x != null).sort((x, y) => x - y); if (!v.length) return null; const h = v.length >> 1; return v.length % 2 ? v[h] : (v[h - 1] + v[h]) / 2; }
const share = (a, fn) => a.length ? a.filter(fn).length / a.length : null;
const enough = idx => idx.filter(i => R[i][C.trades] >= MIN_T);

let famRows = null, famSort = {k: "edge", d: -1};
function renderFamilies(){
  if (!famRows){
    const by = {}; for (let i = 0; i < N; i++) (by[R[i][C.fam]] ||= []).push(i);
    famRows = Object.keys(D.fams).map(Number).map(n => {
      const all = by[n] || [], e = enough(all); let best = null;
      e.forEach(i => { if (best == null || R[i][C.score] > R[best][C.score]) best = i; });
      return {n, fid: D.fams[n].fid, name: D.fams[n].name, grp: D.groups[D.fams[n].grp], count: all.length, pw: median(all.map(i => R[i][C.pw])),
        win: median(e.map(i => R[i][C.win])), prof: share(e, i => R[i][C.tot] > 0), net: median(e.map(i => R[i][C.net])),
        edge: median(e.map(i => R[i][C.edge])), beat: share(e, i => R[i][C.edge] > 0 && R[i][C.et] > D.t95), best, bscore: best == null ? null : R[best][C.score]};
    });
  }
  const H = [["fid","#",1],["name","Family",1],["grp","Group",1],["count","Strategies"],["pw","Trades / wk"],["win","Win %"],["prof","% profitable"],["net","Median net R/tr"],["edge","Median edge"],["beat","% clear luck bar"],["bscore","Best score"]];
  const rows = famRows.slice().sort((a, b) => { const x = a[famSort.k], y = b[famSort.k]; if (x == null) return 1; if (y == null) return -1; return typeof x === "string" ? famSort.d * x.localeCompare(y) : famSort.d * (x - y); });
  const t = $("famTbl");
  t.querySelector("thead").innerHTML = "<tr>" + H.map(([k, h, l]) => `<th class="${l ? "l" : ""}" data-k="${k}"${famSort.k === k ? ` aria-sort="${famSort.d < 0 ? "descending" : "ascending"}"` : ""}>${h}${famSort.k === k ? (famSort.d < 0 ? " ▼" : " ▲") : ""}</th>`).join("") + `<th class="l">Best strategy (click a row to list the family)</th></tr>`;
  t.querySelector("tbody").innerHTML = rows.map(x => {
    const f = D.fams[x.n], legs = f.legs.map(c => D.legs[c].label).join(" · ") || "coin flip", b = x.best != null ? R[x.best] : null;
    return `<tr data-f="${x.n}" title="${esc(f.thesis)}"><td class="l mut">${esc(x.fid)}</td><td class="l"><div class="fname">${esc(x.name)}</div><div class="flegs">${esc(legs)}</div></td><td class="l">${esc(x.grp)}</td><td>${x.count}</td><td>${num(x.pw, 2)}</td><td>${pc(x.win)}</td><td>${pc(x.prof)}</td><td class="${tone(x.net)}">${sgn(x.net, 3)}</td><td class="${tone(x.edge)}">${sgn(x.edge, 3)}</td><td>${pc(x.beat, 1)}</td><td class="${tone(x.bscore)}">${sgn(x.bscore, 3)}</td><td class="l">${b ? esc(`${b[C.id]} · ${b[C.mkt]} ${b[C.tf]}m ${b[C.ses]}`) : "–"}</td></tr>`;
  }).join("");
}
$("famTbl").addEventListener("click", e => {
  const th = e.target.closest("th[data-k]");
  if (th){ const k = th.dataset.k; famSort = famSort.k === k ? {k, d: -famSort.d} : {k, d: ["fid", "name", "grp"].includes(k) ? 1 : -1}; renderFamilies(); return; }
  const tr = e.target.closest("tr[data-f]"); if (!tr) return;
  resetFilters(); $("fFam").value = tr.dataset.f; apply(false); show("strategies");
});

let dimsDone = false;
function renderDims(){
  if (dimsDone) return; dimsDone = true;
  const idx = enough([...Array(N).keys()]);
  $("dimNote").textContent = `Strategies with at least ${MIN_T} trades (${idx.length.toLocaleString()} of ${N.toLocaleString()}). Bars show the median net R per trade around zero; edge compares gross R with random controls in the same market and exit style.`;
  const dims = [
    ["Group", i => D.groups[R[i][C.grp]]], ["Market", i => R[i][C.mkt]], ["Timeframe", i => R[i][C.tf] + "m"],
    ["Session", i => R[i][C.ses]], ["Entry order", i => R[i][C.ent]], ["Stop", i => R[i][C.stp]], ["Target or exit", i => R[i][C.tgt]],
    ["Confluence legs", i => R[i][C.grp] === CTRL ? "random control" : R[i][C.legs] + " legs"],
    ["Extra filter", i => R[i][C.grp] === CTRL ? "random control" : (R[i][C.xtra] ? D.legs[R[i][C.xtra]].label : "none")],
  ];
  $("dims").innerHTML = dims.map(([title, key]) => {
    const by = {}; idx.forEach(i => (by[key(i)] ||= []).push(i));
    const rows = Object.entries(by).map(([k, a]) => ({k, n: a.length, med: median(a.map(i => R[i][C.net])), edge: median(a.map(i => R[i][C.edge])),
      prof: share(a, i => R[i][C.tot] > 0), p6: share(a.filter(i => R[i][C.n6] > 0), i => R[i][C.e6] > 0), cost: median(a.map(i => R[i][C.cost])), pw: median(a.map(i => R[i][C.pw]))}));
    rows.sort((x, y) => (y.med ?? -9) - (x.med ?? -9));
    const mx = Math.max(0.05, ...rows.map(r => Math.abs(r.med || 0)));
    return `<div class="dcard"><h3>${esc(title)}</h3><table class="mini"><tr><th class="l">value</th><th>n</th><th>% profitable</th><th class="l">median net R/trade</th><th>edge</th><th>% up, 6M</th><th>cost R</th><th>trades/wk</th></tr>` +
      rows.map(r => { const w = 64 * Math.abs(r.med || 0) / mx, neg = (r.med || 0) < 0;
        return `<tr><td class="l">${esc(r.k)}</td><td>${r.n.toLocaleString()}</td><td>${pc(r.prof)}</td><td class="l"><span class="div-track"><span class="div-bar" style="${neg ? "right" : "left"}:50%;width:${w.toFixed(1)}px;background:${neg ? "var(--loss)" : "var(--gain)"}"></span></span> <span class="${tone(r.med)}">${sgn(r.med, 3)}</span></td><td class="${tone(r.edge)}">${sgn(r.edge, 3)}</td><td>${pc(r.p6)}</td><td>${num(r.cost, 3)}</td><td>${num(r.pw, 2)}</td></tr>`; }).join("") + `</table></div>`;
  }).join("");
}

const TONE = {good: ["var(--gain)", "Finding"], warn: ["var(--warn)", "Caution"], info: ["var(--accent)", "Context"]};
$("lessons").innerHTML = D.lessons.map(l => { const t = TONE[l.tone] || TONE.info; return `<div class="lcard"><div class="kind" style="color:${t[0]}"><i style="background:${t[0]}"></i>${t[1]}</div><h3>${esc(l.title)}</h3><p>${esc(l.body)}</p></div>`; }).join("");
(function guide(){
  const w = D.weights, pr = D.prop, q = D.meta.quality || {};
  const mk = Object.entries(D.markets).map(([k, v]) => { const c = q[k] || {};
    const chk = c.ret_corr_5m != null ? `${c.ret_corr_5m.toFixed(3)} vs ${esc(c.yahoo)} (${c.overlap_bars.toLocaleString()} bars)` : esc(c.error || "–");
    return `<tr><td>${k}</td><td>${esc(v.name)}</td><td>${esc(v.feed)}</td><td>${esc(v.cost)}</td><td>${chk}</td></tr>`; }).join("");
  const tv = Object.values(q._tradingview_spotcheck || {}).map(t => `<li>TradingView: ${esc(t.tradingview)} vs ${esc(t.feed)}, 5-minute return correlation ${Number(t.ret_corr_5m).toFixed(4)} over ${t.bars} bars.</li>`).join("");
  const ses = Object.entries(D.sessions).map(([k, v]) => `<tr><td>${esc(k)}</td><td>${tdm(v[0])} – ${tdm(v[1])}</td><td>${tdm(v[2])}</td></tr>`).join("");
  const colrows = PRESETS.All.filter(k => COLS[k].tip).map(k => `<tr><td>${esc(COLS[k].h)}</td><td>${esc(COLS[k].tip)}</td></tr>`).join("");
  $("guide").innerHTML = `
  <h2>What this is</h2>
  <p>${N.toLocaleString()} rule-based intraday strategies built from confluence. Each needs a bias (trend or regime), a location (a level, zone, sweep or breakout) and a trigger (the candle that says "now"), sometimes with one extra filter. All were backtested on 8 years of 1-minute data (${esc(D.meta.start)} → ${esc(D.meta.end)}) with realistic costs. Nothing was optimised: every variant was fixed before it was tested, and every one is shown, losers included.</p>
  <h2>Moving around</h2>
  <ul><li>Scroll the table in any direction. The header and the ID and strategy columns stay in place.</li>
  <li>Click a row, or press <code>↑</code> <code>↓</code> (<code>PgUp</code> <code>PgDn</code>, <code>Home</code> <code>End</code> to jump), to show it in the panel on the right.</li>
  <li>Press <code>/</code> to search. Click a column header to sort; click it again to reverse.</li>
  <li>Column sets: Core fits beside the detail panel on a laptop screen. Costs, Recency and Prop swap in the columns for those questions. All shows everything; scroll sideways and the ID and strategy columns stay put.</li>
  <li>Min trades starts at 30 so a strategy with one lucky trade cannot top the table. Set it to 0 to see everything.</li></ul>
  <h2>Columns</h2><div class="tw"><table><tr><th>column</th><th>meaning</th></tr>${colrows}</table></div>
  <h2>The score</h2>
  <p>score = ${w["8y"]} × E(8y) + ${w["3y"]} × E(3y) + ${w["6m"]} × E(6m), where E is the total net R in the window divided by (trades in the window + ${D.shrink}). The last 6 months weigh a little more than the last 3 years, and both more than the full 8. The added ${D.shrink} pulls strategies with few trades toward zero.</p>
  <h2>Luck bar and random controls</h2>
  <p>The random controls enter on a coin flip but use the same markets, sessions, stops, targets and costs. A strategy's edge is its gross R per trade minus the median of the controls with the same market and exit style. The luck bar, ${D.t95.toFixed(2)}, is the 95th percentile of the controls' own edge t-statistic. Below it, chance explains the result as well as skill does.</p>
  <h2>Prop evaluation model</h2>
  <p>2,000 Monte Carlo runs: reach +$${pr.target.toLocaleString()} before a $${pr.mll.toLocaleString()} end-of-day trailing drawdown within ${pr.days} trading days, drawing 5-day blocks of the strategy's daily P&amp;L with the same recency weights as the score. Payout: after passing, a fresh account with the same drawdown must reach ${pr.wins} winning days of $${pr.winusd}+ and $${pr.payout.toLocaleString()} profit within ${pr.fdays} days.</p>
  <h2>Markets, data and costs</h2>
  <p>1-minute history comes from histdata.com, checked month by month against Dukascopy and filled from Dukascopy where histdata is missing, thin, or filed under the wrong instrument. MNQ and MES use the index CFD feed that tracks the same underlying, charged futures costs. The last column checks each feed against the real contract on Yahoo (5-minute returns, last 60 days).</p>
  <div class="tw"><table><tr><th>market</th><th>instrument</th><th>feed</th><th>round-trip cost</th><th>check vs real contract</th></tr>${mk}</table></div>
  <ul>${tv}</ul>
  <h2>Sessions, New York time</h2><div class="tw"><table><tr><th>session</th><th>entries</th><th>flat by</th></tr>${ses}</table></div>
  <h2>How trades are simulated</h2>
  <ul><li>Signals are read on a bar's close and orders work from the next bar. Stops, targets, trailing stops and session exits are walked through the 1-minute bars underneath; when a stop and a target fall in the same minute, the stop counts first.</li>
  <li>Entries: market (next open), stop (1 tick through the signal bar, valid 3 bars) or limit (signal-bar midpoint, valid 3 bars). Stops are never tighter than 0.3 ATR.</li>
  <li>One position at a time, at most 4 trades a day, always flat by the session exit and never held across a data gap. VWAP is range-weighted because the feeds carry no reliable volume.</li></ul>
  <h2>Before trusting a number</h2>
  <p>Out of ${N.toLocaleString()} tests some will look excellent by chance. Prefer strategies profitable in all three windows whose edge clears the luck bar, compare them with the random controls, and read the blind test in Lessons. A backtest is a hypothesis, not a forecast.</p>`;
})();

// ------------------------------------------------------------------ boot
head();
apply(false);
const hash = (location.hash || "").slice(1);
if (VIEWS.includes(hash) && hash !== "strategies") show(hash);
}
})();
</script>
"""
