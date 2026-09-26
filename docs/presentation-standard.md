# How data is presented in this repo

This is the house standard for any page that shows results: backtests, scans,
reports, dashboards. The reference implementation is the Confluence Trade
Explorer, `confluence/templates/explorer.html`, rendered by
`confluence/explorer_html.py`. When you build a new page, start from that file
and keep to the rules below.

## 1. The shape of a page

**A one-screen app, not a long document.** `html` and `body` are `height:100%`
and do not scroll; each view scrolls inside its own pane.

```
┌ top bar ─ brand · tabs (pill buttons) · one-line dataset summary ───────────┐
├ toolbar ─ search · filters · "Show" presets · sort · column set · Reset ─ count ┤
├───────────────────────────────────────────────┬────────────────────────────────┤
│ table (fills the rest of the height)          │ inspector (docked, 28vw,       │
│  · header row frozen                          │  400–500px)                    │
│  · #, ID, name columns frozen                 │  sticky head: ID, name, pills, │
│  · scrolls both ways, virtualised             │  ↑ ↓ buttons                   │
│  · footer: visible range + keyboard hints     │  then tiles, charts, tables    │
└───────────────────────────────────────────────┴────────────────────────────────┘
```

* **Summary before detail.** The table is the summary; the inspector is the
  detail for the selected row. The first row is selected on load, so the page
  is complete at rest.
* **Tabs are views, not sections.** Every tab is its own scroll pane; hidden
  tabs use the `hidden` attribute and CSS must keep `[hidden]{display:none!important}`.
* **Deep links** use a bare `#token` per tab (`#learned`, `#families`).

## 2. Tables

* Virtualise anything over ~300 rows: render only the visible rows plus a
  buffer, with spacer rows above and below. No pagination.
* `table-layout: fixed` with explicit column widths, so columns never jump
  while scrolling.
* Freeze the header (`position:sticky; top:0`) and the identifying columns
  (`position:sticky; left:<offset>`), with an opaque background and a 1px
  divider after the last frozen column.
* Row height 32px, zebra striping, hover and a selected state with a 3px
  accent bar on the first cell.
* **Column sets** instead of one huge table: a default set that fits beside
  the inspector on a laptop, plus sets for each question (costs, recency,
  prop) and "All". Remember the choice in `localStorage` (wrapped in try/catch).
* Every column header has a tooltip that defines it; the same text is listed
  in the "How to read" tab.
* Numbers are right-aligned with `font-variant-numeric: tabular-nums`; text is
  left-aligned; names truncate with an ellipsis and show in full in a tooltip.
* Default filters protect the reader: e.g. **Min trades = 30** so one lucky
  trade cannot top a ranking. Say so next to the control.
* Rates get a **range filter** (two number inputs, "Win % ≥" and "Win % ≤"),
  not a single threshold, so both "high win rate" and "low win rate, big
  winners" styles can be isolated.
* When a result depends on a choice the page made for the reader (the best
  prop account, the risk per trade), show the choice as a column *and* the
  numbers it trades off (pass, bust, payout odds next to expected value), and
  offer the lower-risk alternative beside the headline pick.

## 3. Interaction

| key | action |
|---|---|
| ↑ ↓ (or j k) | move the selection; the inspector follows |
| PgUp PgDn, Home End | jump |
| / | focus search |
| Esc | close the inspector overlay (narrow screens) |
| click a header | sort; click again to reverse |

* Filters apply as you type; the count ("10,166 of 11,370") updates live.
* Clicking a family, a scatter dot or any roll-up row jumps to the table,
  filtered, with that item selected.
* Hover readouts on every chart (crosshair on lines, per-mark tooltips on bars
  and cells). Tooltips add detail; they never hold the only copy of a value.

## 4. Visual tokens (single dark look)

The explorer deliberately commits to one dark, navy "terminal" look. Every
colour is a token on `:root`; components never use literals.

| token | value | role |
|---|---|---|
| `--ground` | `#09131f` | page |
| `--panel` / `--panel-2` | `#0e1b2c` / `#0c1827` | cards, table rows (zebra) |
| `--raised` | `#132338` | headers, buttons, tooltips |
| `--hover` / `--sel` | `#17304f` / `#1b3b66` | row hover / selection |
| `--line` / `--line-2` | `#1b2e47` / `#284567` | hairlines / control borders |
| `--ink` / `--ink-2` / `--ink-3` | `#e6edf7` / `#a6b5ca` / `#7489a6` | text: primary / secondary / labels |
| `--accent` | `#3d8bfd` | selection, active tab, the one highlighted series |
| `--gain` / `--loss` | `#35c97c` / `#f3606f` | positive / negative money and R |
| `--warn` | `#e8b34d` | caution pills, VIX line, controls tag |

