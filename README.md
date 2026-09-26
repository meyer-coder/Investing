# Investing

Two research tools live here:

* **`confluence/`** — a strategy factory that generates ~11,000 named, confluence-based intraday
  strategies for MNQ, MES (ES), NAS100, USOIL, EURUSD, GBPUSD, USDJPY, XAUUSD and GER40, backtests
  every one on 8 years of 1-minute data with realistic costs, logs the results, and builds a
  sortable **explorer** (`results/explorer.html`).
* **`evotrader/`** — evolving daily-bar paper-trading agents bred by Claude (below).

---

## confluence: strategy factory + explorer

```bash
pip install -r requirements.txt            # numpy, numba, pandas
python -m confluence.cli fetch             # 8+ years of 1-minute bars for every market (~10 min)
python -m confluence.cli crosscheck        # how closely each feed tracks the real contract
python -m confluence.cli macro             # VIX, yields, dollar, S&P, CPI, FOMC and jobs-report days
python -m confluence.cli run               # generate, backtest, log, build the explorer (~4 min, 4 cores)
open results/explorer.html                 # or double-click it; no server needed
python -m confluence.cli show 22-091       # one strategy's rules and numbers in the terminal
```

### What gets produced

| file | what it is |
|---|---|
| `results/explorer.html` | self-contained explorer (6 MB, opens from disk): a one-screen table with a frozen header and ID/strategy columns that scrolls smoothly through every strategy, a docked detail panel (rules, equity curve with the 3y/6m windows shaded, yearly bars, $/day distribution, prop-eval odds, last trades), arrow-key navigation (`↑` `↓`, `/` to search), column sets (Core / Costs / Recency / Prop / All), filters by market / timeframe / group / family / session / entry / stop / target / min trades / max trades per week, and a card layout on phones. Tabs: All strategies, Families, Groups & dimensions, Lessons, How to read |
| explorer tab **What we learned** | every trade tagged with the macro regime it was entered in (VIX level and term structure, Fed cycle, 10-year yield trend, dollar, S&P 500 trend, CPI, FOMC and jobs-report days), each regime compared with random controls in the same regime; findings, an 8-year timeline with regime strips, per-regime charts, group × regime and market × regime heatmaps, named episodes (COVID crash, 2022 bear, April 2025 tariffs), and a before/after-6-months scatter |
| `results/macro_regimes.csv` | the regime tag of every trading day, so any tag can be checked |
| `results/strategies_ranked.csv` | the same table for Excel, ranked by the recency-weighted score, with each strategy's rules |
| `results/test_log.jsonl.gz` | the test log: one JSON line per strategy — definition, rules, every metric, yearly results, equity curve |
| `results/run_log.md` | what ran, on what data, how long it took, the top 25, and the lessons |
| `results/data_quality.json` | proxy cross-checks against Yahoo futures and TradingView |
| `runs/trades/*.npz` | every simulated trade (millions; not committed) |

### How strategies are built

Every strategy is a conjunction of **confluence legs** (`confluence/components.py`):

* **bias** — HTF trend, EMA stack, 200 EMA, daily bias, VWAP side, Supertrend, ADX, midnight open…
* **location** — VWAP / EMA pullbacks, VWAP bands, prior-day / prior-week / Asia / London / overnight
  high-low sweeps and breaks, opening range, initial balance, fair-value gaps, order blocks,
  Bollinger / Keltner tags, pivots, Fibonacci 50–61.8, round numbers, double bottoms, gaps, squeezes…
* **trigger** — engulfing, pin bar, break of structure, EMA cross, RSI reset, MACD cross, inside-bar
  break, displacement, Heikin-Ashi flip, Supertrend flip, RSI divergence, exhaustion…
* **filter** (optional) — ATR expanding / calm, RSI room, ADX rising, strong close, range spike, not extended

49 named **families** combine them into trading ideas (EMA Pullback Engulf, Asia Sweep London
Reversal, ORB + VWAP + Trend, Silver Bullet FVG, Power of Three, VWAP 2σ Fade, …) across seven
groups. The generator crosses each family with market × timeframe (1/3/5/15/30/60m) × session
(Asia, London, NY am, NY pm, Ldn+NY, all) × entry (market / stop / limit) × stop (ATR 1.0, ATR 1.5,
swing, signal bar) × target (1R, 1.5R, 2R, 3R, trailing, session close) × extra filter, and samples
210 balanced variants per family. Each gets an ID (`07-031`) and a descriptive name, e.g.
*"Hull-Slope VWAP Hold + RSI room · MNQ 5m NY am · stop entry, swing stop, 2R"*.

