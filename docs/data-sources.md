# Data sources for intraday backtesting

Verified September 2026. Free-tier terms change often — re-check before relying
on any of this. Where a figure could not be confirmed, that is stated.

The question driving this list: **what actually gets you ten years of 5-minute
NQ data**, since the TradingView tunnel cannot (1000-bar hard cap, no date
range — see `prompt-anatomy.md` §3).

---

## FREE ONLY — ranked by how much of the problem each one actually solves

Everything in this section costs nothing. Ranked by usefulness for intraday
strategy research, not by how well known it is.

### 1. Kaggle: NQ 1-minute, Dec 2022 - Dec 2025  *(the single biggest unlock)*
`kaggle.com/datasets/tgtanalytics/nq-futures-1min-bar-2022-2025`
Reported as ~1.05 million rows of 1-minute OHLCV covering **2022-12-26 to
2025-12-11**, including **both regular and extended hours**. Aggregating to 5m
gives ~207,000 bars — roughly **three years**, against the four days the
TradingView tunnel serves.
Also: `kaggle.com/datasets/youneseloiarm/nasdaq-cme-future-nq` (multi-timeframe NQ).
*NOT verified directly — kaggle.com is blocked by this environment's egress
proxy.* Check row count, date range and whether the series is roll-adjusted
before trusting it, and validate it against the TradingView tunnel's daily bars,
which overlap this window and make a free cross-check.

What three years of 5m NQ does and does not support:

| Analysis | Supported? |
|---|---|
| Hour-of-day buckets (9-10am vs 10-11am, all 23 hours) | **Yes** — ~750 samples per bucket |
| 500-variant sweep with walk-forward validation | **Yes** |
| Day-of-week effects | **Yes** |
| Month-of-year seasonality | Weak — only 3 observations per month |
| Year-over-year stability | Weak — 3 years |
| Event studies (COVID, 2022 hikes) | **No** — window starts after them |

### 2. Crypto exchange APIs — free AND complete, the best data anywhere
No key, no cap that matters, and **real `startTime`/`endTime` pagination** —
the thing the TradingView tunnel lacks.
- Binance `/fapi/v1/klines` (perps), `/api/v3/klines` (spot), `/fapi/v1/fundingRate`
- Bybit `/v5/market/kline`, plus OKX / Kraken / Coinbase public REST
- CryptoDataDownload — bulk CSV dumps
Full history to listing (BTC perp Sept 2019, spot 2017). Loop the endpoint, get
everything. No other market gives you this.

### 3. FX — free and genuinely deep
- **Dukascopy** — tick-by-tick with **real bid/ask**, free, back many years, via
  their Historical Data Export tool. Real bid/ask means you can *measure*
  historical spread rather than assume it, which is the difference between a
  credible FX backtest and a worthless one.
- **HistData.com** — 1-minute OHLC per pair per month, back to ~2000.
- **TrueFX** — tick with millisecond timestamps and fractional pips.
- **`github.com/philipperemy/FX-1-Minute-Data`** — HistData packaged with a
  simple API, and it covers **crude oil and stock indexes** as well as FX.
- Helper tools: Tickstory, ForexSB (pre-compiled clean bars from Dukascopy ticks).

### 4. Polygon.io free tier — best free equities option
5 calls/min, **2 years of history, up to 50,000 bars per call**. 50k bars is a
full year of 5-minute data for one ticker in a single request. Genuinely strong.
Caveat: delisted tickers and options sit behind the paid tier.

### 5. Databento $125 signup credit — free to start
Not a free tier, but $125 of free credit (expires 6 months). A single symbol's
`ohlcv-1m` is a small request under their volume billing, so the credit may
cover NQ for the full window outright. Price the exact query in their estimator
before paying anything.

### 6. Alpaca — free with an account
Free IEX feed for equities; full SIP feed is paid. Fine for daily and for
recent intraday.

### 7. Yahoo Finance (`yfinance`) — free, but know the limit
Unlimited daily history, and it carries futures continuations (`NQ=F`). But
intraday is capped at roughly **60 days at 5m**. Fine for daily work, useless
for intraday research.

### What free does NOT get you
- **Ten years of 5m futures.** Free tops out around three years (Kaggle). The
  full decade needs FirstRate or Databento.
- **Delisted equity tickers.** Paid only — which makes the small-cap gap brief
  unrunnable on free data without severe survivorship bias.
- **Options chains.** No credible free source. Do not approximate from the
  underlying and present it as evidence.

### The free-only build order
Crypto (complete) -> FX (deep, free) -> Kaggle NQ (3 years, your instrument)
-> Polygon equities (2 years). That covers four of the eight briefs in
`prompt-library/` at zero cost.

---

## CME futures (NQ, ES, CL, GC) — the hard one

| Source | Cost | History | Verdict |
|---|---|---|---|
| **FirstRate Data** | One-time purchase | NQ 1-min continuous from **2-Jan-2008** (~18y) | **Best value candidate** |
| **Databento** | $125 free credit, then pay-as-you-go; $179/mo Standard CME plan | Full GLBX.MDP3 | Best for precision and live continuity |
| Interactive Brokers | Free with account | **Expired futures >2 years unavailable** | **Ruled out** for this use case |
| CME DataMine | Paid, some free samples | Full | Authoritative, awkward to work with |
| Tick Data / Portara | Institutional pricing | Full | Overkill |

