# The strategy prompt builder

`tools/promptbuilder` turns a strategy spec into a complete, hyper-specific
backtest brief plus a machine-readable variation manifest. It exists so that
writing a new backtest prompt is filling in a form rather than re-deriving —
and re-forgetting — the guardrails each time.

```bash
PYTHONPATH=tools python3 -m promptbuilder.cli \
    tools/promptbuilder/specs/example-nq-5m.yaml -o build/prompts
```

```
  grid: axes: trend_filter(4) x volume_filter(3) x vwap_filter(3) x stop(4) x target(4) = 576 combinations
  grid: 576 variations, inside the 500-800 band, no reduction needed
  sample: 480/576 variations reach 400 trades on 1260 days (5.0y)
  sample: worst case needs 1905 days (7.6y) — reported as insufficient
  stats: E[max t] under null = 3.57, Bonferroni alpha = 8.68e-05
```

Two files come out: `<spec>.prompt.md`, the brief you send, and
`<spec>.variations.json`, the enumerated grid the backtester consumes. The
manifest is what makes the loop automatable — the same grid, reproducible from
a seed, feeding both the prompt and the runner.

---

## What it refuses to do

The builder's main job is saying no. Each refusal maps to a failure observed in
a real brief (see [the backtest prompt breakdown](backtest-prompt-breakdown.md)).

| Refusal | Why |
|---|---|
| No `strategy` block | A brief that does not say what it tests produces polished work on the wrong strategy. This is the single most expensive failure and the reason the tool exists. |
| Missing any of name / instrument / timeframe / thesis / entry_rules / exit_rules / risk | Each was silently guessed at some point. |
| Empty rule list | "Entry rules: []" is an unstated strategy wearing a hat. |
| `history_days` or `base_signals_per_day` ≤ 0 | Feasibility depends on both. A guess you state beats a guess you hide. |
| Fewer than 2 axes, or an axis with 1 value | That is not a variation grid. |
| `pass_rate` outside (0, 1] | A filter that admits more than everything is a modelling error. |
| Any unfilled `{{SLOT}}` in the rendered prompt | A half-filled template is worse than no template. |

---

## The three things it computes

### 1. The grid

Full cartesian product of the axes. If it exceeds the ceiling, the builder
subsamples with a seeded RNG and **says so in the prompt** — it does not
truncate, because truncation drops whole axis values and biases the comparison.
The same seed reproduces the same grid, so a re-run is comparable to the
original.

### 2. Feasibility — the part that matters most

Each axis value carries a `pass_rate`: the fraction of base signals that survive
that filter. A variation's selectivity is the product of its filters, so:

```
trades_per_day   = base_signals_per_day × selectivity
attainable       = trades_per_day × history_days
required_days    = min_trades / trades_per_day
```

A variation that cannot reach the trade floor is marked infeasible **before any
data is fetched**, and the generated prompt instructs that it be reported as
`insufficient sample` and excluded from ranking.

This matters because selectivity cuts both ways: stacking filters is exactly
what makes a variation look impressive and simultaneously makes it unprovable.
Those are the same variations. Without this check they win the leaderboard.

### 3. Multiple-comparison arithmetic

Rank 500–800 variations and the best one is a near-certainty even if none has an
edge. The builder computes and embeds the numbers:

- expected best-of-N t-statistic under the null ≈ `sqrt(2 ln N)` — **≈3.6 at
  N=650**, which reads as "highly significant" to anyone scoring one strategy;
- Bonferroni threshold `0.05/N` — **p < 8.7e-05, |z| > 3.95 at N=576**;
- a pointer to Benjamini–Hochberg FDR and the Deflated Sharpe Ratio, which are
  better suited because these variations are correlated, not independent.

---

## The test window and recency emphasis

```yaml
window:
  lookback_years: 3          # drives history_days (x252) unless stated explicitly
  emphasis_months: 6         # the recent period that carries extra weight
  recent_weight: 0.6         # 60% of the ranking score comes from it
  method: weighted           # weighted | half_life | gate
  require_recent_positive: true
```

Three ways to express "the market is changing, weight the recent stuff":

* **`weighted`** — score the full window and the recent window separately, rank on
  `recent_weight x recent + (1 - recent_weight) x full`, and report both parts so
  the blend can be undone by eye.
* **`half_life`** — weight each trade by `0.5 ** (age / half_life_days)`. The
  prompt also demands the *effective* sample size `(Σw)² / Σw²`, because decay
  shrinks it more than people expect.
* **`gate`** — rank on the full window but disqualify anything not also profitable
  recently. Recency as a filter rather than a weight.

### The two things recency breaks, and how the builder handles them

**1. It shrinks the sample, so it needs its own floor.** The emphasis window is a
fraction of the whole, so demanding the same absolute trade count inside it is
arithmetically impossible. `min_trades_recent` therefore defaults to the full
floor scaled by window length — 400 x 126/756 = **67** for a 3-year/6-month
split — and the spec is rejected if you set it above the full-window floor. A
variation clearing one floor but not the other is reported as `full window only`
and is not ranked.

