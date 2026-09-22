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

## Installing

```bash
pip install -r requirements.txt          # numpy: engine, backtests, MCP servers
pip install -r requirements-llm.txt      # adds anthropic, for breeding with Claude
```

Python 3.9 has no `anthropic>=1.0`, which is why breeding is a separate file:
everything else runs on numpy alone, and installing it should not fail over a
dependency it never uses.

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

Fitness can be tilted toward the present: with `recent_bars` and
`recent_weight` set (the quick configs use 126 bars and 0.5), an agent's
score is a blend of its whole-window score and its score over the last
`recent_bars` bars, so what works now outranks what worked years ago.

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
python -m evotrader.cli evaluate strategies/recent_regime.json --config configs/quick_names.json --test-frac 0 --since 2026-03-22,2025-09-22
```

`--test-frac 0` scores one full window. `--by-year` adds calendar-year
returns and trade counts, a per-symbol breakdown, and the best and worst
trades. `--since` adds trailing-window rows from a date (return, trades,
profit factor, max drawdown, worst day), which is how a strategy is judged
on the last six months rather than on its whole history. The exit code is 2 when any strategy is unprofitable on any window,
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
hand this way and one evolved, and `strategies/recent_regime.json` the set
ranked by the last six months;
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

## Watching a run from Claude Code

A run is a long-lived process writing to SQLite, which makes it awkward to
follow from a terminal you also want to use. `evotrader mcp` serves the same
record over the Model Context Protocol, so a Claude Code session can watch
training as it happens and reason about what it sees:

```bash
evotrader mcp --db runs/evotrader.sqlite      # stdio, one client
```

`.mcp.json` in the repo root registers this server and the backtesting one
below, so a Claude Code session started here picks both up with no setup. For
any other MCP client:

```json
{"mcpServers": {"evotrader": {"command": "python3",
                              "args": ["-m", "evotrader.cli", "mcp"],
                              "env": {"EVOTRADER_DB": "runs/evotrader.sqlite"}}}}
```

Then ask in plain English — *how is the run going, and is the champion real?*

| tool | what it answers |
|---|---|
| `training_status` | generations done, fitness trend, champion on both windows, spend, whether the run has stalled |
| `generation_history` | best/mean/median by generation, next to the held-out score of each generation's champion |
| `leaderboard` | the best distinct strategies, ranked on training **or** held-out fitness |
| `inspect_genome` | one agent's thesis, rules, risk limits, scores and ancestry |
| `genome_trades` | the trades it actually made, best or worst first, with the rule that fired |
| `reflections` | Claude's own analysis of each generation and the lessons carried forward |
| `overfitting_report` | training against held-out fitness, and the rank correlation between them |
| `search_genomes` | which agents trade on `rsi14`, `cross_above`, or any word in a thesis |
| `strategy_language` | the feature and function vocabulary, so rules can be read correctly |
| `backtest_genome` | replay a stored agent over any window or symbol list |
| `list_runs` | every run in the database |

Two resources come with it: `evotrader://run/<id>` is the full Markdown report,
`evotrader://strategy-language` is the rule vocabulary.

The view is read-only — it cannot start, steer or stop a run, and
`backtest_genome`, the one tool that computes anything, writes nothing back.
The server speaks JSON-RPC on stdin and stdout itself, so it adds no
dependencies. It also says out loud, every time it hands over a leaderboard,
that training fitness is in-sample and the held-out window is the only evidence
there is.

## Backtesting on TradingView data

TradingView is where the chart is. `evotrader tv-mcp` is a second MCP server
that fetches bars from TradingView's own feed and backtests strategies on them
with this repo's engine, reporting the result the way a Strategy Tester does:

```bash
evotrader tv-mcp                       # stdio; bars from TradingView
evotrader tv-mcp --source yahoo        # or the cached Yahoo daily bars
```

Ask for a test in plain English, or call the tools directly:

| tool | what it does |
|---|---|
| `search_symbols` | AAPL -> `NASDAQ:AAPL`, so you pass symbols TradingView knows |
| `get_bars` | what the feed actually returned: range, bar count, the last few bars |
| `backtest` | run a strategy; net profit vs buy-and-hold, drawdown, profit factor, Sharpe, trade list |
| `compare_strategies` | two to eight strategies over identical bars, ranked |
| `walk_forward` | re-test on windows the strategy was not chosen on, fold by fold |
| `backtest_evolved_agent` | take an agent from a training run by id and test it on symbols it never evolved on |
| `screener` | scan the market for symbols matching conditions — where a list of candidates comes from |
| `quote` | last price, change and volume for a symbol |
| `technicals` | TradingView's own indicator snapshot for a symbol |
| `strategy_language` | the rule vocabulary |

A strategy is the same rule language the evolved agents use — not Pine:

```json
{"symbols": ["NASDAQ:AAPL", "NASDAQ:MSFT"],
 "entry_rules": [{"when": "rsi14 < 35 and close > sma200", "weight": 0.3}],
 "exit_rules": [{"when": "rsi14 > 60"}, {"when": "position_return < -0.08"}],
 "risk": {"stop_loss_pct": 0.08, "max_positions": 3},
 "timeframe": "1D", "bars": 2000}
```

and the answer comes back as:

```
RSI dip — NASDAQ:AAPL, NASDAQ:MSFT · 1D · 2016-12-01..2026-09-16 (2000 bars)
  net profit          +41.2%   buy & hold  +58.4%   excess -17.2%
  max drawdown        -14.9%   volatility 16.1%
  profit factor         1.38   sharpe 0.71   sortino 0.94   calmar 0.31
  trades                  46   win 61%   avg hold 14 bars
  exposure               38%   turnover 3.1x/yr   fitness +0.22

  worth noting
  buy-and-hold beat it over this window

  this window was chosen, not drawn at random — run `walk_forward` before
  treating it as evidence
```

Rules are parsed, never executed as code, so a bad rule is an error message
rather than a surprise. Fills land at the **next** bar's open with commission
and slippage charged both ways, exactly as in evolution — a strategy tested
here and an agent bred by a run are measured the same way, which is what makes
`backtest_evolved_agent` meaningful.

### Finding something to test

`screener` turns a strategy into a list worth running it on:

```json
{"filters": [{"field": "rsi", "op": "less", "value": 35},
             {"field": "market_cap", "op": "greater", "value": 50000000000},
             {"field": "close", "op": "greater", "value": 10}],
 "sort_by": "market_cap", "limit": 25}
```

```
42 matches — rsi less 35, market_cap greater 50000000000, close greater 10
  NYSE:BAC           close     57.73  change     -0.77  rsi     29.16  Bank of America Corporation
  NYSE:GE            close    314.27  change     -1.02  rsi     34.21  GE Aerospace
  ...
  a screen is a list of candidates, not signals — `backtest` them before
  believing any of it
```

Filters run over `close`, `change`, `volume`, `relative_volume`, `market_cap`,
`pe`, `rsi`, `macd`, `sma20/50/200`, `atr`, `volatility`, `perf_week/month/ytd`,
`gap` and `sector`. Results are common stock only by default — without that the
top of a large-cap screen fills with preferred shares and second listings of the
same company, which is a good way to backtest a bank's preferred stock by
accident.

These three tools use TradingView's scanner, which is a plain HTTPS endpoint —
no WebSocket, no session needed. `technicals` reports what TradingView computes;
the backtest computes its own indicators from bars and never reads them, so the
two can disagree at the edges.

### TradingView specifics

Symbol search is a plain HTTPS call. Bars arrive over the same WebSocket
protocol the charts use, implemented in `tvdata.py` — a session is opened, the
symbol resolved, a series requested, and `timescale_update` messages collected
until the server says `series_completed`. No dependency is added for either.