Family 50 is **RANDOM control**: 1,080 coin-flip strategies on a grid of market × exit style, run
through the same sessions, stops, targets and costs. They are the yardstick for luck: every
strategy's *edge* is its gross R/trade minus the median of the controls with the same market and
exit, and the *luck bar* is the 95th percentile of the controls' own edge t-statistic.

### Recency weighting

All 8 years are tested; the ranking leans on the recent past, with the last 6 months weighted a
little more than the last 3 years:

```
score = 0.25 · E(8y) + 0.35 · E(3y) + 0.40 · E(6m)        E(w) = total net R in w / (trades in w + 30)
```

The shrinkage stops a strategy with a handful of lucky trades from topping the table. The prop-firm
Monte Carlo samples days with the same weights. The Lessons tab also runs the honest version: rank
using only data up to six months ago, then look at how the top 5% did in the six months after.

### Data

| source | used for |
|---|---|
| **histdata.com** | the 8-year 1-minute backbone (one zip per symbol-year). Timestamps are New York time *with* DST — verified against Dukascopy (correlation 1.0 at the right offset, ~0 at the wrong one) |
| **Dukascopy** | fills every day histdata is missing or thin on (e.g. all of WTI 2024 – May 2026, most of 2023), and extends each feed to the last session. Splices are checked minute-by-minute |
| **Yahoo Finance** | real futures (NQ=F, ES=F, CL=F, GC=F …) to cross-check each proxy: 5-minute return correlation 0.96–0.99 for indices, oil and gold |
| **TradingView** (MCP) | spot check of CME_MINI:MNQ1! / MES1! against the proxy feeds (0.999 / 0.998) |
| **massive.com** | `data.fetch_massive` pulls minute aggregates when `MASSIVE_API_KEY` (or `POLYGON_API_KEY`) is set |

MNQ and MES are backtested on the index CFD feed that tracks the same underlying (continuous, no roll
gaps) and charged futures costs; NAS100 uses the same prices with CFD costs. Costs per round trip
are in `confluence/markets.py` (MNQ 1.2 pts, MES 0.78 pts, NAS100 1.8 pts, EURUSD 1.2 pips, …).

### How trades are simulated

Signals on bar close; orders from the next bar. Entries, stops, targets, trailing stops and session
exits are walked through the 1-minute bars underneath, so a 60-minute strategy knows whether its
stop or target was hit first; if both fall inside one minute the stop wins. Stops are never tighter
than 0.3 ATR, one position at a time, at most four trades a day, always flat at the session exit and
never across a data gap. The engine was checked on synthetic random walks: with a near-continuous
price path, random entries average ~0R gross for every entry and exit type.

### Presentation standard

Pages in this repo follow [`docs/presentation-standard.md`](docs/presentation-standard.md); the explorer
(`confluence/templates/explorer.html`) is the reference implementation.

### Read the results with care

11,000 tests will always produce some that look spectacular by chance. Use the random controls,
the edge t-statistic, the "profitable 8y + 3y + 6m" filter and the blind test in Lessons before
believing the leaderboard. Nothing here connects to a broker.

---

# evotrader


Evolving paper-trading agents, bred by Claude.

A population of trading agents is backtested on real market data. The best few
are handed to Claude, which reads their rules **and their trade journals**,
works out why they made money, and writes the next generation. Repeat for as
many generations as you can afford.

```
  100 agents  ->  backtest each on historical bars  ->  rank by fitness
       ^                                                     |
       |                                                     v
  next generation  <-  Claude reads the top 3-5 journals and writes new agents
```

Nothing here trades real money, and nothing here connects to a broker. Every
fill is simulated.

---

## The one design decision worth knowing

**Claude is the breeder, not the tick-by-tick trader.**

An agent's genome is a small, readable strategy spec — a thesis in English plus
entry rules, exit rules and risk limits:

```
Oversold Dip Buyer (id=8f3a1c2b9d04, gen=17, origin=llm)
  thesis: Buy fear inside an intact uptrend, sell into the bounce.
  BUY  30% when: rsi14 < 32 and close > sma200 and mkt_above_sma200 == 1
  SELL when: rsi14 > 60
  SELL when: position_return < -0.07 or bars_held > 30
  risk: max_pos=30% max_open=4 gross<=100% stop=8% ... cooldown=5
```