Semantic colour (gain, loss, warn) is separate from the accent and always comes
with a sign, a label or an icon, never colour alone.

**Type:** Archivo 700 for the brand and headings; IBM Plex Sans for UI and
numbers; IBM Plex Mono for IDs. Always with system fallbacks. Uppercase
labels are 10.5–11px with 0.6–0.8px letter-spacing.

## 5. Numbers

| kind | format | example |
|---|---|---|
| R per trade | sign, 3 decimals | `+0.226`, `−0.059` (true minus sign U+2212) |
| R totals | sign, 0–1 decimals | `+71R` |
| dollars | `$` with thousands, sign when it is a P&L | `+$8`, `−$16,672` |
| percentages | 0 decimals (1 for probabilities) | `19%`, `38.8%` |
| counts | thousands separators, window count in brackets | `+1.097 (115)` |
| missing | en dash | `–` |

Colour a number green or red only when its sign is the point (P&L, edge).

## 6. Charts

Follow the dataviz method (form first, colour last). Specifics used here:

* **Lines** 2px, round joins; one area wash at 10% opacity; end dot r=4 with a
  2px ring in the panel colour and the final value labelled beside it.
* **Bars** at most 24px wide, 4px rounded at the data end, square at the
  baseline; value labels at the tip (or beside the bar when two bars sit
  together); diverging bars for signed values, centred on a zero line.
* **Gridlines** 1px, solid, `--line`; the zero line one step darker (`--ink-3`).
* **Time windows that matter are shaded** on the time axis (last 3 years,
  last 6 months, named episodes), with a small label on top.
* **Two measures, two charts.** Never a second y-axis: VIX and strategy
  returns are stacked charts sharing the time axis.
* **Legends** whenever there are two or more series (line keys for lines,
  squares for bars); a single series is named by its heading.
* **Heatmaps** use gain/loss hues with opacity scaled to |value|, and print
  the value in every cell; a dot marks "not enough data".
* **Regime strips** (one row of month cells per dimension) use a sequential
  ramp for ordered regimes and gain/loss or warm/cool for binary states, with
  a legend under each strip.
* **Scatter** of thousands of points goes on a `<canvas>` with nearest-point
  hover and click-to-open.
* Chart text uses text tokens, never the series colour.

Inspector chart set (per item): equity with shaded windows, calendar-year
bars, month-by-month heatmap, drawdown from peak, outcome histogram,
distribution strip (P5–P95 whisker, P25–P75 box, median tick, zero line),
and results by macro regime as diverging bar rows with counts.

## 7. Honesty on the page

* Always show a **baseline** next to results (here: random-entry controls
  through the same costs), and a **luck bar** (95th percentile of the
  baseline's statistic). An optimiser that picks the best of many options
  (plans × risk levels) must run the controls through the same search, so
  the bar reflects the selection too.
* **Verdict pills** in the inspector encode the state at a glance: "Edge clears
  the luck bar" / "Edge within luck", "Profitable 8y · 3y · 6m", "Fewer than
  30 trades", "Random control".
* Anything that uses information the ranking already saw is labelled as such;
  keep one **blind test** (rank with data up to a cut-off, measure after it).
* Say where every data series comes from and how it was checked (the "How to
  read" tab).

## 8. Delivery

* One self-contained HTML file that opens from disk: data embedded as
  gzip + base64 and unpacked with `DecompressionStream` (8.8 MB for 11k
  strategies with full profiles). No runtime requests except web fonts.
* Also usable as a hosted page: `render(payload, standalone=False)` drops the
  document skeleton.
* Phones: under 760px the table becomes a virtualised card list, filters fold
  behind a "Filters" button, and the inspector is a full-screen sheet.

## 9. Checklist before shipping a page

- [ ] Opens with a realistic selection and every section filled (complete at rest)
- [ ] Header and identifying columns frozen; table scrolls both ways
- [ ] Keyboard navigation works; focus is visible
- [ ] Default column set fits beside the inspector at 1440px
- [ ] Every column has a definition; every chart has a heading saying what it shows
- [ ] Baseline or control shown next to results
- [ ] No dual axes; legends for 2+ series; values not only in tooltips
- [ ] Numbers use the formats above (sign, U+2212, thousands separators)
- [ ] Works at 400px wide; no horizontal page scroll
- [ ] Loaded once in a browser and checked for console errors
