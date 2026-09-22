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

# breed toward a particular trader's style (see "Breeding for a trading style")
python -m evotrader.cli run --config configs/leveraged_swing.json

# score hand-written strategies on a config's windows (see "Hand-written strategies")
python -m evotrader.cli evaluate strategies/quick_leveraged.json --config configs/quick_nasdaq.json --by-year
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

## Breeding for a trading style

By default the loop breeds toward whatever the fitness function rewards on
the configured universe, which for `configs/default.json` means low-turnover
ETF rotation. A **style** points it at a particular way of trading instead.
A style has two parts, both defined in `styles.py`:

* a **mandate**: plain-English guidance appended to every breeding briefing,
  so Claude breeds toward that behaviour rather than toward whatever one
  backtest window happens to reward;
* **seed archetypes**: hand-written genomes in that style, placed at the
  front of generation 0 so the population starts with the behaviour instead
  of having to stumble onto it.

The fitness weights that make a style score well stay in the run config,
because they are the part worth arguing about per run. Set `"style"` in the
config or pass `--style` on the command line.

### `leveraged_swing`: leveraged core names, small wins

Modelled on a real account's recent trading: buy 2x/3x ETFs on large,
well-known names (Nasdaq-100, semis, mega-cap tech), hold one to seven days,
take a gain of 5-15% on the leveraged product and leave; keep each position
at 10-15% of equity with up to six or eight open; cut losers slowly, around
-10%. The portfolio itself is never levered. The leverage lives in the
instruments, which are just symbols to the engine.

```bash
python -m evotrader.cli run --config configs/leveraged_swing.json        # 2x mega-cap ETFs + TQQQ/SOXL, since Dec 2022
python -m evotrader.cli run --config configs/leveraged_swing_long.json   # 3x index and sector funds since 2015
python -m evotrader.cli run --config configs/quick.json --style leveraged_swing
```

What the style configs change, and why:

| knob | default | style | reason |
|---|---|---|---|
| `turnover_limit` / `turnover_penalty` | 6x / 0.10 | 120x / 0.01 | one-week holds turn the book over 50-100x a year; the default scores that as churn |
| `excess_weight` | 1.5 | 0.5 | buy-and-hold of leveraged funds through a bull run is not the bar; return still counts, but less than consistency |
| `win_rate_weight` | 0 | 2.0 | rewards `win_rate - 0.5`: many small wins is the point |
| `hold_limit_bars` / `hold_penalty` | off | 7 bars / 1.0 | an average hold twice the limit costs a full point; drifting into buy-and-hold is the failure mode |
| `drawdown_limit` | 20% | 25% | leveraged products swing; the portfolio still has to stay intact |
| `min_trades` | 10 | 40 | short holds should produce many trades; fewer is noise |
| `slippage_bps` | 5 | 10 | single-stock leveraged ETFs trade wider than SPY |

Two universes ship because history is the constraint. 2x single-stock ETFs
on mega-caps only date from late 2022, so `leveraged_swing.json` has under
four years of bars and a thin held-out window: treat its results as
hypotheses. `leveraged_swing_long.json` uses 3x index and sector funds with
history since 2015, which is where a claimed edge can actually be tested.
Newer single-stock funds (MUU, RIOX, MSTU) fit the style but would truncate
the whole universe to their own short history, since symbols are aligned on
their shared calendar.

### `quick_leveraged`: one to three sessions, long and short funds

For funded accounts, where a trade lasts a session or three. The universe is
leveraged funds in both directions on the same underlying (TQQQ and SQQQ,
SOXL and SOXS, MUU and MUD...), so in this long-only engine buying the inverse
fund *is* the short trade. The mandate asks for 1-3 bar holds, 3-8% targets,
fast features only, and rules that make sense in both directions; the fitness
in its configs charges for an average hold over 3 bars.

```bash
python -m evotrader.cli run --config configs/quick_nasdaq.json    # TQQQ/SQQQ, SOXL/SOXS, QLD/QID since 2010
python -m evotrader.cli run --config configs/quick_names.json     # TQQQ/SQQQ, MUU/MUD, RIOX, SOXL/SOXS since 2025
python -m evotrader.cli run --config configs/quick_bigcaps.json   # 2x long/short pairs on AAPL, TSLA, AMZN, MSFT, GOOGL, NVDA
```

A genome starts trading on the first bar at which the features *it* reads
are defined, not at the 200-bar mean the slowest feature needs. That is what
makes a fund with a year of history (RIOX, MUU) tradeable in a backtest: a
rule on `rsi7` and `sma50` is live after 50 bars. Buy-and-hold is benchmarked
over the same bars the genome traded.

To add a style, append a `TradingStyle` to `STYLES` in `styles.py`.

---

## Hand-written strategies

The loop writes genomes; `evaluate` goes the other way. Put genomes in a JSON
file (a list, or `{"genomes": [...]}`, in the same shape the breeder emits)
and score them on a config's training and held-out windows, on any other
symbol set, year by year, and at any cost assumption:

```bash
python -m evotrader.cli evaluate strategies/quick_leveraged.json --config configs/quick_nasdaq.json --by-year
python -m evotrader.cli evaluate strategies/quick_leveraged.json --config configs/quick_names.json --test-frac 0 --by-year
python -m evotrader.cli evaluate strategies/quick_leveraged.json --config configs/quick_nasdaq.json --symbols TQQQ,SOXL,QLD
python -m evotrader.cli evaluate strategies/quick_leveraged.json --config configs/quick_nasdaq.json --slippage 15
python -m evotrader.cli evaluate strategies/quick_leveraged.json --config configs/quick_nasdaq.json --by-year --markdown strategies/reports/quick_nasdaq.md
```

`--test-frac 0` scores one full window. `--by-year` adds calendar-year
returns and trade counts, a per-symbol breakdown, and the best and worst
trades. The exit code is 2 when any strategy is unprofitable on any window,
so it works as a check in a script. A strategy counts as profitable on a
window when it made at least ten trades with a positive net return and a
profit factor above one.

`signals` is the daily use of a strategy file: it evaluates every entry
rule on the latest bar, as if flat, and prints the buys for the next open.

```bash
python -m evotrader.cli signals strategies/quick_leveraged.json --config configs/quick_names.json --refresh
```

`strategies/quick_leveraged.json` holds eight quick-trade strategies for
the leveraged Nasdaq, semiconductor and single-stock funds, seven bred by
hand this way and one evolved;
`strategies/README.md` is the report on them, and `strategies/reports/`
the generated per-universe tables.

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
  styles.py       trading styles: a breeder mandate plus seed archetypes
  evaluate.py     score hand-written genomes over windows, years and symbol sets
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
python -m pytest tests -q      # 96 tests, ~30s
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

* Long-only, one lot per symbol, daily bars. No shorting, no portfolio
  leverage, no options or intraday data. Leveraged ETFs are just symbols;
  `configs/leveraged_swing.json` trades them.
* Fills assume you can transact at the next open at the modelled slippage.
  Illiquid symbols will flatter themselves.
* Survivorship bias lives in your symbol list. Picking today's winners and
  evolving on their history proves nothing.
* A backtest is not a forecast. This is a research tool for generating and
  stress-testing hypotheses about strategies.