**2. Emphasising and validating on the same bars is circular.** The
out-of-sample split is chronological, so it lands on exactly the recent period
being emphasised: select on it and test on it and you have done one act twice.
Every generated prompt carries the fix — walk-forward folds, recency weighting
applied only inside each fold's training portion, the final emphasis window kept
as a fold nothing was selected on, reported separately. If walk-forward is not
run, the prompt requires the whole result be labelled in-sample.

---

## The two standing constraints

Both are baked into every generated prompt:

- **400–500 trades per strategy** (`guardrails.min_trades`, `target_trades`).
  Below the floor a variation is reported as `insufficient sample` and never
  ranked, however good it looks.
- **500–800 variations per prompt** (`grid.target_min`, `target_max`). Under the
  floor the builder names the axis to extend; over the ceiling it subsamples and
  discloses it.

### What those two constraints cost in data

They interact, and the interaction is the binding constraint on the whole
programme. Holding the example grid fixed and varying only available history:

| History available | Variations reaching 400 trades |
|---|---|
| 60 calendar days (≈42 trading days) | **0 of 576** |
| 1 year | 32 of 576 |
| 3 years (the standing window) | 304 of 576 |
| 5 years | 480 of 576 |
| 10 years | **576 of 576** |

At the standing 3-year window, **304 of 576** variations clear the 400-trade
floor and the rest are correctly reported as insufficient. That is a healthy
outcome, not a failure: the excluded 272 are the most heavily filtered
variations, which are precisely the ones that would otherwise top the
leaderboard on a sample too small to mean anything.

### What the data actually supports — measured, not assumed

Bar depth from the TradingView feed, probed directly rather than estimated:

| Symbol | Timeframe | Bars returned | Span |
|---|---|---|---|
| `CME_MINI:NQ1!` (E-mini future) | 5-minute | 5,798 | **≈1 month** |
| `CME_MINI:NQ1!` | 15-minute | 5,413 | ≈3 months |
| `CME_MINI:NQ1!` | 60-minute | 10,154 | **≈1.7 years** |
| `CFI:US100` (CFD) | 5-minute | 5,779 | ≈1 month |

The feed caps intraday history by bar count (~5–6k below hourly, ~10k hourly),
not by date. Two consequences:

* **The CFD rung does not deepen 5-minute history.** It returns the same one
  month as the future, so as a fallback for *depth* it is useless — it is a
  fallback for *availability* only.
* **Three years at 5-minute is not obtainable from this feed.** The honest
  choices are: run 5-minute on ~1 month and treat it as a pilot, not evidence;
  run the 3-year window at 60-minute where the history exists; or buy the
  history from a vendor (Databento GLBX.MDP3 or equivalent) and keep 5-minute.
  The generated prompt's fallback clause covers the first two; the third is a
  purchasing decision, better made before the first backtest than after.

---

## Spec format

See [`tools/promptbuilder/specs/example-nq-5m.yaml`](../tools/promptbuilder/specs/example-nq-5m.yaml).
The `strategy` block is yours to replace; the rest is mostly reusable defaults.

```yaml
strategy:          # required, all of it
  name / instrument / timeframe / direction / thesis
  entry_rules: []  # non-empty
  exit_rules:  []  # non-empty
  risk: {}         # non-empty
  session_in_spec: "09:30-11:00 America/New_York"
  override_session: true     # test around the clock anyway

data:
  sources: []                # ordered ladder; rung 1 preferred
  history_days: 1260         # what you believe the best rung delivers
  base_signals_per_day: 3.0  # unfiltered signal rate — drives feasibility

grid:
  target_min: 500
  target_max: 800
  seed: 7
  axes: []                   # each value may carry a pass_rate

guardrails:
  min_trades: 400
  target_trades: [400, 500]
  oos_fraction: 0.3

analysis:
  session_buckets: []
  seasonality: [month, year, day_of_week, week_of_month]
  events: true

deliverables: [pdf, html_dashboard]
```

---

## What the generated prompt carries

Every brief contains, without you having to remember any of it: the full
strategy spec; the data ladder with an explicit instruction to drop a rung
rather than stop and ask; a demand for provenance on page one of both
deliverables; a session override so a spec written for the open still gets
tested around the clock; the trade-count floor with the exclusion rule; a
chronological in/out-of-sample split with ranking on out-of-sample; the
multiple-comparison correction with its numbers; a benchmark requirement; a
costs-and-fills statement; and a fallback paragraph for when the data turns out
to be thinner than assumed.

It closes by requiring the full distribution of all variations rather than a
top-10 table, and a plain-language verdict including the strongest argument
*against* the strategy — because a 500-way search that reports only its winner
has not told you anything.

---

## Tests

```bash
python3 -m pytest tests/test_promptbuilder.py -q     # 21 tests
```

They cover every refusal above, grid reproducibility under a fixed seed, the
selectivity-to-required-history arithmetic, the multiple-comparison figures, and
an end-to-end build asserting the example flags exactly 96 of 576 variations as
insufficient.
