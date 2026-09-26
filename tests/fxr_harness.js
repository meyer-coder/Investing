// Runs an FXR Script against exported bars with a mock of the FX Replay API.
const fs = require('fs'), vm = require('vm');
const [script, barsFile, outFile] = process.argv.slice(2);
const bars = JSON.parse(fs.readFileSync(barsFile));
const N = bars.t.length;
let k = 0;                                   // current (forming) bar
const at = (arr, n) => (k - n >= 0 ? arr[k - n] : NaN);
const inputs = {};
const drawings = { lines: 0, texts: 0, shapes: 0, deleted: 0 };
const errors = [];
const live = new Set();
const seriesStyle = {};
const ctx = {
  console: { log: console.log, error: (m) => errors.push(String(m)) }, Math, Date, isNaN, Array, Number, JSON, String,
  indicator: () => ({}),
  input: {
    float: (t, v, id) => { inputs[id] = v; return { id }; },
    int: (t, v, id) => { inputs[id] = v; return { id }; },
    bool: (t, v, id) => { inputs[id] = v; return { id }; },
  },
  high: (n) => at(bars.h, n), low: (n) => at(bars.l, n), openC: (n) => at(bars.o, n), closeC: (n) => at(bars.c, n),
  time: (n) => at(bars.t, n),
  color: { white: '#fff', rgba: (r, g, b, a) => `rgba(${r},${g},${b},${a})` },
  plot: {
    // a shapes series keeps one style: the same id must always come with the same text, colours and shape
    shapes: (title, value, text, col, textCol, type, loc, size, offset, transp, id) => {
      const key = id || title, style = JSON.stringify([title, text, col, textCol, type, loc, size]);
      if (seriesStyle[key] !== undefined && seriesStyle[key] !== style) throw new Error('shapes series ' + key + ' changed style');
      seriesStyle[key] = style;
      drawings.shapes++;
    },
  },
  trendLine: (p1, p2) => { if (!p1 || !p2 || isNaN(p1.time) || isNaN(p2.price)) throw new Error('bad point'); drawings.lines++; live.add('l' + drawings.lines); return 'l' + drawings.lines; },
  text: (t, p, st, v) => { if (typeof v !== 'string') throw new Error('text value'); drawings.texts++; live.add('t' + drawings.texts); return 't' + drawings.texts; },
  deleteDrawingById: (id) => { if (!live.delete(id)) throw new Error('unknown drawing ' + id); drawings.deleted++; },
  newPoint: (time, price) => ({ time, price }),
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(script, 'utf8'), ctx);
ctx.init();
const t0 = Date.now();
for (k = 0; k < N; k++) {
  ctx.index = k;
  // several ticks per bar, like a live replay
  ctx.onTick(k + 1, null, undefined, null, inputs);
  ctx.onTick(k + 1, null, undefined, null, inputs);
}
const tr = ctx.trades;
if (errors.length) { console.error('script errors: ' + errors.slice(0, 3).join(' | ')); process.exit(2); }
fs.writeFileSync(outFile, JSON.stringify(tr));
console.log(`${script.split('/').pop()}: ${tr.length} trades, ${tr.reduce((s, x) => s + x.r, 0).toFixed(1)}R, ` +
  `${(Date.now() - t0) / 1000}s, drawings ${JSON.stringify(drawings)}, on chart ${live.size}`);