That spec executes as a deterministic rule engine, so a backtest costs about
0.2 seconds of CPU and no tokens at all. Claude is called **once per
generation** — to analyse the winners and author the next batch — instead of
once per trading decision. The difference is the whole project:

| | LLM per decision | LLM per generation (this repo) |
|---|---|---|
| API calls for 100 agents x 1000 generations | ~10^8 | ~10^3 |
| Cost at Opus 5 list prices | millions of dollars | ~$210 |
| Wall clock | months | hours |

You still get reasoning in the loop — it just operates on *evidence about
trading* rather than on each bar.

---

## Quick start

```bash
pip install -r requirements.txt
python -m evotrader.cli doctor          # checks data access, credentials, deps

# a cheap first run: 30 agents, 10 generations, capped at $5 of API spend
python -m evotrader.cli run --config configs/quick.json

# no API key and no network: synthetic prices, mutation-only breeding
python -m evotrader.cli run --config configs/offline.json

# the real thing
python -m evotrader.cli run --config configs/default.json     # 100 x 1000
```

Every run streams progress and writes to `runs/evotrader.sqlite`:

```
gen   17 | best +1.412 | mean -0.286 | Regime-Gated Dip Buyer  ret +91.2% (bh +43.0%) sharpe 1.21 mdd -12.4% trades 46 win 61% | 6.8s | $0.21 (run $3.44)
        held-out: ret +18.9% (bh +19.3%) sharpe 1.31 mdd -7.1% trades 11 win 64%
        claude: The two survivors that beat buy-and-hold both required a trend filter...
```

Then:

```bash
python -m evotrader.cli report --html reports/run.html   # leaderboard + chart + Claude's analysis
python -m evotrader.cli inspect <genome-id>              # rules, metrics, trades, ancestry
python -m evotrader.cli backtest <genome-id> --start 2025-01-01 --end 2025-12-31
python -m evotrader.cli resume <run-id> --generations 200
```

Runs checkpoint every generation, so `resume` picks up exactly where a run
stopped — which matters when 1000 generations takes hours.

## Credentials

Breeding uses the Anthropic API. Set `ANTHROPIC_API_KEY`, or run `ant auth
login`. Without credentials the run still works: it falls back to mutation and
crossover and says so once at startup.

## Cost

`run --dry-run` prints the estimate before anything happens:

```
plan: 100,000 backtests, 1,000 breeding calls (~$210.00 at claude-opus-5 list prices)
```

Three knobs bring that down: `--llm-every 5` (breed with Claude every fifth
generation, mutation in between), `--llm-share 0.3` (fewer Claude-authored
offspring per generation), and `--model claude-sonnet-5` (~2.5x cheaper).
`--budget 25` is a hard ceiling: once spent, the run continues on mutation
alone rather than stopping.

---

## How a generation works

1. **Evaluate.** Every genome is backtested over the training window. Decisions
   are made on a bar's close and filled at the **next** bar's open, with
   commission (1bp) and slippage (5bp) charged on both sides. Identical
   strategies are cached, so carried-over elites are not re-run.
2. **Score.** Fitness is not raw return — that just breeds leverage into one
   lucky regime. The composite is
   `sharpe + 1.5 x annualised excess return over buy-and-hold`, minus charges
   for drawdown past 20%, turnover past 6x/year, and trade counts too small to
   mean anything. All weights live in `FitnessConfig`.
3. **Select.** Top `elites` (default 5) survive unchanged into the next
   generation, so the best score can never go backwards.
4. **Breed.** The elites' genomes, metrics, best and worst trades, rule-fire
   counts and entry reasoning are written into a briefing, along with what the
   *losers* did and the score history of previous generations. Claude returns
   an `analysis`, a list of `lessons` carried forward, and a batch of new
   genomes as strict JSON. Offspring that do not compile are dropped and
   backfilled by mutation; the population size never changes.
5. **Record.** Genomes, scores, elite trade journals, Claude's analysis, and a
   resumable checkpoint all go into SQLite.

### Guarding against the obvious failure mode

Any search this aggressive will find something that looks brilliant in-sample.
Three defences are built in:

* The last 25% of history is **held out**. Leaders are scored on it every
  generation, and that score is reported, stored, and **never used for
  selection**. When training fitness climbs while held-out fitness does not,
  you are watching overfitting happen in real time.