An anonymous session covers recent history on most symbols. To sign in:

```bash
evotrader tv-login          # prompts, hidden; verifies before it stores anything
```

Take the `sessionid` and `sessionid_sign` cookies from a browser logged in to
TradingView (DevTools → Application → Cookies). The command exchanges them for
an auth token to prove they work — a cookie that does not work is never stored
— and writes them to `~/.config/evotrader/tradingview.json`, created 0600 so
only you can read it. `evotrader tv-login --forget` removes it.

**Use the stored login, not environment variables, when an MCP client is
involved.** The client launches the server itself and inherits no shell, so
anything exported in a terminal never reaches it and the server stays anonymous
however carefully you exported it. `TRADINGVIEW_SESSION` and
`TRADINGVIEW_SESSION_SIGN` still work and take precedence where a shell is
doing the launching.

The cookie is a bearer token: whoever holds it is logged in as you until you
log out. It is never echoed to a terminal or put in an error message.

Intraday timeframes (`1`, `5`, `60`, `240`, or `1h`/`4h` aliases) need the
TradingView source; `--source yahoo` is daily only.

Check the feed before trusting a backtest:

```bash
evotrader tv-check --symbol NASDAQ:AAPL --timeframe 1D
```

```
credentials       file ~/.config/evotrader/tradingview.json (32 chars)
account           signed in (cookie exchanged for an auth token)
symbol search     ok (NASDAQ:AAPL, Pyth:AAPL, TSX:AAPL)
bars              ok (120 x 1D, 2026-03-26..2026-09-16, last close 332.41)

ready: evotrader tv-mcp
```

It says whether the account is actually signed in, which symbols resolved, how
many bars came back and how recent the newest one is. A newest bar several days
old means the account is not entitled to that symbol's data. For historical
backtesting, delayed data is not a problem: yesterday's bar is the same bar
whether you see it now or in fifteen minutes.

### How much history you actually get

`evotrader tv-depth` measures it, so the question can be settled with numbers
rather than a pricing page. Signed out, for `NASDAQ:AAPL`:

```
  tf   |   bars | from             | to               | span
  1    |  6,630 | 2026-08-24 13:30 | 2026-09-16 19:59 | 23 days
  5    |  5,070 | 2026-06-15 13:30 | 2026-09-16 19:55 | 3.1 months
  60   |  6,479 | 2023-01-03 14:30 | 2026-09-16 19:30 | 3.7 years
  1D   | 11,526 | 1980-12-12       | 2026-09-16       | 45.8 years
```

Daily and weekly come back complete — 45 years of AAPL with no account at all,
which is everything a daily backtest needs. Intraday is where the limit bites,
and it is a server-side cap rather than a paging limit: `fetch_bars` already
asks for earlier pages until the feed stops adding bars.

So run `tv-depth` signed out, set `TRADINGVIEW_SESSION`, and run it again. Rows
that do not move are limits a subscription will not lift, and buying one to fix
them will not work.

The limit is a **bar count, not a date**: AAPL and SPY return the same 5,070
five-minute bars and the same 6,479 hourly ones, and a 24/7 crypto symbol gets
the same few thousand bars spread over fewer days. So the deeper the timeframe,
the further back the same window reaches.

### Ten years of one-minute data

The pull is not the hard part — 3.5 million bars (ten years of one-minute
futures) arrives in roughly a minute and a half over the chart socket, if the
account is entitled to it. What matters is what happens either side of that:

| step | 3.5M bars |
|---|---|
| store write | 3.0s |
| store read | 2.5s, 392 MB |
| feature build | ~30s |
| **one backtest** | **~2 minutes** (29,000 bars/sec through the engine) |

So a deep intraday history is comfortable for testing a strategy and useless
for evolving one: a hundred agents over a thousand generations is a hundred
thousand backtests, which at two minutes each is not a run you can start.
Evolve on daily bars; use the minute data to examine a survivor.

