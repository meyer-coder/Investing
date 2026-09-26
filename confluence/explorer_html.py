"""The explorer page: one self-contained HTML file, no external requests.

Open ``results/explorer.html`` straight from disk.  All data is embedded as
JSON; sorting, filtering, the family and dimension roll-ups and each
strategy's profile are computed in the browser.
"""
from __future__ import annotations

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


def render(payload: dict) -> str:
    data = json.dumps(_clean(payload), separators=(",", ":"), allow_nan=False)
    data = data.replace("</", "<\\/")
    return TEMPLATE.replace("/*__DATA__*/", data)


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Confluence Trade Explorer</title>
<style>
:root{
  --bg:#0a1729; --bg2:#0d1d33; --panel:#10233d; --panel2:#132a48; --line:#1d3656; --line2:#27466d;
  --text:#dbe6f5; --muted:#8298b6; --dim:#5d7392; --accent:#2f80ed; --accent2:#1c5fbf;
  --pos:#35d08a; --pos2:#1f9a63; --neg:#ff6b7d; --neg2:#c2475a; --warn:#f2b84b; --chip:#17304f;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--text);font:13px/1.45 "Segoe UI",Inter,system-ui,-apple-system,Roboto,Arial,sans-serif}
button,input,select{font:inherit;color:inherit}
.top{display:flex;align-items:center;gap:18px;flex-wrap:wrap;padding:12px 16px;background:linear-gradient(180deg,#0d1f38,#0a1729);border-bottom:1px solid var(--line)}
.brand{font-size:20px;font-weight:700;letter-spacing:.2px;white-space:nowrap}
.tabs{display:flex;gap:8px;flex-wrap:wrap}
.tab{background:transparent;border:1px solid var(--line2);border-radius:999px;padding:6px 16px;cursor:pointer;color:var(--text)}
.tab:hover{border-color:var(--accent)}
.tab.on{background:var(--accent);border-color:var(--accent);color:#fff}
.meta{color:var(--muted);font-size:12px;flex:1;min-width:280px}
section{padding:12px 16px}
.filters{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px 12px;align-items:end}
.f label{display:block;font-size:11px;letter-spacing:.6px;color:var(--muted);text-transform:uppercase;margin:0 0 4px}
.f input,.f select{width:100%;background:var(--bg2);border:1px solid var(--line2);border-radius:6px;padding:7px 9px;outline:none}
.f input:focus,.f select:focus{border-color:var(--accent)}
.f.wide{grid-column:span 2}
.row2{display:flex;gap:12px;align-items:end;margin-top:10px;flex-wrap:wrap}
.btn{background:var(--accent2);border:1px solid var(--accent);border-radius:6px;padding:7px 16px;cursor:pointer;color:#fff}
.btn:hover{background:var(--accent)}
.btn.ghost{background:transparent;color:var(--text);border-color:var(--line2)}
.count{color:var(--muted);padding-bottom:8px}
.tablewrap{margin-top:12px;overflow:auto;max-height:calc(100vh - 290px);border:1px solid var(--line);border-radius:8px;background:var(--bg2)}
table{border-collapse:collapse;width:100%}
th,td{padding:7px 10px;white-space:nowrap;text-align:right;border-bottom:1px solid var(--line)}
th{position:sticky;top:0;background:var(--panel);color:var(--muted);font-size:11px;letter-spacing:.5px;text-transform:uppercase;font-weight:600;cursor:pointer;user-select:none;z-index:1}
th:hover{color:var(--text)}
th.sorted{color:#fff}
td.l,th.l{text-align:left}
tbody tr{cursor:pointer}
tbody tr:hover td{background:#12294a}
tbody tr.ctrl td{color:#aab8cc}
.pos{color:var(--pos)} .neg{color:var(--neg)} .mut{color:var(--dim)}
.p-hi{color:var(--pos);font-weight:600} .p-mid{color:#8fe3b8}
.name{max-width:330px;overflow:hidden;text-overflow:ellipsis}
.pager{display:flex;gap:10px;align-items:center;margin-top:10px;color:var(--muted);flex-wrap:wrap}
.pager .btn{padding:4px 12px}
.chip{display:inline-block;background:var(--chip);border:1px solid var(--line2);border-radius:999px;padding:2px 10px;margin:0 6px 6px 0;font-size:12px;color:var(--text)}
.chip.ctrl{border-color:var(--warn);color:var(--warn)}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.card h3{margin:0 0 8px;font-size:15px}
.card.good{border-left:4px solid var(--pos)} .card.warn{border-left:4px solid var(--warn)} .card.info{border-left:4px solid var(--accent)}
.card p{margin:0;color:#c3d1e6}
.dimgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:14px}
.dimgrid table td,.dimgrid table th{padding:5px 8px}
.bar{display:inline-block;height:8px;border-radius:4px;vertical-align:middle}
.how{max-width:1100px}
.how h2{font-size:16px;margin:22px 0 8px}
.how p,.how li{color:#c3d1e6}
.how table{width:auto;margin:6px 0 14px}
.how td,.how th{text-align:left;padding:5px 10px}
.how code{background:var(--bg2);padding:1px 5px;border-radius:4px;border:1px solid var(--line)}
#modal{position:fixed;inset:0;background:rgba(3,10,20,.72);display:flex;align-items:flex-start;justify-content:center;z-index:10;overflow:auto;padding:28px 12px}
#modal[hidden]{display:none}
.sheet{background:var(--bg2);border:1px solid var(--line2);border-radius:12px;max-width:1120px;width:100%;padding:18px 20px 24px;box-shadow:0 20px 60px rgba(0,0,0,.5)}
.sheet h2{margin:0 0 4px;font-size:18px}
.sheet .sub{color:var(--muted);margin-bottom:10px}
.close{float:right;background:transparent;border:1px solid var(--line2);border-radius:6px;color:var(--text);padding:4px 10px;cursor:pointer}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.box{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.box h4{margin:0 0 8px;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px}
.kv{display:grid;grid-template-columns:auto 1fr;gap:3px 14px}
.kv div:nth-child(odd){color:var(--muted)}
.kv div:nth-child(even){text-align:right}
.rules{margin:0;padding-left:18px;color:#c3d1e6}
.rules li{margin:2px 0}
.mini td,.mini th{padding:4px 8px;font-size:12px}
svg text{fill:var(--muted);font-size:10px}
@media (max-width:760px){.grid2,.grid3{grid-template-columns:1fr}.cards,.dimgrid{grid-template-columns:1fr}.f.wide{grid-column:span 1}.tablewrap{max-height:none}}
</style>
</head>
<body>
<header class="top">
  <div class="brand">Confluence Trade Explorer</div>
  <nav class="tabs">
    <button class="tab on" data-tab="all">All strategies</button>
    <button class="tab" data-tab="fam" id="famTab">Families</button>
    <button class="tab" data-tab="dims">Groups &amp; dimensions</button>
    <button class="tab" data-tab="lessons">Lessons</button>
    <button class="tab" data-tab="how">How to read</button>
  </nav>
  <div class="meta" id="meta"></div>
</header>

<section id="tab-all">
  <div class="filters">
    <div class="f wide"><label>Search</label><input id="q" placeholder="id, name, family, text"></div>
    <div class="f"><label>Market</label><select id="fMkt"></select></div>
    <div class="f"><label>Timeframe</label><select id="fTf"></select></div>
    <div class="f"><label>Group</label><select id="fGrp"></select></div>
    <div class="f wide"><label>Family</label><select id="fFam"></select></div>
    <div class="f"><label>Session</label><select id="fSes"></select></div>
    <div class="f"><label>Entry</label><select id="fEnt"></select></div>
    <div class="f"><label>Stop</label><select id="fStp"></select></div>
    <div class="f"><label>Target</label><select id="fTgt"></select></div>
    <div class="f"><label>Min trades</label><input id="fMin" type="number" min="0" value="30" title="30 by default so one lucky trade cannot top the table; set 0 to see everything"></div>
    <div class="f"><label>Max trades/week</label><input id="fMaxW" type="number" min="0" step="0.1" placeholder="any"></div>
  </div>
  <div class="row2">
    <div class="f" style="min-width:260px"><label>Only</label><select id="fOnly">
      <option value="all">everything</option>
      <option value="noctrl">hide random controls</option>
      <option value="ctrl">random controls only</option>
      <option value="net">net-profitable (8y)</option>
      <option value="allwin">profitable 8y + 3y + 6m</option>
      <option value="beat">beats random (edge t above the luck bar)</option>
      <option value="prop">prop candidates (P(pass) &ge; 50%)</option>
      <option value="active">&ge; 1 trade / week</option>
    </select></div>
    <button class="btn" id="reset">Reset</button>
    <span class="count" id="count"></span>
  </div>
  <div class="tablewrap"><table id="tbl"><thead></thead><tbody></tbody></table></div>
  <div class="pager">
    <button class="btn ghost" id="prev">&lsaquo; prev</button><span id="page"></span><button class="btn ghost" id="next">next &rsaquo;</button>
    <span>click any column to sort · click a row for the full profile · <code>results/strategies_ranked.csv</code> has the same table for Excel</span>
  </div>
</section>

<section id="tab-fam" hidden><div class="tablewrap" style="max-height:none"><table id="famTbl"><thead></thead><tbody></tbody></table></div></section>
<section id="tab-dims" hidden><p class="count" id="dimNote"></p><div class="dimgrid" id="dims"></div></section>
<section id="tab-lessons" hidden><div class="cards" id="lessons"></div></section>
<section id="tab-how" hidden><div class="how" id="how"></div></section>

<div id="modal" hidden><div class="sheet" id="sheet"></div></div>

<script id="data" type="application/json">/*__DATA__*/</script>
<script>
(function(){
"use strict";
const D = JSON.parse(document.getElementById("data").textContent);
const C = {}; D.cols.forEach((c,i)=>C[c]=i);
const R = D.rows, P = D.prof, N = R.length;
const MIN_T = 30;
const $ = id => document.getElementById(id);
const esc = s => String(s==null?"":s).replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const num = (v,d=2) => v==null? "–" : Number(v).toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d});
const sgn = (v,d=3,suf="") => v==null? "–" : (v>0?"+":v<0?"−":"")+Math.abs(v).toFixed(d)+suf;
const usd = v => v==null? "–" : (v<0?"−$":"$")+Math.abs(Math.round(v)).toLocaleString("en-US");
const usdS = v => v==null? "–" : (v>0?"+$":v<0?"−$":"$")+Math.abs(Math.round(v)).toLocaleString("en-US");
const pc = (v,d=0) => v==null? "–" : (100*v).toFixed(d)+"%";
const cls = v => v==null? "mut" : v>0? "pos" : v<0? "neg" : "mut";
const famName = n => D.fams[n].name;
const grpName = g => D.groups[g];

// ------------------------------------------------------------------ header
const m = D.meta;
const nCtrl = R.filter(r=>D.groups[r[C.grp]]==="Control").length;
$("meta").textContent = `${N.toLocaleString()} strategies (${(N-nCtrl).toLocaleString()} confluence + ${nCtrl.toLocaleString()} random controls) · 8-year test ${m.start} → ${m.end} · score weights 8y ${D.weights["8y"]} / 3y ${D.weights["3y"]} / 6m ${D.weights["6m"]} · generated ${m.generated}`;
$("famTab").textContent = `Families (${Object.keys(D.fams).length})`;

// ------------------------------------------------------------------ columns
const COLS = [
  {k:"rank", h:"#", v:(r,i)=>i+1, f:(v)=>v, nosort:true},
  {k:"id", h:"ID", l:1},
  {k:"name", h:"Strategy", l:1, cls:"name"},
  {k:"mkt", h:"Market", l:1},
  {k:"tf", h:"TF", l:1, f:v=>v+"m"},
  {k:"ses", h:"Session"},
  {k:"trades", h:"Trades", f:v=>v.toLocaleString()},
  {k:"pw", h:"Per week", f:v=>num(v,2)},
  {k:"win", h:"Win %", f:v=>pc(v)},
  {k:"rr", h:"Avg RR", f:v=>num(v,2), tip:"average winner ÷ average loser, net R"},
  {k:"net", h:"Net R/trade", f:v=>sgn(v,3,"R"), c:1},
  {k:"gross", h:"Gross R/trade", f:v=>sgn(v,3,"R"), c:1},
  {k:"tot", h:"Total net R", f:v=>v==null?"–":Math.round(v).toLocaleString(), c:1},
  {k:"usd", h:"$ at $250 risk", f:usd, c:1},
  {k:"dd", h:"Max DD (R)", f:v=>num(v,0)},
  {k:"cost", h:"Cost-in-R", f:v=>num(v,3)},
  {k:"r12", h:"Last 12M net R", f:(v,r)=>`${v==null?"–":num(v,1)} (${r[C.n12]})`, c:1},
  {k:"e3y", h:"3Y net R/trade", f:(v,r)=>`${sgn(v,3,"R")} (${r[C.n3y]})`, c:1},
  {k:"e6", h:"Last 6M (OOS)", f:(v,r)=>`${sgn(v,3,"R")} (${r[C.n6]})`, c:1, tip:"no parameter was fitted to any window, so these 6 months are out-of-sample for every rule — but they ARE part of the score you asked for; see Lessons for a blind test"},
  {k:"score", h:"Score", f:v=>sgn(v,3), c:1, tip:"0.25·E(8y) + 0.35·E(3y) + 0.40·E(6m), each E = total net R ÷ (trades + 30)"},
  {k:"uday", h:"Avg $/day", f:v=>v==null?"–":usdS(v), c:1, tip:"net $ per trading day (all days, not only days traded), $250 risk per trade"},
  {k:"dp10", h:"$/day range", f:(v,r)=>`${usdS(v)} … ${usdS(r[C.dp90])}`, tip:"10th to 90th percentile of daily P&L on days with a trade"},
  {k:"yp", h:"Years +", f:(v,r)=>`${v}/${r[C.yn]}`, tip:"calendar years with positive net R / years with trades"},
  {k:"edge", h:"Edge vs random", f:v=>sgn(v,3,"R"), c:1, tip:"gross R/trade minus the median gross R/trade of random controls in the same market with the same exit"},
  {k:"et", h:"Edge t", f:v=>num(v,2), c:1, tip:"t-statistic of the edge over random controls; above the luck bar (95th percentile of the controls' own edge t) it is unlikely to be luck"},
  {k:"t", h:"t-stat", f:v=>num(v,2), c:1, tip:"t-statistic of net R per trade"},
  {k:"pp", h:"P(pass eval)", f:v=>pc(v,1), p:1},
  {k:"ppay", h:"P(payout)", f:v=>pc(v,1), p:1},
];
COLS.forEach(c=>{ if(c.k in C) c.i=C[c.k]; });

// ------------------------------------------------------------------ filters
function fillSelect(el, items, label=x=>x){
  el.innerHTML = `<option value="">any</option>` + items.map(v=>`<option value="${esc(v)}">${esc(label(v))}</option>`).join("");
}
const uniq = k => [...new Set(R.map(r=>r[C[k]]))];
fillSelect($("fMkt"), Object.keys(D.markets));
fillSelect($("fTf"), uniq("tf").sort((a,b)=>a-b), v=>v+"m");
fillSelect($("fGrp"), D.groups.map((g,i)=>i), i=>D.groups[i]);
fillSelect($("fFam"), Object.keys(D.fams).map(Number).sort((a,b)=>a-b), n=>`${D.fams[n].fid}  ${D.fams[n].name}`);
fillSelect($("fSes"), Object.keys(D.sessions));
fillSelect($("fEnt"), Object.keys(D.text.entry));
fillSelect($("fStp"), Object.keys(D.text.stop));
fillSelect($("fTgt"), Object.keys(D.text.target));

const state = {sort:"score", dir:-1, page:0, per:200, rows:[]};
const searchText = R.map(r => (r[C.id]+" "+r[C.name]+" "+famName(r[C.fam])+" "+r[C.mkt]+" "+r[C.ses]+" "+grpName(r[C.grp])+" "+r[C.tf]+"m").toLowerCase());

function apply(){
  const q = $("q").value.trim().toLowerCase();
  const mk=$("fMkt").value, tf=$("fTf").value, gr=$("fGrp").value, fa=$("fFam").value, se=$("fSes").value,
        en=$("fEnt").value, st=$("fStp").value, tg=$("fTgt").value, mn=+$("fMin").value||0,
        mw=$("fMaxW").value===""?null:+$("fMaxW").value, only=$("fOnly").value;
  const ctrlG = D.groups.indexOf("Control");
  const out = [];
  for(let i=0;i<N;i++){
    const r=R[i];
    if(q && !searchText[i].includes(q)) continue;
    if(mk && r[C.mkt]!==mk) continue;
    if(tf && r[C.tf]!=+tf) continue;
    if(gr!=="" && r[C.grp]!=+gr) continue;
    if(fa && r[C.fam]!=+fa) continue;
    if(se && r[C.ses]!==se) continue;
    if(en && r[C.ent]!==en) continue;
    if(st && r[C.stp]!==st) continue;
    if(tg && r[C.tgt]!==tg) continue;
    if(r[C.trades]<mn) continue;
    if(mw!=null && r[C.pw]>mw) continue;
    const isC = r[C.grp]===ctrlG;
    if(only==="noctrl" && isC) continue;
    if(only==="ctrl" && !isC) continue;
    if(only==="net" && !(r[C.tot]>0)) continue;
    if(only==="allwin" && !(r[C.tot]>0 && (r[C.e3y]||0)>0 && (r[C.e6]||0)>0)) continue;
    if(only==="beat" && !(r[C.edge]>0 && r[C.et]>D.t95 && r[C.trades]>=MIN_T)) continue;
    if(only==="prop" && !(r[C.pp]>=0.5)) continue;
    if(only==="active" && !(r[C.pw]>=1)) continue;
    out.push(i);
  }
  state.rows = out; state.page = 0; sortRows(); render();
}
function sortRows(){
  const col = COLS.find(c=>c.k===state.sort); if(!col || col.nosort) return;
  const i = col.i, d = state.dir;
  state.rows.sort((a,b)=>{
    const x=R[a][i], y=R[b][i];
    if(x==null && y==null) return 0; if(x==null) return 1; if(y==null) return -1;
    if(typeof x==="string") return d*x.localeCompare(y);
    return d*(x-y);
  });
}
function head(){
  $("tbl").querySelector("thead").innerHTML = "<tr>"+COLS.map(c=>{
    const on = state.sort===c.k;
    return `<th class="${c.l?"l":""} ${on?"sorted":""}" data-k="${c.k}" title="${esc(c.tip||"")}">${esc(c.h)}${on?(state.dir<0?" ▼":" ▲"):""}</th>`;
  }).join("")+"</tr>";
}
function pclass(v){ return v==null?"mut": v>=0.5?"p-hi": v>=0.2?"p-mid": v>0?"":"mut"; }
function fullName(r){ return `${r[C.name]} · ${r[C.mkt]} ${r[C.tf]}m ${r[C.ses]} · ${r[C.ent]} entry, ${r[C.stp]} stop, ${r[C.tgt]}`; }
function render(){
  head();
  const s = state.page*state.per, rows = state.rows.slice(s, s+state.per);
  const ctrlG = D.groups.indexOf("Control");
  $("tbl").querySelector("tbody").innerHTML = rows.map((ri,j)=>{
    const r = R[ri];
    return `<tr data-i="${ri}" class="${r[C.grp]===ctrlG?"ctrl":""}">`+COLS.map(c=>{
      const v = c.k==="rank"? s+j+1 : r[c.i];
      let txt = c.f? c.f(v,r) : v;
      let k = c.l? "l ": "";
      if(c.cls) k += c.cls+" ";
      if(c.c) k += cls(v);
      if(c.p) k += pclass(v);
      const title = c.k==="name"? ` title="${esc(fullName(r))}"` : "";
      return `<td class="${k}"${title}>${esc(txt)}</td>`;
    }).join("")+"</tr>";
  }).join("");
  const pages = Math.max(1, Math.ceil(state.rows.length/state.per));
  $("page").textContent = `page ${state.page+1} / ${pages}`;
  $("count").textContent = `${state.rows.length.toLocaleString()} strategies match`;
}
$("tbl").querySelector("thead").addEventListener("click", e=>{
  const th = e.target.closest("th"); if(!th) return;
  const k = th.dataset.k; const col = COLS.find(c=>c.k===k); if(!col || col.nosort) return;
  if(state.sort===k) state.dir*=-1; else { state.sort=k; state.dir = col.l? 1 : -1; }
  sortRows(); state.page=0; render();
});
$("tbl").querySelector("tbody").addEventListener("click", e=>{
  const tr = e.target.closest("tr"); if(tr) openProfile(+tr.dataset.i);
});
$("prev").onclick = ()=>{ if(state.page>0){state.page--; render(); $("tbl").parentElement.scrollTop=0;} };
$("next").onclick = ()=>{ if((state.page+1)*state.per < state.rows.length){state.page++; render(); $("tbl").parentElement.scrollTop=0;} };
["q","fMkt","fTf","fGrp","fFam","fSes","fEnt","fStp","fTgt","fMin","fMaxW","fOnly"].forEach(id=>{
  $(id).addEventListener(id==="q"||id==="fMin"||id==="fMaxW"?"input":"change", apply);
});
$("reset").onclick = ()=>{
  $("q").value=""; ["fMkt","fTf","fGrp","fFam","fSes","fEnt","fStp","fTgt"].forEach(id=>$(id).value="");
  $("fMin").value=30; $("fMaxW").value=""; $("fOnly").value="all"; state.sort="score"; state.dir=-1; apply();
};

// ------------------------------------------------------------------ tabs
document.querySelectorAll(".tab").forEach(b=>b.addEventListener("click", ()=>showTab(b.dataset.tab)));
function showTab(t){
  document.querySelectorAll(".tab").forEach(b=>b.classList.toggle("on", b.dataset.tab===t));
  ["all","fam","dims","lessons","how"].forEach(x=>$("tab-"+x).hidden = x!==t);
  if(t==="fam") renderFamilies(); if(t==="dims") renderDims();
}

// ------------------------------------------------------------------ helpers for roll-ups
function median(a){ const v=a.filter(x=>x!=null).sort((x,y)=>x-y); if(!v.length) return null; const h=v.length>>1; return v.length%2? v[h] : (v[h-1]+v[h])/2; }
function share(a,f){ return a.length? a.filter(f).length/a.length : null; }
function enough(idx){ return idx.filter(i=>R[i][C.trades]>=MIN_T); }

// ------------------------------------------------------------------ families
let famDone=false;
function renderFamilies(){
  if(famDone) return; famDone=true;
  const by = {}; for(let i=0;i<N;i++){ (by[R[i][C.fam]] ||= []).push(i); }
  const rows = Object.keys(D.fams).map(Number).sort((a,b)=>a-b).map(n=>{
    const all = by[n]||[], e = enough(all);
    let best=null; e.forEach(i=>{ if(best==null || R[i][C.score]>R[best][C.score]) best=i; });
    return {n, all, e, best,
      prof: share(e, i=>R[i][C.tot]>0), med: median(e.map(i=>R[i][C.net])), edge: median(e.map(i=>R[i][C.edge])),
      pw: median(all.map(i=>R[i][C.pw])), win: median(e.map(i=>R[i][C.win])), beat: share(e, i=>R[i][C.edge]>0 && R[i][C.et]>D.t95)};
  });
  const t = $("famTbl");
  t.querySelector("thead").innerHTML = `<tr><th class="l">#</th><th class="l">Family</th><th class="l">Group</th><th>Strategies</th><th>Median trades/wk</th><th>Median win %</th><th>% net-profitable</th><th>Median net R/trade</th><th>Median edge vs random</th><th>% beat random</th><th class="l">Best by score</th><th>Score</th></tr>`;
  t.querySelector("tbody").innerHTML = rows.map(x=>{
    const f = D.fams[x.n];
    const legs = f.legs.map(c=>D.legs[c].label).join(" · ") || "coin flip";
    const b = x.best!=null? R[x.best] : null;
    return `<tr data-f="${x.n}" title="${esc(f.thesis)}"><td class="l">${esc(f.fid)}</td><td class="l"><b>${esc(f.name)}</b><div class="mut">${esc(legs)}</div></td><td class="l">${esc(D.groups[f.grp])}</td><td>${x.all.length}</td><td>${num(x.pw,2)}</td><td>${pc(x.win)}</td><td class="${cls(x.prof==null?null:x.prof-0.5)}">${pc(x.prof)}</td><td class="${cls(x.med)}">${sgn(x.med,3,"R")}</td><td class="${cls(x.edge)}">${sgn(x.edge,3,"R")}</td><td>${pc(x.beat,1)}</td><td class="l">${b?esc(b[C.id]+" "+b[C.mkt]+" "+b[C.tf]+"m "+b[C.ses]):"–"}</td><td class="${cls(b?b[C.score]:null)}">${b?sgn(b[C.score],3):"–"}</td></tr>`;
  }).join("");
  t.querySelector("tbody").onclick = e=>{
    const tr = e.target.closest("tr"); if(!tr) return;
    $("reset").onclick(); $("fFam").value = tr.dataset.f; apply(); showTab("all");
  };
}

// ------------------------------------------------------------------ dimensions
let dimsDone=false;
function renderDims(){
  if(dimsDone) return; dimsDone=true;
  const ctrlG = D.groups.indexOf("Control");
  const idx = enough([...Array(N).keys()]);
  $("dimNote").textContent = `Strategies with at least ${MIN_T} trades (${idx.length.toLocaleString()} of ${N.toLocaleString()}). Bars show median net R per trade; "edge" compares gross R with random controls in the same market and exit.`;
  const dims = [
    ["Group", i=>D.groups[R[i][C.grp]]], ["Market", i=>R[i][C.mkt]], ["Timeframe", i=>R[i][C.tf]+"m"],
    ["Session", i=>R[i][C.ses]], ["Entry", i=>R[i][C.ent]], ["Stop", i=>R[i][C.stp]], ["Target / exit", i=>R[i][C.tgt]],
    ["Confluence legs", i=>R[i][C.grp]===ctrlG? "control" : R[i][C.legs]+" legs"],
    ["Extra filter", i=>R[i][C.grp]===ctrlG? "control" : (R[i][C.xtra]? D.legs[R[i][C.xtra]].label : "none")],
  ];
  const html = dims.map(([title, key])=>{
    const by = {}; idx.forEach(i=>{ (by[key(i)] ||= []).push(i); });
    const rows = Object.entries(by).map(([k,a])=>({k, a, med: median(a.map(i=>R[i][C.net])), edge: median(a.map(i=>R[i][C.edge])),
      prof: share(a,i=>R[i][C.tot]>0), p6: share(a.filter(i=>R[i][C.n6]>0), i=>R[i][C.e6]>0), cost: median(a.map(i=>R[i][C.cost])), pw: median(a.map(i=>R[i][C.pw]))}));
    rows.sort((x,y)=>(y.med??-9)-(x.med??-9));
    const mx = Math.max(0.05, ...rows.map(r=>Math.abs(r.med||0)));
    return `<div class="card"><h3>${esc(title)}</h3><table class="mini"><thead><tr><th class="l">value</th><th>n</th><th>% profitable</th><th class="l">median net R/trade</th><th>edge</th><th>% +6M</th><th>cost R</th><th>trades/wk</th></tr></thead><tbody>`+
      rows.map(r=>{ const w = Math.round(60*Math.abs(r.med||0)/mx);
        return `<tr><td class="l">${esc(r.k)}</td><td>${r.a.length}</td><td>${pc(r.prof)}</td><td class="l"><span class="bar" style="width:${w}px;background:${(r.med||0)>=0?"var(--pos2)":"var(--neg2)"}"></span> <span class="${cls(r.med)}">${sgn(r.med,3)}</span></td><td class="${cls(r.edge)}">${sgn(r.edge,3)}</td><td>${pc(r.p6)}</td><td>${num(r.cost,3)}</td><td>${num(r.pw,2)}</td></tr>`;}).join("")+
      `</tbody></table></div>`;
  }).join("");
  $("dims").innerHTML = html;
}

// ------------------------------------------------------------------ lessons & how
$("lessons").innerHTML = D.lessons.map(l=>`<div class="card ${l.tone}"><h3>${esc(l.title)}</h3><p>${esc(l.body)}</p></div>`).join("");
(function how(){
  const w=D.weights, pr=D.prop, q=(D.meta.quality||{});
  const mk = Object.entries(D.markets).map(([k,v])=>{
    const c=q[k]||{}; const chk = c.ret_corr_5m!=null? `${c.ret_corr_5m.toFixed(3)} vs ${esc(c.yahoo)} (${c.overlap_bars} bars)` : (c.error? esc(c.error): "–");
    return `<tr><td><b>${k}</b></td><td>${esc(v.name)}</td><td>${esc(v.feed)}</td><td>${esc(v.cost)}</td><td>${chk}</td></tr>`;}).join("");
  const ses = Object.entries(D.sessions).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${tdm(v[0])} – ${tdm(v[1])}</td><td>${tdm(v[2])}</td></tr>`).join("");
  $("how").innerHTML = `
  <h2>What this is</h2>
  <p>${N.toLocaleString()} rule-based, intraday strategies built from <b>confluence</b>: every strategy needs a bias (trend or regime), a location (a level, zone, sweep or breakout) and a trigger (the candle that says "now"), sometimes with one extra filter. Each was backtested on 8 years of 1-minute data (${esc(D.meta.start)} → ${esc(D.meta.end)}) with realistic costs, and nothing was optimised: every variant you see was fixed before it was tested, and every one is shown, losers included.</p>
  <h2>Columns</h2>
  <table>
  <tr><td><b>Trades / Per week</b></td><td>trades over the 8 years, and per calendar week</td></tr>
  <tr><td><b>Win %</b></td><td>share of trades with positive net R</td></tr>
  <tr><td><b>Avg RR</b></td><td>average winning trade ÷ average losing trade (net R)</td></tr>
  <tr><td><b>Net / Gross R/trade</b></td><td>average result per trade in R (1R = the amount risked), after / before costs</td></tr>
  <tr><td><b>Total net R, $ at $250 risk</b></td><td>sum of net R over 8 years; × $${D.risk} assumes every trade risks $${D.risk} at its stop</td></tr>
  <tr><td><b>Max DD (R)</b></td><td>largest peak-to-trough fall of the cumulative net R curve</td></tr>
  <tr><td><b>Cost-in-R</b></td><td>average round-trip cost per trade (commission + spread + slippage) as a fraction of the risk; tight stops make this large</td></tr>
  <tr><td><b>Last 12M net R</b></td><td>net R in the last 12 months (trades in brackets)</td></tr>
  <tr><td><b>3Y / Last 6M net R/trade</b></td><td>net R per trade over the last 3 years / 6 months (trades in brackets)</td></tr>
  <tr><td><b>Score</b></td><td>${w["8y"]} × E(8y) + ${w["3y"]} × E(3y) + ${w["6m"]} × E(6m), where E = total net R in the window ÷ (trades in the window + ${D.shrink}), i.e. net R/trade shrunk toward zero when there are few trades. The table hides strategies with fewer than 30 trades by default (Min trades). The last 6 months weigh a little more than the last 3 years, both more than the full 8.</td></tr>
  <tr><td><b>Avg $/day, $/day range</b></td><td>net dollars per trading day at $${D.risk} risk (averaged over every day, traded or not) and the 10th–90th percentile of daily P&amp;L on days it traded</td></tr>
  <tr><td><b>Years +</b></td><td>calendar years with positive net R out of the years the strategy traded — a quick robustness read</td></tr>
  <tr><td><b>Edge vs random</b></td><td>gross R/trade minus the median gross R/trade of the random controls in the same market with the same exit style. Exit style alone shifts results (holding index futures to the close earned money even with coin-flip entries), so this is the fairer yardstick</td></tr>
  <tr><td><b>Edge t</b></td><td>edge ÷ its standard error. Random controls measured the same way have a 95th percentile of ${D.t95.toFixed(2)} — the luck bar; below it, chance explains the edge as well as skill does</td></tr>
  <tr><td><b>t-stat</b></td><td>mean ÷ standard error of net R per trade (is it profitable after costs, not just better than random)</td></tr>
  <tr><td><b>P(pass eval)</b></td><td>Monte Carlo: ${D.meta.mc||2000} runs of a 50K-style evaluation — reach +$${pr.target.toLocaleString()} before a $${pr.mll.toLocaleString()} trailing (end-of-day) drawdown, within ${pr.days} trading days, drawing 5-day blocks of this strategy's daily P&amp;L with the same recency weights as the score</td></tr>
  <tr><td><b>P(payout)</b></td><td>pass, then in a fresh funded account with the same $${pr.mll.toLocaleString()} trailing drawdown reach ${pr.wins} winning days of $${pr.winusd}+ and $${pr.payout.toLocaleString()} profit within ${pr.fdays} days</td></tr>
  </table>
  <h2>Markets, data and costs</h2>
  <p>1-minute history comes from histdata.com (8-year backbone), spliced with Dukascopy up to the last session; the splice is checked minute-by-minute (correlation ≥ 0.97). MNQ and MES are traded on the index CFD feed that tracks the same underlying, continuous with no roll gaps, and charged futures commissions. The last column checks each proxy against the real contract on Yahoo (5-minute returns, last 60 days). massive.com is supported when <code>MASSIVE_API_KEY</code> is set; TradingView's ~1 month of futures bars was used to spot-check MNQ/MES.</p>
  <table><tr><th>market</th><th>instrument</th><th>feed</th><th>round-trip cost</th><th>proxy check</th></tr>${mk}</table>
  ${Object.values(q._tradingview_spotcheck||{}).map(t=>`<p>TradingView spot check: <b>${esc(t.tradingview)}</b> vs ${esc(t.feed)} — 5-minute return correlation ${Number(t.ret_corr_5m).toFixed(4)} over ${t.bars} bars (${esc(t.window)}).</p>`).join("")}
  <h2>Sessions (New York time)</h2>
  <table><tr><th>session</th><th>entries</th><th>flat at</th></tr>${ses}</table>
  <h2>How trades are simulated</h2>
  <ul>
  <li>Signals are read on the bar's close; orders work from the next bar. Stops, targets and trailing stops are walked through the underlying 1-minute bars, so a 60-minute strategy knows whether its stop or its target was hit first. If both land in the same minute, the stop is assumed first.</li>
  <li>Entries: market (next open), stop (1 tick through the signal bar, valid 3 bars), limit (signal-bar midpoint, valid 3 bars). Stops are never tighter than 0.3 ATR.</li>
  <li>One position at a time, at most 4 trades a day, always flat at the session exit. VWAP is range-weighted because the CFD feeds carry no reliable volume.</li>
  </ul>
  <h2>Read the leaderboard with the Lessons tab open</h2>
  <p>Out of ${N.toLocaleString()} tests, some will look excellent by chance. Compare anything you like with the random controls (filter "random controls only"), prefer strategies profitable in all three windows whose edge t clears the luck bar of ${D.t95.toFixed(2)}, and check the blind test in Lessons before trusting the score. A backtest is a hypothesis, not a forecast.</p>`;
})();
function tdm(x){ const t=(x+18*60)%1440; return String(Math.floor(t/60)).padStart(2,"0")+":"+String(t%60).padStart(2,"0"); }

// ------------------------------------------------------------------ profile
function openProfile(i){
  const r=R[i], p=P[i], f=D.fams[r[C.fam]], isC = D.groups[r[C.grp]]==="Control";
  const rules = [];
  if(isC) rules.push("enter at random (about one signal every two sessions), long or short on a coin flip");
  else p.lg.forEach(c=>rules.push(`<b>${esc(D.legs[c].kind)}</b> — ${esc(D.legs[c].text)}`));
  rules.push(`<b>entry</b> — ${esc(D.text.entry[r[C.ent]])}`);
  rules.push(`<b>stop</b> — ${esc(D.text.stop[r[C.stp]])} (never tighter than 0.3 ATR)`);
  rules.push(`<b>target</b> — ${esc(D.text.target[r[C.tgt]])}`);
  const sv = D.sessions[r[C.ses]];
  rules.push(`<b>session</b> — ${esc(r[C.ses])}: entries ${tdm(sv[0])}–${tdm(sv[1])} ET, flat at ${tdm(sv[2])} ET; max 4 trades a day; shorts mirror the long rules`);
  const w=D.weights, sh=D.shrink;
  const e8 = r[C.tot]/(r[C.trades]+sh), e3 = (p.r3||0)/(r[C.n3y]+sh), e6=(p.r6||0)/(r[C.n6]+sh);
  const win = [["8 years", r[C.trades], r[C.net], r[C.tot]], ["last 3 years", r[C.n3y], r[C.e3y], p.r3], ["last 12 months", r[C.n12], r[C.n12]? r[C.r12]/r[C.n12]: null, r[C.r12]], ["last 6 months", r[C.n6], r[C.e6], p.r6]];
  const yrs = Object.entries(p.yrs||{});
  const ex = p.ex||[0,0,0,0], side=p.side||[0,0,0,0];
  $("sheet").innerHTML = `
   <button class="close" id="cls">close ✕</button>
   <h2>${esc(r[C.id])} · ${esc(r[C.name])}</h2>
   <div class="sub">${esc(fullName(r))}</div>
   <div><span class="chip ${isC?"ctrl":""}">${esc(D.groups[r[C.grp]])}</span><span class="chip">${esc(f.name)}</span><span class="chip">${esc(r[C.mkt])} · ${esc(D.markets[r[C.mkt]].name)}</span><span class="chip">${r[C.tf]}m</span><span class="chip">${esc(r[C.ses])}</span><span class="chip">${r[C.legs]} confluence legs</span></div>
   <p style="color:#c3d1e6;margin:6px 0 12px">${esc(f.thesis)}</p>
   <div class="grid2">
     <div class="box"><h4>Rules (long side)</h4><ol class="rules">${rules.map(x=>`<li>${x}</li>`).join("")}</ol></div>
     <div class="box"><h4>Headline</h4><div class="kv">
       <div>trades · per week</div><div>${r[C.trades].toLocaleString()} · ${num(r[C.pw],2)}</div>
       <div>win % · avg RR · profit factor</div><div>${pc(r[C.win])} · ${num(r[C.rr],2)} · ${num(r[C.pf],2)}</div>
       <div>net · gross R/trade</div><div><span class="${cls(r[C.net])}">${sgn(r[C.net],3,"R")}</span> · <span class="${cls(r[C.gross])}">${sgn(r[C.gross],3,"R")}</span></div>
       <div>total net R · $ at $250</div><div><span class="${cls(r[C.tot])}">${num(r[C.tot],1)}R</span> · <span class="${cls(r[C.usd])}">${usd(r[C.usd])}</span></div>
       <div>max drawdown · worst losing streak</div><div>${num(r[C.dd],1)}R · ${p.stk} trades</div>
       <div>best · worst trade</div><div>${sgn(p.best,2,"R")} · ${sgn(p.worst,2,"R")}</div>
       <div>cost per trade</div><div>${num(r[C.cost],3)}R</div>
       <div>edge vs random · edge t</div><div><span class="${cls(r[C.edge])}">${sgn(r[C.edge],3,"R")}</span> · <span class="${r[C.et]>D.t95?"pos":"mut"}">${num(r[C.et],2)}</span> (luck bar ${D.t95.toFixed(2)})</div>
       <div>t-stat of net R</div><div>${num(r[C.t],2)}</div>
     </div></div>
   </div>
   <div class="box" style="margin-top:14px"><h4>Equity, cumulative net R by month — shaded: last 3 years and last 6 months (the weighted windows)</h4>${equity(p.eq)}</div>
   <div class="grid3" style="margin-top:14px">
     <div class="box"><h4>Windows &amp; score</h4><table class="mini"><tr><th class="l">window</th><th>trades</th><th>R/trade</th><th>total R</th></tr>${win.map(x=>`<tr><td class="l">${x[0]}</td><td>${x[1]}</td><td class="${cls(x[2])}">${sgn(x[2],3)}</td><td class="${cls(x[3])}">${x[3]==null?"–":num(x[3],1)}</td></tr>`).join("")}</table>
       <div class="kv" style="margin-top:8px"><div>${w["8y"]} × E(8y)</div><div>${sgn(w["8y"]*e8,4)}</div><div>${w["3y"]} × E(3y)</div><div>${sgn(w["3y"]*e3,4)}</div><div>${w["6m"]} × E(6m)</div><div>${sgn(w["6m"]*e6,4)}</div><div><b>score</b></div><div class="${cls(r[C.score])}"><b>${sgn(r[C.score],4)}</b></div></div></div>
     <div class="box"><h4>Profit per day at $250 risk</h4><div class="kv">
       <div>avg $/day · 8y</div><div class="${cls(r[C.uday])}">${usdS(r[C.uday])}</div>
       <div>avg $/day · 3y</div><div class="${cls(p.u3)}">${usdS(p.u3)}</div>
       <div>avg $/day · 6m</div><div class="${cls(p.u6)}">${usdS(p.u6)}</div>
       <div>days traded · green</div><div>${(p.ad||0).toLocaleString()} · ${pc(r[C.green])}</div>
       <div>range P10 … P90</div><div>${usdS(r[C.dp10])} … ${usdS(r[C.dp90])}</div>
       <div>worst · best day</div><div>${usdS(p.dmin)} · ${usdS(p.dmax)}</div></div>
       ${(p.dq||[]).length?`<table class="mini" style="margin-top:8px"><tr><th>P5</th><th>P25</th><th>median</th><th>P75</th><th>P95</th></tr><tr>${[0,2,3,4,6].map(k=>`<td class="${cls(p.dq[k])}">${usdS(p.dq[k])}</td>`).join("")}</tr></table>`:""}${dayBar(p)}</div>
     <div class="box"><h4>Prop evaluation (Monte Carlo)</h4><div class="kv">
       <div>P(pass eval)</div><div class="${pclass(r[C.pp])}">${pc(r[C.pp],1)}</div>
       <div>P(pass and first payout)</div><div class="${pclass(r[C.ppay])}">${pc(r[C.ppay],1)}</div>
       <div>median days to pass</div><div>${p.pd==null?"–":num(p.pd,0)}</div>
       <div>target · trailing DD</div><div>+$${D.prop.target.toLocaleString()} · $${D.prop.mll.toLocaleString()}</div></div>
       <h4 style="margin-top:12px">Exits · sides</h4><div class="kv">
       <div>stop · target · trail · time</div><div>${ex.join(" · ")}</div>
       <div>longs (net R)</div><div>${side[0]} <span class="${cls(side[1])}">(${sgn(side[1],1)})</span></div>
       <div>shorts (net R)</div><div>${side[2]} <span class="${cls(side[3])}">(${sgn(side[3],1)})</span></div></div></div>
   </div>
   <div class="grid2" style="margin-top:14px">
     <div class="box"><h4>By calendar year (trades · net R)</h4>${yearBars(yrs)}</div>
     <div class="box"><h4>Last trades</h4><table class="mini"><tr><th class="l">day</th><th class="l">side</th><th>net R</th><th class="l">exit</th></tr>${(p.last||[]).slice().reverse().map(t=>`<tr><td class="l">${t[0]}</td><td class="l">${t[1]>0?"long":"short"}</td><td class="${cls(t[2])}">${sgn(t[2],2)}</td><td class="l">${["stop","target","trail","time"][t[3]]}</td></tr>`).join("")||"<tr><td class='l'>no trades</td></tr>"}</table></div>
   </div>`;
  $("modal").hidden=false; $("cls").onclick=closeP;
}
function closeP(){ $("modal").hidden=true; }
$("modal").addEventListener("click", e=>{ if(e.target.id==="modal") closeP(); });
document.addEventListener("keydown", e=>{ if(e.key==="Escape") closeP(); });

function equity(eq){
  if(!eq || !eq.length) return "<p class='mut'>no trades</p>";
  const W=1060,H=220,pl=44,pr=10,pt=10,pb=22, n=eq.length;
  const mn=Math.min(0,...eq), mx=Math.max(0,...eq), rng=(mx-mn)||1;
  const x=i=>pl+(W-pl-pr)*i/Math.max(n-1,1), y=v=>pt+(H-pt-pb)*(1-(v-mn)/rng);
  const pts = eq.map((v,i)=>`${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const i3 = Math.max(0,n-36), i6=Math.max(0,n-6);
  const last = eq[n-1];
  let ticks=""; for(let k=0;k<n;k+=12){ ticks+=`<text x="${x(k)}" y="${H-6}" text-anchor="middle">${esc((D.months[k]||"").slice(0,4))}</text>`; }
  const yt = [mn, (mn+mx)/2, mx].map(v=>`<text x="${pl-6}" y="${y(v)+3}" text-anchor="end">${v.toFixed(0)}R</text>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="equity curve">
   <rect x="${x(i3)}" y="${pt}" width="${x(n-1)-x(i3)}" height="${H-pt-pb}" fill="#2f80ed" opacity=".08"/>
   <rect x="${x(i6)}" y="${pt}" width="${x(n-1)-x(i6)}" height="${H-pt-pb}" fill="#2f80ed" opacity=".14"/>
   <line x1="${pl}" x2="${W-pr}" y1="${y(0)}" y2="${y(0)}" stroke="#3a5579" stroke-dasharray="3 3"/>
   <polyline points="${pts}" fill="none" stroke="${last>=0?"#35d08a":"#ff6b7d"}" stroke-width="1.8"/>${ticks}${yt}</svg>`;
}
function yearBars(yrs){
  if(!yrs.length) return "";
  const W=500,H=150,pb=30,pt=14, mx=Math.max(1,...yrs.map(y=>Math.abs(y[1][1]))), bw=(W-20)/yrs.length;
  const z=pt+(H-pt-pb)/2, s=(H-pt-pb)/2/mx;
  return `<svg viewBox="0 0 ${W} ${H}" width="100%">`+yrs.map((y,i)=>{ const v=y[1][1], h=Math.abs(v)*s, xx=10+i*bw+bw*.15;
    return `<rect x="${xx}" y="${v>=0?z-h:z}" width="${bw*.7}" height="${Math.max(h,.5)}" fill="${v>=0?"#1f9a63":"#c2475a"}"/><text x="${xx+bw*.35}" y="${H-16}" text-anchor="middle">${y[0]}</text><text x="${xx+bw*.35}" y="${H-4}" text-anchor="middle">${y[1][0]}·${v.toFixed(0)}R</text>`;}).join("")+`<line x1="10" x2="${W-10}" y1="${z}" y2="${z}" stroke="#3a5579"/></svg>`;
}
function dayBar(p){
  const q=p.dq; if(!q||!q.length) return "";
  const lo=Math.min(q[0],0), hi=Math.max(q[6],0), W=300,H=34, X=v=>10+(W-20)*(v-lo)/((hi-lo)||1);
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" style="margin-top:8px"><line x1="${X(q[0])}" x2="${X(q[6])}" y1="14" y2="14" stroke="#5d7392"/><rect x="${X(q[2])}" y="6" width="${Math.max(X(q[4])-X(q[2]),1)}" height="16" fill="#2f80ed" opacity=".45"/><line x1="${X(q[3])}" x2="${X(q[3])}" y1="4" y2="24" stroke="#fff"/><line x1="${X(0)}" x2="${X(0)}" y1="2" y2="26" stroke="#ff6b7d" stroke-dasharray="2 2"/><text x="${X(q[0])}" y="32" text-anchor="middle">P5</text><text x="${X(q[6])}" y="32" text-anchor="middle">P95</text></svg>`;
}

apply();
})();
</script>
</body>
</html>
"""
