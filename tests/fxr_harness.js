// Runs an FXR Script against exported bars the way FX Replay runs it, and fails where FX Replay would.
//
// A model of FX Replay's compiler and chart runtime, taken from how app.fxreplay.com behaves:
//  * the compiler rejects `new X(...)` and browser calls such as setTimeout or fetch
//    ("There are errors in the script");
//  * everything outside init and onTick runs again on every bar. Only top-level variables that start
//    as a literal, an {object} or a non-empty [array] are kept between bars, as state.NAME, and every
//    NAME inside onTick is renamed state.NAME (an empty [] becomes a bar-indexed series instead);
//  * an onTick helper declared with const/let that uses only globals, state and other helpers is moved
//    out of onTick, where the renamed state is out of reach, so helpers have to be `var`;
//  * the input ids, index, plotIndex and sessionId become constants inside onTick, and `inputs.x` is
//    replaced by the constant;
//  * the live bar runs once per tick: before its first run the state is snapshotted (arrays copied,
//    objects shallow-copied), before each repeat the snapshot is put back by reference, and the bar's
//    drawings are wiped every time. The last LIVE bars are replayed that way, TICKS runs each.
//
// usage: node tests/fxr_harness.js script.js bars.json out.json
const fs = require('fs');
const [script, barsFile, outFile] = process.argv.slice(2);
const LIVE = 2000, TICKS = 3;
const src = fs.readFileSync(script, 'utf8');
const reject = (m) => { console.error('FX Replay would reject this script: ' + m); process.exit(3); };

// ------------------------------------------------------------------ source scanning
// The code with comments and string contents blanked (same length), so brackets and words can be
// found without being fooled by text.
const mask = (s) => {
  let out = '', i = 0;
  while (i < s.length) {
    const c = s[i], d = s[i + 1];
    if (c === '/' && d === '/') { while (i < s.length && s[i] !== '\n') { out += ' '; i++; } continue; }
    if (c === '/' && d === '*') {
      while (i < s.length && !(s[i] === '*' && s[i + 1] === '/')) { out += s[i] === '\n' ? '\n' : ' '; i++; }
      out += '  '; i += 2; continue;
    }
    if (c === "'" || c === '"' || c === '`') {
      out += c; i++;
      while (i < s.length && s[i] !== c) {
        if (s[i] === '\\') { out += ' '; i++; }
        out += s[i] === '\n' ? '\n' : ' '; i++;
      }
      out += c; i++; continue;
    }
    out += c; i++;
  }
  return out;
};
// [start, end) of each statement at bracket depth 0 of masked code m between from and to
const statements = (m, from, to) => {
  const out = [];
  let depth = 0, start = from;
  for (let i = from; i < to; i++) {
    const c = m[i];
    if (c === '{' || c === '(' || c === '[') depth++;
    else if (c === '}' || c === ')' || c === ']') depth--;
    else if (c === ';' && depth === 0) { if (m.slice(start, i).trim()) out.push([start, i]); start = i + 1; }
    // a block statement (if / for / try) ends at its closing brace
    if (c === '}' && depth === 0 && !/^\s*[;,).]/.test(m.slice(i + 1, i + 3)) && /^\s*(if|for|while|try|do|switch)\b/.test(m.slice(start, i))) {
      out.push([start, i + 1]); start = i + 1;
    }
  }
  if (m.slice(start, to).trim()) out.push([start, to]);
  return out;
};
const M = mask(src);

// ------------------------------------------------------------------ what FX Replay's compiler rejects
let bad = M.match(/\bnew\s+[A-Za-z_$][\w$]*/);
if (bad) reject(`Use of "${bad[0]}" is not allowed`);
bad = M.match(/\b(setTimeout|setInterval|requestAnimationFrame|eval|document|navigator|fetch)\b/);
if (bad) reject(`Forbidden API call: ${bad[1]}`);
bad = M.match(/\bDate\b|\bMath\.random\b/);        // our rule: the replay must not depend on the clock
if (bad) reject(`${bad[0]}: results would depend on when the script runs`);

