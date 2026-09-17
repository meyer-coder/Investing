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
  mcp_rpc.py      the MCP wire protocol, shared by both servers
  mcp_server.py   the training view, served over MCP
  tvdata.py       TradingView symbol search and OHLCV history
  tvcache.py      the local candle store that deepens with every fetch
  tv_mcp.py       backtesting on TradingView data, served over MCP
```

## Tests

```bash
python -m pytest tests -q      # 215 tests, ~35s
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

* Long-only, one lot per symbol, daily bars. No shorting, leverage, options or
  intraday data.
* Fills assume you can transact at the next open at the modelled slippage.
  Illiquid symbols will flatter themselves.
* Survivorship bias lives in your symbol list. Picking today's winners and
  evolving on their history proves nothing.
* A backtest is not a forecast. This is a research tool for generating and
  stress-testing hypotheses about strategies.