* Buy-and-hold over the same window is the benchmark in the fitness function,
  so an agent that merely rides the market up does not score as a discovery.
* The breeder is told explicitly to call out results that look like luck or
  like beta in disguise, and to keep more than one hypothesis alive in the
  population.

None of this makes an evolved strategy predictive out of sample. Treat a
champion as a hypothesis worth examining, not a signal worth trading.

---

## The strategy language

Rules are boolean expressions over a fixed vocabulary, parsed by a small
recursive-descent parser in `dsl.py`. There is no `eval` anywhere — a genome,
whoever wrote it, cannot reach outside the feature set.

```
rsi14 < 30 and close > sma200
cross_above(macd, macd_signal) and volume_ratio > 1.5
dist_sma20 < -0.03 and mkt_above_sma200 == 1 and vol20 < 0.35
position_return > 0.18 or bars_held > 40 or position_drawdown < -0.06
```

**Market features:** OHLCV, returns over 1/5/20/60 bars, SMA 10/20/50/200,
EMA 12/26, distance from each average, RSI 7/14, MACD and its signal and
histogram, ATR and ATR%, realised volatility over 20/60 bars and their ratio,
Bollinger bands and %B, 20-bar z-score, position within the 52-week range,
relative volume, plus three market-regime features computed from the
equal-weighted universe.

**Portfolio features** (mostly for exits): `in_position`, `bars_held`,
`position_return`, `position_drawdown`, `position_weight`, `cash_pct`,
`gross_exposure`, `position_count`, `bars_since_exit`, `portfolio_return`,
`portfolio_drawdown`.

**Functions:** `cross_above`, `cross_below`, `prev`, `change`, `abs`, `min`,
`max`, `clamp`.

To add a feature, compute it in `features.py` and name it in `MARKET_FEATURES`
with a line in `FEATURE_DOCS` — the docs are what Claude is shown, so the
breeder can use a new feature the moment it exists.

---

## Data

Daily OHLCV from Yahoo Finance's public chart endpoint — no key needed — cached
as CSV under `data/cache/`. Prices are adjusted for splits and dividends so
corporate actions do not look like tradeable gaps. Symbols are aligned onto
their shared calendar. `--offline` swaps in a deterministic synthetic
random-walk generator so the whole system runs with no network at all.

```bash
python -m evotrader.cli fetch --symbols SPY,QQQ,IWM,TLT,GLD --start 2005-01-01
```

## Layout

```
evotrader/
  indicators.py   vectorised technical indicators
  data.py         fetching, caching, alignment, train/test splitting
  features.py     the per-bar feature vocabulary agents trade on
  dsl.py          the safe rule language (tokenizer, parser, evaluator)
  genome.py       the agent: thesis, rules, risk limits, lineage
  broker.py       paper broker: cash, positions, commission, slippage
  runner.py       the backtest engine (decide on close, fill at next open)
  journal.py      trades and thoughts — what the breeder reads
  fitness.py      metrics and the composite fitness function
  population.py   seed archetypes, mutation, crossover
  llm.py          Claude client: structured output, retries, cost ceiling
  prompts.py      the breeding briefing and its JSON schema
  breeder.py      LLM / mutation / hybrid breeders
  evolution.py    the generation loop, checkpointing, parallel evaluation
  store.py        SQLite persistence
  report.py       console, Markdown and HTML reports
  cli.py          command line interface
```

## Tests

```bash
python -m pytest tests -q      # 76 tests, ~30s
```

They cover the rule language (including that hostile input is rejected), the
indicators, no-look-ahead fills and risk-limit enforcement in the backtester,
fitness behaviour, the genetic operators, the full Claude breeding path against
a stubbed client, and a complete run with checkpoint and resume.

## Performance

About 0.2s per backtest over seven years of five symbols. A 100 x 1000 run is
~100k backtests: roughly 6 hours single-threaded, or about 1 hour with
`--workers 8`. Evaluation parallelises across processes; the market data and
features are computed once and shared.

## Limits worth stating plainly

* Long-only, one lot per symbol, daily bars. No shorting, leverage, options or
  intraday data.
* Fills assume you can transact at the next open at the modelled slippage.
  Illiquid symbols will flatter themselves.
* Survivorship bias lives in your symbol list. Picking today's winners and
  evolving on their history proves nothing.
* A backtest is not a forecast. This is a research tool for generating and
  stress-testing hypotheses about strategies.