// ------------------------------------------------------------------ top level: init, onTick and state
const IDENT = /^[A-Za-z_$][\w$]*$/;
const state = {};                          // name -> initialiser source
let tickStart = -1, tickEnd = -1, initBody = '';
for (const [a, b] of statements(M, 0, M.length)) {
  const m = M.slice(a, b).trim(), s = src.slice(a, b).trim();
  if (/^init\s*=/.test(m)) { initBody = s; continue; }
  const t = M.slice(a, b).match(/onTick\s*=\s*\([^)]*\)\s*=>\s*\{/);
  if (t && /^onTick\s*=/.test(m)) {
    tickStart = a + t.index + t[0].length;
    tickEnd = M.lastIndexOf('}', b);
    continue;
  }
  const d = m.match(/^(const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*([\s\S]*)$/);
  if (!d) reject(`top-level code outside init and onTick runs again on every bar: ${s.slice(0, 60)}`);
  const [, , name, initM] = d;
  const init = s.slice(s.length - initM.length);
  if (statements(initM.replace(/,/g, ';'), 0, initM.length).length > 1) reject(`${name}: declare one state variable per statement`);
  if (/^\[\s*\]$/.test(initM)) reject(`${name} = []: an empty array becomes a bar-indexed series; start it with one item`);
  const kept = /^[{[]/.test(initM) || /^['"`]/.test(initM) || /^\d|^\.\d/.test(initM) ||
    /^(true|false|null|NaN|Infinity|-Infinity|-NaN)$/.test(initM);
  if (!kept) reject(`${name} = ${init.slice(0, 30)}: FX Replay only keeps literals, objects and arrays between bars`);
  state[name] = init;
}
if (tickStart < 0) reject('no onTick');

// ------------------------------------------------------------------ onTick
const inputIds = [...initBody.matchAll(/input\.(?:float|int|bool|str|color|source|session|timeframe|textarea|time)\(\s*(['"])[^'"]*\1\s*,[^,]*,\s*(['"])([^'"]+)\2/g)].map((x) => x[3]);
let body = src.slice(tickStart, tickEnd);
const bodyM = M.slice(tickStart, tickEnd);
for (const [a, b] of statements(bodyM, 0, bodyM.length)) {
  const m = bodyM.slice(a, b).trim();
  const f = m.match(/^(const|let)\s+([A-Za-z_$][\w$]*)\s*=\s*(function\b|async\b|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)/);
  if (f) reject(`helper ${f[2]} is declared with ${f[1]}: FX Replay can move it out of onTick, away from the state; use var`);
  const g = m.match(/^function\s+([A-Za-z_$][\w$]*)/);
  if (g) reject(`function ${g[1]}: FX Replay can move it out of onTick, away from the state; use var ${g[1]} = function`);
}
// FX Replay's rewrite: inputs.x -> the input constant, then every state name -> state.NAME
body = body.replace(/\binputs\.([A-Za-z_$][\w$]*)/g, (x, id) => (inputIds.includes(id) ? id : 'undefined'));
for (const name of Object.keys(state)) body = body.replace(new RegExp(`\\b${name.replace(/\$/g, '\\$')}\\b`, 'g'), `state.${name}`);
// bar accessors, drawings and plots, which FX Replay replaces with its own series and drawing calls
body = body.replace(/(?<![.\w$])(time|high|low|openC|closeC|volume)\s*\(/g, '__bar.$1(')
  .replace(/(?<![.\w$])(trendLine|newPoint)\s*\(/g, '__drawings.$1(')
  .replace(/(?<![.\w$])plot\.(\w+)\s*\(/g, '__plot.$1(');
const prelude = [
  'let timeSeries, highSeries, lowSeries, openCSeries, closeCSeries;',
  ...inputIds.map((id, i) => `const ${id} = input(${i});`),
  'const plotIndex = context.symbol.index;', 'const index = plotIndex;', 'const sessionId = "s1";',
].join('\n');
let he;
try {
  he = new Function('context', 'input', 'state', '_moment', '_', 'ta', 'length', 'color', 'console', '__drawings',
    'iconList', 'StickersList', 'PineJS', '__bar', '__plot', `"use strict";\n${prelude}\n${body}`);
} catch (e) { reject(String(e)); }

// ------------------------------------------------------------------ run
const bars = JSON.parse(fs.readFileSync(barsFile));
const N = bars.t.length;
let W = 0;
const at = (arr, n) => (W - n >= 0 ? arr[W - n] : NaN);
const __bar = { time: (n) => at(bars.t, n), high: (n) => at(bars.h, n), low: (n) => at(bars.l, n),
  openC: (n) => at(bars.o, n), closeC: (n) => at(bars.c, n), volume: () => NaN };
const inputVals = inputIds.map((id) => {
  const m = initBody.match(new RegExp(`input\\.\\w+\\(\\s*(['"])[^'"]*\\1\\s*,\\s*([^,]+),\\s*(['"])${id}\\3`));
  return m ? JSON.parse(m[2].replace(/'/g, '"')) : undefined;
});
const COLOR_KEYS = ['linecolor', 'color', 'backgroundColor', 'borderColor'];
const colour = Object.freeze({ white: { base: 'white' }, red: { base: 'red' }, green: { base: 'green' }, rgba: (r, g, b, a) => ({ r, g, b, a }) });
const drawn = new Map();                     // candle index -> drawings made while it was the current bar
const __drawings = {
  newPoint: (time, price) => ({ time, price }),
  trendLine: (p1, p2, st, text) => {
    for (const key of COLOR_KEYS) {
      if (st && key in st && typeof st[key] !== 'object') throw new Error(`drawing style ${key} must be a color value, got ${st[key]}`);
    }
    if (!p1 || !p2 || !Number.isFinite(p1.time) || !Number.isFinite(p2.price)) throw new Error('bad point');
    if (!drawn.has(W)) drawn.set(W, []);
    drawn.get(W).push([p1, p2, st, text]);
    return 'l' + W;
  },
};
const seriesStyle = {};
let plotted = [];
const __plot = {
  // a shapes series has one fixed style: the same id always comes with the same text, colours and shape
  shapes: (title, value, text, col, textCol, type, loc, size, offset, transp, id) => {
    const key = id || title, style = JSON.stringify([title, text, col, textCol, type, loc, size]);
    if (seriesStyle[key] !== undefined && seriesStyle[key] !== style) throw new Error('shapes series ' + key + ' changed style');
    seriesStyle[key] = style;
    plotted.push([key, value, offset]);
  },
};
const logs = [];
const cons = { log: (...a) => logs.push(a.join(' ')), error: (...a) => logs.push(a.join(' ')), warn: () => {} };
const context = { symbol: { index: 0 } };
const P = {};
new Function('state', '"use strict";\n' + Object.entries(state).map(([k, v]) => `state.${k} = ${v};`).join('\n'))(P);
const snapshot = () => {
  const o = {};
  for (const k in P) { const x = P[k]; o[k] = x && typeof x === 'object' ? (Array.isArray(x) ? x.slice() : { ...x }) : x; }
  return o;
};
const restore = (B) => { for (const k in P) if (!(k in B)) delete P[k]; for (const k in B) P[k] = B[k]; };
let lastW = null, B = null, unstable = 0, shapes = 0;
const t0 = Date.now();
for (W = 0; W < N; W++) {
  context.symbol.index = W;
  const live = W >= N - LIVE;
  let first = null;
  for (let tick = 0; tick < (live ? TICKS : 1); tick++) {
    if (W === lastW) { if (B) restore(B); } else { lastW = W; B = live ? snapshot() : null; }
    drawn.delete(W);
    plotted = [];
    he(context, (i) => inputVals[i], P, null, null, null, W + 1, colour, cons, __drawings, {}, {}, null, __bar, __plot);
    const out = JSON.stringify([plotted, drawn.get(W) || []]);
    if (first === null) first = out; else if (out !== first) unstable++;
  }
  shapes += plotted.length;
}
const tr = P.S_TRADES.filter((x) => x.t0 > 0);
const errors = logs.filter((x) => x.includes('SCRIPT ERROR'));
if (errors.length) { console.error('script errors: ' + errors.slice(0, 3).join(' | ')); process.exit(2); }
if (unstable) { console.error(`${unstable} live bars drew something different on a repeated tick`); process.exit(2); }
fs.writeFileSync(outFile, JSON.stringify(tr));
const lines = [...drawn.values()].reduce((s, x) => s + x.length, 0);
console.log(`${script.split('/').pop()}: ${tr.length} trades, ${tr.reduce((s, x) => s + x.r, 0).toFixed(1)}R, ` +
  `${(Date.now() - t0) / 1000}s, ${Object.keys(state).length} state variables, ${shapes} markers, ${lines} lines on chart`);
