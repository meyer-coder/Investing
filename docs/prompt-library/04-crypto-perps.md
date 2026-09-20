# Crypto perpetual futures — momentum, funding carry, liquidation fade

**Why this is the #1 market for an agent fleet, and why you should build here
first:** the data problem that cripples every other brief in this library does
not exist. Binance, Bybit and OKX serve complete historical klines back to
listing — free, no key, no rate-limit worth mentioning, no 1000-bar cap, with
explicit `startTime`/`endTime` pagination. You can pull **eight years of
1-minute BTC data in a few minutes** and aggregate to any resolution.

Compare with NQ, where the primary source in your original prompt yields 3.6
days. Here you get the full study, immediately, for free.

Everything else compounds it: 24/7 (no session gaps, no roll, no expiry), native
shorting, deep leverage, and two signals that exist in no other market — the
**funding rate** (a directly observable crowd-positioning gauge, printed every
8 hours) and **liquidation cascades** (forced, mechanical, non-informational
selling — the cleanest reversion setup in any market).

Build your pipeline here. Debug variant search, walk-forward and reporting
against free complete data. Then port the machinery to markets where data costs
money.

---

```
## 1. ROLE
Quantitative researcher specialising in crypto microstructure and intraday
systematic strategies. I am not a quant — plain language, define terms on first
use. Do not ask clarifying questions; resolve ambiguity with the most defensible
reading, state the assumption, continue. Report failures as prominently as wins.

## 2. INSTRUMENT
Primary:   BYBIT:BTCUSDT.P and BINANCE:BTCUSDT.P (USDT-margined perpetual swaps)
Secondary: ETHUSDT.P, SOLUSDT.P
No expiry, no roll, no settlement. Price is tethered to spot by the funding
mechanism, not by delivery — understand and model that before anything else.
Funding: paid every 8h (00:00 / 08:00 / 16:00 UTC) on most venues. Positive
funding = longs pay shorts. A position held across a funding timestamp pays or
receives it. THIS IS A REAL P&L LINE, NOT A ROUNDING ERROR: sustained funding of
0.01% per 8h is ~11% annualised. Any strategy holding directional positions for
hours must account for it, and ignoring it has sunk many published crypto
backtests.

## 3. DATA (the easy part — exploit it)
Target: 5+ years of 5m bars. This is trivially achievable, so accept nothing less.
  1. Binance public REST `/fapi/v1/klines` — free, no key, 1500 bars/request,
     with startTime/endTime pagination. Loop it. BTCUSDT perp lists from
     Sept 2019; spot from 2017.
  2. Bybit `/v5/market/kline` as a cross-check on a different venue. Comparing
     two venues is a free data-quality audit — material divergence means one
     feed has a problem.
  3. Funding rate history: Binance `/fapi/v1/fundingRate` — free, full history.
     Pull it and join it onto the bars. It is a FEATURE, not just a cost.
  4. Open interest: `/futures/data/openInterestHist` (~30 days only — note the
     limit and design around it).
  5. Liquidation data where obtainable; otherwise proxy a cascade as
     (volume > 5x its 20-period average) AND (range > 3x ATR) in a single bar.
  6. TradingView MCP `bars` for spot-checks only (1000-candle cap, no date range).
Still print a data inventory before testing: first/last bar, count, gaps,
duplicate timestamps, zero-volume bars, exchange downtime windows, and the
dates of any venue outage. Crypto exchanges do go down, and the resulting gaps
look like tradeable moves if you do not flag them.

## 4. CLOCK
5m bars, UTC throughout. 24/7 — but DO NOT assume time-of-day is irrelevant.
Tag each bar with UTC hour and with the regional session it falls in:
  Asia 00:00-08:00 | Europe 07:00-16:00 | US 13:00-22:00 UTC
Tag day of week INCLUDING weekends. Weekend crypto is a distinct regime —
thinner books, lower volume, and historically different behaviour. Test it as
its own bucket rather than pooling it with weekdays.
Tag funding timestamps and minutes-to-next-funding.

## 5. COST MODEL (mandatory)
Taker 0.055%, maker 0.02% (verify against your venue's current fee tier).
A taker-in/taker-out round trip is ~0.11% of notional. On a $100k position that
is $110 per round trip. This is FAR more expensive than futures relative to
typical move size — model it precisely or your results are fiction.
Slippage: 1 bp on BTC in normal conditions; 5 bp during a volume spike > 5x
average; 15 bp during a liquidation cascade bar.
Funding: charge or credit actual historical funding for every position held
across a funding timestamp. Not an estimate — the real printed rate.
Report gross, net-of-fees, and net-of-fees-and-funding as three separate curves.
The gap between them is frequently the whole result.

## 6. BASELINE
<<PASTE STRATEGY SPEC.>>
If none, use this control: long when 5m close > EMA(50) and EMA(50) slope > 0
and relative volume > 1.5; stop 1.5 x ATR(14); target 3R; time stop 48 bars.

## 7. VARIANT SPACE — 500 variants
Three distinct strategy families — allocate roughly 170 variants to each, and
report them as three separate populations rather than one pooled ranking:

  FAMILY A — MOMENTUM / TREND CONTINUATION
  EMA 9/21/50/200 combinations; breakout of N-bar high/low (N = 12/24/48/96);
  higher-timeframe (1h/4h) trend agreement; relative volume confirmation;
  ATR-percentile regime gate.

  FAMILY B — FUNDING CARRY AND POSITIONING
  Funding rate level, sign, percentile, and rate-of-change as entry filters.
  Hypothesis worth testing properly: extreme positive funding marks crowded
  longs and precedes downside. Test funding-extreme fades, funding-sign trend
  alignment, and funding-momentum divergence against price. Also test the pure
  carry trade (hold the side that RECEIVES funding) as its own variant — it is
  a genuinely different return stream and belongs in a fleet.

  FAMILY C — LIQUIDATION CASCADE FADE
  Detect a cascade bar (volume > 3/5/8x average AND range > 2/3/4x ATR), then
  fade the move: enter at cascade+1/+2/+3 bars, target the pre-cascade level or
  a fraction of the cascade range, stop beyond the extreme. Vary the required
  wick-to-body ratio. This is mechanical, forced selling with no information
  content — the structurally cleanest reversion premise available anywhere.

  CROSS-CUTTING: UTC hour (all 24); weekday vs weekend; minutes-to-funding;
  BTC vs ETH vs SOL (does an edge generalise across assets, or is it one asset's
  noise?); long-only / short-only / both; risk parameters as in other briefs.

## 8. VALIDATION (non-negotiable, and harder here than it looks)
Train 50% / validation 25% / LOCKED TEST 25%, chronological.
Walk-forward 12mo fit / 3mo OOS, concatenated — the headline curve.
Deflated Sharpe adjusted for trial count; Benjamini-Hochberg FDR.
Full distribution of all 500, split by family.
1000 Monte Carlo trade-order shuffles on the top 5.
Parameter sensitivity +/-1 step with surfaces.
CRYPTO-SPECIFIC AND IMPORTANT:
  - BTC rose enormously over any multi-year sample. A long-biased variant may
    simply be levered beta. Benchmark EVERY variant against buy-and-hold over
    the identical window and report EXCESS return. A variant that cannot beat
    holding spot is not a strategy.
  - Regime-split explicitly: 2021 bull / 2022 bear / 2023-24 recovery / 2025+.
    An edge present in only one regime is a regime bet, not an edge. Show all.
  - Cross-asset validation: fit on BTC, test unchanged on ETH and SOL. Surviving
    that transfer is stronger evidence than any in-sample statistic.
  - Cross-venue validation: re-run the top 5 on the other exchange's data. A
    result that appears on Binance and not Bybit is a data artifact.

## 9. SLICING
UTC hour (all 24, counts shown, < 30 suppressed); day of week including
weekends; month; year over year; realized-vol decile; funding-rate decile;
relative-volume decile.
Named events (Mar 2020 COVID, May 2021 China ban, Nov 2022 FTX, Jan 2024 ETF
approval, and any others you identify from the volume data) as an explicitly
underpowered secondary check with n stated.

## 10. RANKING
Walk-forward net profit factor AFTER fees and funding, subject to max drawdown
< 25% and >= 150 trades, AND positive excess return vs buy-and-hold.
Secondary: net PnL, Sharpe, Sortino, MAR, Calmar, expectancy in bps and dollars,
win rate, avg win/avg loss, longest losing streak, total funding paid/received.
Tie-break toward variants that survive cross-asset and cross-venue transfer.

## 11. DELIVERABLES
PDF; self-contained interactive HTML dashboard; 500-variant spaghetti PnL chart
with median and 25/75 bands, top 5 highlighted, buy-and-hold overlaid as the
benchmark, and the three families colour-coded; per-variant CSV; trade logs;
plus a chart of funding rate against strategy PnL over time.

## 12. HONESTY
Lead with what failed and what the data could not answer. All assumptions in one
place. Flag suspected overfits even if they rank first. State plainly whenever a
variant's apparent edge is buy-and-hold in disguise. Nothing is tradeable on a
backtest alone.
```