The store is `.npz` rather than CSV for exactly this reason — text costs about
six seconds per million bars to parse and binary about a fifth of a second.
CSV remains the interchange format:

```bash
evotrader tv-import --file nq_1min.csv --symbol CME_MINI:NQ1! --timeframe 1
evotrader tv-export --symbol CME_MINI:NQ1! --timeframe 1D --file out.csv
```

`tv-import` matches columns by header, so another tool's export loads as long
as it has a date column and OHLC. Imports merge with what is already stored.

### Deep futures history, from expired contracts

A futures root is not one series. Every quarterly contract — NQH2016, NQM2016,
NQU2016, NQZ2016 — is its own symbol with its own window ending at its own
expiry, so pulling forty of them returns forty windows scattered through a
decade, none of which the continuous symbol will give you. The idea is
Charlie's; this is the version with the caveats instrumented.

```bash
evotrader tv-archive --root NQ --timeframe 5 --since 2015
```

```
CME_MINI:NQ#ARCHIVE 5: 81,136 bars from 18 contracts
  2023-02-20 .. 2026-09-18  ·  320 sessions of 935 weekdays  ·  34% covered
  largest hole: 73 days  ·  253.6 bars per session present
  back-adjusted across 17 rolls (14 measured on daily overlap)
  this is 34% of sessions, not a continuous history — indicators run across
  the holes will average over months that are not there
```

**It is a decade of islands, not a decade of bars.** Each contract yields
about nineteen sessions at 5-minute resolution, four or five at 1-minute, so a
sixty-three-day quarter arrives about a third covered, and the holes between
islands run to seventy days. The report says so every time rather than leaving
it to be discovered in a backtest: a strategy tested on the concatenation is
holding positions across months that are not in the data.

**Roll basis.** Contracts trade at different levels, so splicing them raw
leaves a jump at every boundary that nobody traded. Back-adjustment shifts the
older contracts onto the newest one's scale — returns become continuous,
absolute prices become fiction, which is the right bargain for testing a
strategy. `--raw-prices` keeps the jumps.

Measuring that shift needs an overlap, and the intraday windows rarely have
one: they end three months apart. Each contract's *daily* series spans its
whole life, though, so consecutive contracts overlap there by months — the
archive pulls daily bars alongside and measures the basis on those, which took
the measured rolls from 3 of 17 to 14 of 17. The three that remain are
reported, not guessed at.

### The candle store

`evotrader tv-fetch` pulls candles into `data/cache/tv` and merges them with
what is already there, keyed by timestamp:

```bash
evotrader tv-fetch --symbols NASDAQ:AAPL,AMEX:SPY --timeframes 5,15,60,240,1D
```

```
  symbol           | tf   |   bars | from             | to               | added
  NASDAQ:AAPL      | 60   |  6,479 | 2023-01-03 14:30 | 2026-09-16 19:30 | +6,479
  NASDAQ:AAPL      | 240  |  5,368 | 2016-01-04 14:30 | 2026-09-16 17:30 | +5,368
  NASDAQ:AAPL      | 1D   | 11,525 | 1980-12-12       | 2026-09-15       | +11,525
```

This is how the intraday history gets past TradingView's window. The feed
serves a rolling few thousand bars; the store keeps what rolls off the back, so
a weekly cron accumulates a 5-minute record no single request will ever return:

```cron
0 6 * * 1  cd /path/to/evotrader && evotrader tv-fetch --symbols NASDAQ:AAPL,AMEX:SPY --timeframes 1,5,15
```

Re-fetching an overlapping window adds nothing (bars are keyed by timestamp),
a bar TradingView later revises replaces the stored one, and a gap in the store
is filled by the next pull. The still-forming candle is dropped — a backtest
that fills on a bar which has not closed is trading a candle that does not
exist yet.

