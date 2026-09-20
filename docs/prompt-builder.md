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
| Yahoo free 5-minute (60 calendar days ≈ 42 trading days) | **0 of 576** |
| 1 year | 32 of 576 |
| 5 years | 480 of 576 |
| 10 years | **576 of 576** |

**A 400-trade floor across a 500–800 grid needs roughly ten years of 5-minute
data.** No keyless source supplies that: Yahoo's intraday API is hard-capped at
60 days, which yields zero qualifying variations — not a degraded run, a
categorically impossible one. This programme requires a paid historical feed
(Databento GLBX.MDP3 or equivalent). That is a purchasing decision, not a
modelling one, and it is better to know before the first backtest than after.

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
