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

# or skip evolution entirely and just backtest something
python -m evotrader.cli compare --symbols SPY,QQQ,IWM,TLT,GLD
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

## Choosing what to evolve on

Survivorship bias lives in the symbol list, so the list deserves the same rigour
as the backtester. `evotrader screen` picks one with a rule, using
TradingView's public scanner (no key, no account):

```bash
evotrader screen --preset liquid-large-cap --limit 25
evotrader screen --filter "mcap > 5e9" --filter "rsi < 35" --sort rsi
evotrader screen --preset etf-liquid --config configs/etf.json --save
```

```
liquid-large-cap  (america, 450 matches, showing 8, captured 2026-09-15)

symbol               price          mcap    avg_volume    rel_volume           rsi
----------------------------------------------------------------------------------
NVDA                212.04          5.1T        142.7M          0.37         44.95
AAPL                329.95          4.8T         52.1M          0.30         59.80
```

`--config` writes the symbols straight into a run config; `--save` writes a
dated snapshot under `data/universes/`. Presets: `liquid-large-cap`,
`liquid-mid-cap`, `high-volatility`, `etf-liquid`, `crypto-major`. Any
[TradingView column](https://www.tradingview.com/screener/) works in a
`--filter`, with `evotrader screen`'s aliases (`mcap`, `avg_volume`, `perf_y`…)
as shorthand.

### The bias this does not fix

**The scanner reports the present.** It has no history, so it cannot feed a
backtest — bars still come from Yahoo via `data.py`. More importantly, a
universe screened today and backtested on an earlier window is *selection on
the outcome*: "market cap > $10B today" silently means "companies that grew".
Snapshots are stamped with their capture date and the tooling says so out loud:

```
universe 'liquid-large-cap' was screened on 2026-09-15 but the backtest starts
2015-01-01. Symbols were selected using data from after the test window, so
results carry survivorship and look-ahead bias — treat them as a hypothesis,
not a measurement.
```

Screening is honest when you screen today and trade *forward*, when you filter
on slow-moving structural traits (listing venue, instrument type), or when you
accumulate dated snapshots until you have a real point-in-time universe. It is
not honest as a way to pick winners for a historical run.

### As an MCP server

The screener and the backtester are exposed over MCP, sharing one process and
one set of caches. `.mcp.json` in this repo registers it; `pip install mcp` to
enable it.

```bash
python -m evotrader.mcp_server      # stdio
```

| tool | does |
|---|---|
| `backtest` | one strategy or ad-hoc rules over a universe |
| `compare_strategies` | rank the library, or a chosen subset |
| `walk_forward_test` | anchored folds; consistency across regimes |
| `optimize_strategy` | grid search with a held-out window |
| `list_strategies` / `describe_strategy` | what can be run, and its rules |
| `list_features` / `validate_strategy` | the rule vocabulary, and a dry-run check |
| `data_cache` | which prepared windows are in memory |
| `screen_symbols` / `quote` / `save_universe` | TradingView screening (above) |
| `list_presets` / `list_columns` | the screen and column vocabulary |

A prepared window is memoised, so the first backtest over a universe costs a
download and a feature build and every later one costs ~0.2s of CPU. Comparing
fourteen strategies over ten years of five symbols takes about 1.5 seconds.

---

## Backtesting anything, without an evolution run

The engine the evolution loop uses is available directly, so a strategy can be
tested without breeding one. Same fills, same costs, same portfolio accounting,
and buy-and-hold reported alongside every result.

```bash
evotrader strategies                       # 28 named strategies
evotrader simulate --strategy rsi_pullback --symbols SPY,QQQ,IWM
evotrader simulate --entry "rsi14 < 25 and close > sma200" --exit "rsi14 > 65"
evotrader compare  --symbols SPY,QQQ,IWM,TLT,GLD --start 2015-01-01
```

```
14 strategies over GLD, IWM, QQQ, SPY, TLT  2015-01-02..2024-12-31 (2516 1d bars)

strategy                fitness   return   vs b&h  sharpe   maxdd  trades
-------------------------------------------------------------------------
squeeze                    0.71   +83.1%   -90.2%    0.85  -10.4%      75
triple_ma                  0.63   +79.6%   -93.7%    0.79  -12.5%      71
ma_cross                   0.46  +108.3%   -65.0%    0.84  -20.5%     102

buy-and-hold over the same window: +173.2%
```

That last line is the point of the table. Three strategies made money; none of
them beat owning the index.

### Intraday

`--interval` accepts `1d`, `1h`, `30m`, `15m` and `5m`. Yahoo only serves
intraday history for a trailing window — 730 days hourly, 60 days finer — and
requests outside it are refused rather than silently returning nothing.
Annualisation follows the bar size, so an hourly Sharpe is not a daily Sharpe
multiplied by a wrong constant.

### Two kinds of validation, which answer different questions

```bash
evotrader simulate --strategy triple_ma --walk-forward --start 2010-01-01
```

```
  fold1   train +94.8% (bh +261.4%)   test  -6.4% (bh -10.5%)  11 trades
  fold2   train +85.3% (bh +216.4%)   test  -2.6% (bh  +4.9%)   7 trades
  fold3   train +80.5% (bh +259.3%)   test +13.4% (bh +33.8%)  11 trades

  beat buy-and-hold in 1 of 3 folds
```

Walk-forward runs **fixed** rules across anchored folds, so a train/test gap
measures *regime dependence*: the same rules worked in one period and not
another. Nothing was fitted, so nothing was overfitted.

Overfitting needs a *choice* made from the data, which is what `--grid`
measures — it searches a parameter grid on a training window and reports the
winners on bars the search never saw:

```bash
evotrader simulate --strategy rsi --grid "oversold=20,25,30,35,40" \
                   --grid "overbought=55,60,65,70" --start 2010-01-01
```

```
rsi: 20 combinations, chosen on 2010-01-04..2021-03-31, scored on 2021-04-01..2024-12-31

parameters                                 train  held out    vs b&h
--------------------------------------------------------------------
overbought=65, oversold=35                +70.6%    +19.1%    +27.9%
overbought=70, oversold=30                +43.2%    +13.1%    +27.9%

  retained 0.27 of the in-sample return out of sample
```

Keeping 27% of an in-sample result is the normal outcome of a parameter
search, not a bug in one. That is the number the sweep exists to produce.

Folds slice a feature matrix computed once over the full history. Every feature
is causal — each bar derives only from bars at or before it — so a slice leaks
nothing forward while arriving already warmed up. Recomputing per fold instead
would spend the first ~200 bars on indicator warmup, which is most of a short
validation window.

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

**Market features:** OHLCV, returns over 1/5/20/60 bars, SMA 10/20/50/100/200,
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
  screener.py     TradingView scanner client; rule-based universe selection
  strategies.py   named, parameterised strategies in the rule language
  backtest_api.py cached datasets, comparison, walk-forward and optimisation
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
  mcp_server.py   backtesting and screening exposed as an MCP server
```

## Tests

```bash
python -m pytest tests -q      # 212 tests, ~9s
```

They cover the rule language (including that hostile input is rejected), the
indicators, no-look-ahead fills and risk-limit enforcement in the backtester,
fitness behaviour, the genetic operators, the full Claude breeding path against
a stubbed client, and a complete run with checkpoint and resume. The newer
files cover the strategy library, the backtest API and its caches, the screener
against a stubbed transport, both CLI surfaces, and the invariants the speed
work depends on — that a restricted feature snapshot equals the full one, and
that a sliced feature window equals the same bars of the whole series.

## Performance

About 50ms per backtest over ten years of five symbols, single-threaded. A
100 x 1000 run is ~100k backtests: roughly 45 minutes single-threaded, or
under ten with `--workers 8`.

Most of that came from one observation: a rule reads three or four features,
not the forty-odd that exist, so a compiled genome reports which it needs and
the backtester builds only those per bar. That alone was a 10x speedup, and it
applies to evolution and ad-hoc backtests alike. Evaluation also parallelises
across processes, and market data and features are computed once and shared —
a prepared window is memoised, so the first backtest over a universe pays for
the download and the feature build and every later one does not.

## Limits worth stating plainly

* Long-only, one lot per symbol. No shorting, leverage or options. Intraday
  bars are supported but only for as far back as Yahoo serves them.
* Fills assume you can transact at the next open at the modelled slippage.
  Illiquid symbols will flatter themselves.
* Survivorship bias lives in your symbol list. Picking today's winners and
  evolving on their history proves nothing — `evotrader screen` makes the
  choice explicit and dated, which is not the same as making it unbiased.
* A backtest is not a forecast. This is a research tool for generating and
  stress-testing hypotheses about strategies.