Backtests read the store first and only pull when a series is missing or stale,
which is what makes them fast: a three-fold walk-forward over 4,995 four-hour
bars takes about a second warm, against a minute or more cold. A cold pull of
several symbols can exceed an MCP client's tool timeout, so warm new symbols
with `tv-fetch` before backtesting a basket of them. If the feed is down, the
store answers anyway and the result says so.

Bars are taken as TradingView serves them, split-adjusted like a default chart,
whereas `data.py` gets dividend-adjusted bars from Yahoo. Two conventions —
pick one per backtest rather than comparing numbers across them.

## Using it from Claude chats (custom connector)

`.mcp.json` covers Claude Code sessions started in this repo. A Claude **custom
connector** covers everything else — chats on the web, desktop and mobile — by
pointing Claude at a remote MCP server instead of a subprocess it launches. That
needs a different transport, which `serve-http` provides:

```bash
evotrader serve-http --server both --token "$(openssl rand -hex 24)"
```

```
listening on http://127.0.0.1:8787/mcp/tradingview
listening on http://127.0.0.1:8787/mcp/training
```

Then expose it over public HTTPS — a tunnel (`cloudflared tunnel --url
http://localhost:8787`, `ngrok http 8787`) or a host with a certificate — and
add the resulting `https://…/mcp/tradingview` URL under Settings → Connectors →
Add custom connector.

What Claude requires of the other end:

* **Public HTTPS.** Claude's cloud makes the connection, so localhost, a VPN, or
  anything behind a firewall will not do. A tunnel is the quickest way to give a
  laptop a public URL.
* **Streamable HTTP**, which is what `serve-http` speaks: one endpoint per
  server taking POST, answering `202` to a notification and a single JSON object
  to a request, returning `405` to the GET stream it never pushes on, and
  refusing a protocol version it does not know.

Some sharp edges worth knowing before you point the internet at it:

* **Anyone who reaches the port can use the tools.** `--token` requires
  `Authorization: Bearer …`; where a client cannot send headers, an unguessable
  `--path` is the fallback. The server refuses to bind a public interface
  without a token at all. A request without the token gets **403, never 401**:
  in MCP a 401 means "authenticate with me over OAuth", so a client that
  receives one goes looking for an authorization server, finds nothing, and
  reports the connector as needing a sign-in that does not exist.
* **`--server both` serves the training view too**, which exposes a run's whole
  record. `--server tradingview` keeps the training database off the internet.
* **The `Origin` header is validated**, so a web page your browser happens to
  open cannot reach a server bound to localhost. `--allow-origin` permits one.
* **Data still comes from where the server runs.** The candle store and the
  training database are local to that machine, so a laptop that sleeps takes the
  connector down with it.

`GET /health` answers without credentials, which is usually the quickest way to
tell whether a tunnel is up.

## Keeping the connector up

One command does all of it — first-run setup included:

```bash
scripts/tunnel install     # once: adds `tunnel` to your shell
tunnel                     # starts everything, prints the connector URL
```

`tunnel` asks nothing. It reads `tunnel.conf` from the repo, installs anything
missing (numpy, cloudflared), creates the Cloudflare tunnel and its DNS record
if they do not exist yet, starts the server and the tunnel **detached** so
closing the terminal does not kill them, and then checks the public URL end to
end rather than assuming it works.

Settings live in `tunnel.conf` in the repo. Override them for one machine in
`~/.mcp-tunnel.conf` (or with environment variables, which win over both);
`tunnel setup` writes that file for you.

```
tunnel            start (or report that it is already up)
tunnel autostart  start at login, and re-check every 5 minutes (macOS)
tunnel stop       stop both
tunnel status     what is running, and what the public address answers
tunnel url        print the connector URL
tunnel setup      change the saved settings
tunnel logs       the last lines of the server log
```

The rest of this section is what `tunnel` is doing underneath, and how to do it
by hand.