**FirstRate Data** is the strongest fit for this specific problem, for a reason
beyond price: it ships **pre-adjusted continuous contracts** in three flavours —
unadjusted, absolute-adjusted, and ratio-adjusted. Contract roll handling is one
of the top modelling errors in futures backtests (NQ rolls quarterly, CL
*monthly*), and this removes it as a source of bugs. Timeframes included: 1-min,
5-min, 30-min, 1-hour, 1-day.
*Pricing not verified* — the site is blocked by this environment's egress proxy.
One dated forum reference mentions ~EUR200 for a 70-contract bundle since 2006;
treat that as indicative only and check the current bundle page.

**Databento** gives $125 in free credit on signup, expiring 6 months later.
Pull `ohlcv-1m` and aggregate to 5m yourself so you control bar boundaries. A
single symbol's 1-minute OHLCV is a small request by their volume-based billing,
so the free credit may cover NQ alone for the full window — worth pricing the
exact query in their cost estimator before paying for anything.

**Interactive Brokers is not viable here.** Expired futures data older than two
years from the contract's expiration is not served through the API, so a
ten-year continuous series cannot be assembled. Fine for ~2 years, equities and FX.

---

## Crypto — free, complete, no caveats

The only market where the full dataset is simply given away.

| Source | Endpoint | Notes |
|---|---|---|
| **Binance** | `/fapi/v1/klines` (perps), `/api/v3/klines` (spot) | No key, ~1000-1500 bars/request, **real `startTime`/`endTime` pagination**, history back to listing (BTC perp Sept 2019, spot 2017) |
| Binance funding | `/fapi/v1/fundingRate` | Full history — a signal, not just a cost |
| Bybit | `/v5/market/kline` | Second venue = free data-quality audit |
| OKX, Kraken, Coinbase | public REST | Further cross-checks |

Pagination is the thing the TradingView tunnel lacks and these have. Loop the
endpoint and you get everything. **Build here first** — debug the whole pipeline
against free complete data before spending anything.

---

## FX — free and genuinely deep

| Source | Cost | History |
|---|---|---|
| **HistData.com** | Free | 1-minute OHLC per pair per month, back to ~2000 |
| **Dukascopy** | Free | Tick data with **real bid/ask**, back to ~2003 |
| OANDA API | Free practice account | Good recent history |

Dukascopy's real bid/ask matters more than it sounds: FX spread is
time-of-day dependent, and a backtest that assumes London-overlap spreads during
Asian hours is fiction. Dukascopy lets you *measure* historical spread instead
of guessing it.

---

## US equities and ETFs

| Source | Free tier | Notes |
|---|---|---|
| **Polygon.io** | 5 calls/min, **2 years history, 50,000 bars per call** | 50k bars = a full year of 5m for one ticker in ONE request. Strong free tier |
| Polygon paid | from ~$29/mo | Unlocks longer history, delisted tickers, options, tick data |
| Alpaca | Free with account | IEX feed free, full SIP feed paid |
| Tiingo | Cheap | Good intraday coverage |
| Yahoo Finance | Free | **Only ~60 days at 5m** — fine for daily, useless for intraday research |
| Alpha Vantage | 25 req/day, 5/min | **The `month` parameter for deep intraday is now PAID-GATED.** Free tier gives ~30 days intraday at most. Do not plan around it |

**Survivorship warning:** delisted tickers sit behind Polygon's paid tier. For
the small-cap gap strategy (`prompt-library/07-smallcap-gap.md`) that is not
optional — a universe missing the companies that went to zero will inflate
long-side results badly. Budget for the paid tier or run a different brief.

---

## Options (SPX 0DTE)

No good free source exists. Be honest about this rather than approximating.

| Source | Notes |
|---|---|
| CBOE DataShop | Authoritative, paid, per-day intraday chain snapshots |
| ThetaData | Options-focused, reasonable pricing, popular for 0DTE research |
| ORATS | Paid, good historical IV surfaces |
| Polygon options | Paid tier |

Reconstructing option prices from the underlying plus VIX is a feasibility
screen, not evidence — it understates skew and, critically, the bid/ask spread
where most of the real cost lives.

---

## Recommended sequence

Spending money on data before the backtester works is premature. Order the work
so the free sources carry the build:

1. **Crypto (free).** Complete history, real pagination, no roll logic, 24/7.
   Build and debug the whole pipeline here — acquisition, variant sweep,
   walk-forward, reporting — at zero data cost.
2. **FX (free).** Adds session structure and spread modelling on top of a
   pipeline you already trust. Still free.
3. **Equities (free tier).** Polygon's 2 years covers a real study. Adds
   cross-sectional work.
4. **Futures (paid).** Only now buy FirstRate or spend Databento credit. By this
   point the machinery is proven and the data is the only new variable.
5. **Options (paid).** Last — needs everything above.

---

## Sources

- https://databento.com/pricing
- https://databento.com/datasets/GLBX.MDP3
- https://firstratedata.com/i/futures/NQ
- https://firstratedata.com/bundle/all
- https://interactivebrokers.github.io/tws-api/historical_limitations.html
- https://polygon.io/
- https://www.alphavantage.co/documentation/
