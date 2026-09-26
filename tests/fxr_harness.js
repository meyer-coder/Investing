// Runs an FXR Script against exported bars with a mock of the FX Replay API.
const fs = require('fs'), vm = require('vm');
const [script, barsFile, outFile] = process.argv.slice(2);
const bars = JSON.parse(fs.readFileSync(barsFile));
const N = bars.t.length;
let k = 0;                                   // current (forming) bar
const at = (arr, n) => (k - n >= 0 ? arr[k - n] : NaN);
const inputs = {};
const drawings = { lines: 0, texts: 0, shapes: 0 };
const ctx = {
  console, Math, Date, isNaN, Array, Number, JSON,
  indicator: () => ({}),
  input: {
    float: (t, v, id) => { inputs[id] = v; return { id }; },
    int: (t, v, id) => { inputs[id] = v; return { id }; },
    bool: (t, v, id) => { inputs[id] = v; return { id }; },
  },
  high: (n) => at(bars.h, n), low: (n) => at(bars.l, n), openC: (n) => at(bars.o, n), closeC: (n) => at(bars.c, n),
  time: (n) => at(bars.t, n),
  color: { white: '#fff', rgba: (r, g, b, a) => `rgba(${r},${g},${b},${a})` },
  plot: { shapes: () => { drawings.shapes++; } },
  trendLine: () => { drawings.lines++; return 'l' + drawings.lines; },
  text: () => { drawings.texts++; return 't' + drawings.texts; },
  deleteDrawingById: () => {},
  newPoint: (time, price) => ({ time, price }),
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(script, 'utf8') + '\n;globalThis.__trades = trades;', ctx);
ctx.init();
const t0 = Date.now();
for (k = 0; k < N; k++) {
  ctx.index = k;
  // several ticks per bar, like a live replay
  ctx.onTick(k + 1, null, undefined, null, inputs);
  ctx.onTick(k + 1, null, undefined, null, inputs);
}
const tr = ctx.__trades;
fs.writeFileSync(outFile, JSON.stringify(tr));
console.log(`${script.split('/').pop()}: ${tr.length} trades, ${tr.reduce((s, x) => s + x.r, 0).toFixed(1)}R, ` +
  `${(Date.now() - t0) / 1000}s, drawings ${JSON.stringify(drawings)}`);