Both processes — the server and the tunnel — have to be running for the
connector to work, and a quick tunnel invents a new URL every time it starts,
which means editing the connector again. Three ways out, in increasing order of
never thinking about it again.

**One command, new URL each time.**

```bash
scripts/mcp-up.sh          # starts both, waits, prints the URL to paste
scripts/mcp-down.sh        # stops both
```

**A permanent URL.** A *named* Cloudflare tunnel keeps one hostname forever, so
the connector URL never changes again. It needs a domain on a Cloudflare
account (the DNS side is free):

```bash
cloudflared tunnel login
cloudflared tunnel create evotrader
cloudflared tunnel route dns evotrader mcp.example.com
TUNNEL_HOSTNAME=mcp.example.com scripts/mcp-up.sh
```

The connector URL is then `https://mcp.example.com/mcp`, today and in a year.

**Someone else's machine, your domain.** Create a second tunnel and its DNS
record on the account that owns the domain:

```bash
cloudflared tunnel create partner
cloudflared tunnel route dns partner mcp2.example.com      # a different hostname
```

Send them the credentials file that prints (`~/.cloudflared/<uuid>.json`) — it
is a credential, so send it the way you would a password — and they run:

```bash
TUNNEL_HOSTNAME=mcp2.example.com TUNNEL_NAME=<uuid> \
TUNNEL_CREDENTIALS=~/.cloudflared/<uuid>.json scripts/mcp-up.sh
```

They never need your Cloudflare login. Give each machine its own tunnel and
hostname: two machines sharing one tunnel become two replicas of it, and
Cloudflare will split requests between them — different caches, different
answers, at random.

**Started for you at login.** `scripts/com.evotrader.mcp.plist` is a launchd
agent: edit the two paths, drop it in `~/Library/LaunchAgents`, `launchctl
load` it once, and both processes start at login and restart if they die.
Combined with a named tunnel there is nothing left to rerun.

### What actually takes it down

A named tunnel does not expire, and neither does its DNS record. `cloudflared`
reconnects by itself after a dropped connection or a wake from sleep. What ends
it is more mundane:

| | |
|---|---|
| reboot or shutdown | `tunnel`, or `tunnel autostart` once and never again |
| the Mac asleep | unreachable while it sleeps, back on wake |
| the domain expiring | the one calendar item — turn on auto-renew |
| deleting the tunnel or its DNS record | recreated by `tunnel` on the next run |
| a very old `cloudflared` | `brew upgrade cloudflared` once in a while |

A *quick* tunnel (`trycloudflare.com`) is the one that really is temporary — a
new hostname every run. That is what the named tunnel replaced.

None of this survives the Mac sleeping — the connector is down while the
machine is. If you want it up regardless, run the server on something that
stays awake (a small VM, Fly, Railway) and skip the tunnel entirely; the
tradeoff is that the candle store and any training runs then live there rather
than on your laptop.

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
  mcp_rpc.py      the MCP wire protocol, shared by both servers
  mcp_server.py   the training view, served over MCP
  tvdata.py       TradingView symbol search and OHLCV history
  tvcache.py      the local candle store that deepens with every fetch
  tv_mcp.py       backtesting on TradingView data, served over MCP
  mcp_http.py     Streamable HTTP transport, for a Claude custom connector
scripts/
  mcp-up.sh       start the server and tunnel, print the connector URL
  mcp-down.sh     stop them
  com.evotrader.mcp.plist   launchd agent, to start both at login
```

## Tests

```bash
python -m pytest tests -q      # 320 tests, ~80s
```

They cover the rule language (including that hostile input is rejected), the
indicators, no-look-ahead fills and risk-limit enforcement in the backtester,
fitness behaviour, the genetic operators, the full Claude breeding path against
a stubbed client, a complete run with checkpoint and resume, both MCP servers
down to the wire protocol, and the TradingView client against recorded socket
frames.

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
