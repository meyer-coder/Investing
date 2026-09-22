# Intraday NQ: first pass

FundedNext Futures trades NQ, MNQ, ES, MES and a few others, no ETFs, and
the daily-bar strategies in the parent directory do not fit its $25,000
account (see "FundedNext" in `../README.md`). This directory is the
intraday track: session rules on the Nasdaq future, tested on TradingView
bars with the repo's session features (`evotrader/sessions.py`).

## What was tested

- **Data.** `CME_MINI:NQ1!` from the TradingView feed through the local
  store (`data/cache/tv`, filled by `evotrader tv-fetch`). Without a
  TradingView login the feed's depth is one month of 5-minute bars (6,033),
  twelve weeks of 15-minute bars (5,491) and 21 months of hourly bars
  (10,173, since January 2025). Stamps are UTC; the session features
  convert to New York: RTH flags, minutes since the 09:30 open, a
  midnight-anchored session VWAP, the 60-minute opening range.
- **Engine.** Long-only. Decide on a bar's close, fill at the next bar's
  open. Costs 0.2 bp commission and 0.8 bp slippage per side, about six NQ
  points a round trip at 31,000, three times what an MNQ trade costs.
- **Sizing.** Weight 1.0 is 100% of equity in index notional, about 0.4
  MNQ per $25,000 at NQ 31,000; one MNQ is 2.5 times the account. Results
  are in NQ points; points times $2 is dollars per MNQ, times $20 per NQ.
- **Rules.** `nq_candidates_5m.json`, `nq_candidates_15m.json` and
  `nq_candidates_60m.json`, run by `run_study.py`, plus parameter grids
  over each family (VWAP reclaim, capitulation bar, opening-range
  breakout, power-hour dip and its mirror, red morning hour, morning
  stretch under VWAP, z-score dip, last-hour reversal and its mirror).

## Results

Hourly bars, January 2025 to 22 September 2026, 539 sessions, from
`run_study.py 60`. "Per session" includes flat sessions.

| strategy | trades | win | PF | avg trade | per session | best session | worst session | since 22 Mar 2026 |
|---|---|---|---|---|---|---|---|---|
| Red morning hour, hold to 15:00 | 66 | 56% | 1.90 | +53 pts | +6.5 pts | +1,650 | -551 | about -125 pts, 12 trades |
| Morning stretch under VWAP | 64 | 56% | 1.30 | +16 pts | +1.9 pts | +335 | -551 | -291 pts, 12 trades |
| Last-hour reversal after a red 14:00 hour | 38 | 55% | 1.48 | +18 pts | +1.3 pts | +491 | -285 | +113 pts, 12 trades |
| Last hour under VWAP | 154 | 56% | 1.14 | +5 pts | +1.4 pts | +262 | -285 | +503 pts, 45 trades |
| Midday z-score dip | 74 | 53% | 1.15 | +6 pts | +0.8 pts | +356 | -372 | -67 pts |
| Last hour above VWAP (the mirror) | 248 | 45% | 0.76 | -8 pts | -3.7 pts | +491 | -724 | -499 pts, 75 trades |

What the grids add:

- *Red morning hour* (buy after a 10:00, 11:00 or 12:00 hour down 0.4% to
  0.8%, hold to 15:00): all 18 parameter combinations are profitable over
  the 21 months, eight with PF above 1.3. April 2025 alone is +1,845 of its
  +3,493 points, and since 22 March 2026 the combinations run from -454 to
  +583 points, mostly negative. A crash-regime rule, not a current one.
- *Last-hour reversal* (buy the 15:00 open when the 14:00 hour was red, or
  when the index is under the day's VWAP; sell at the 16:00 open): every
  red-hour combination is profitable (PF 1.33 to 1.48 on 38 to 72 trades),
  the under-VWAP version is 12 of 24 above PF 1 and none above 1.3, and
  the mirror (above VWAP at 15:00) loses in all 9 combinations, PF 0.72 to
  0.76. The asymmetry looks real. The size does not: 5 to 18 points a
  trade.
- *15-minute bars, twelve weeks.* VWAP reclaim: 5 of 48 combinations above
  PF 1, none above 1.3. Capitulation bar: 0 of 8. Opening-range breakout:
  0 of 8, 18% to 25% winners. Power-hour dip (under VWAP after 15:00, first
  up bar, flat by 16:00): 6 of 6 above PF 1, 1.27 to 1.60, on 10 to 20
  trades, +68 to +151 points in total; the same rule on the month of
  5-minute bars is 7 trades at PF 0.64. Power-hour pullback above VWAP: 0
  of 6, PF 0.12 to 0.33.

## Verdict

Nothing here is tradeable on a $25,000 FundedNext account.

- The best-evidenced pattern, the last-hour reversal of a red afternoon,
  is worth 5 to 18 NQ points a trade, $10 to $36 per MNQ, one to seven
  trades a month. At one MNQ that is roughly $30 to $65 a month against a
  $1,250 target. To matter it needs five or more MNQ, and at five the
  ordinary worst session, -285 points, is -$2,850 against a $1,000
  trailing drawdown.
- The red morning hour earns more per trade, +53 points, but has been flat
  to negative for six months, and its worst session, -551 points, is
  -$1,100 per single MNQ, past the drawdown on its own.
- Costs are not the problem. At the real MNQ cost, about two points a round
  trip instead of six, the per-trade figures rise by four points and the
  verdict does not move.

The daily-bar strategies in the parent directory make +3% to +5% a trade
on the leveraged funds; these intraday rules make 0.02% to 0.06% of the
index. The edge that exists in this data is in the ETF book on a brokerage
account, not in a $25,000 NQ account.

## What would change the picture

1. **Depth.** With a TradingView login (`TRADINGVIEW_SESSION`, the
   `sessionid` cookie) the feed serves years of 5- and 15-minute bars:
   `python -m evotrader.cli tv-fetch --symbols CME_MINI:NQ1! --timeframes 5,15 --bars 60000 --timeout 900`.
   Then re-run the grids over the last six months alone, with at least 100
   trades per candidate.
2. **The short side.** NQ sells off faster than it rallies, and the mirror
   test says buying above VWAP into the close loses, which is a short
   signal of about 8 points a trade before costs. The engine is long-only;
   a short leg is the next engine change if this track continues.
3. **One-minute bars for the last hour**, where the effect lives, to
   sharpen the 15:00 entry and the 16:00 exit.
4. **The evidence bar** before a single paper trade: at least 100 trades,
   PF above 1.3 at these costs, profitable in both halves of the window,
   the mirror side negative, and the worst session under 40% of the
   trailing drawdown at the intended size.
5. **Paper first.** A Pine port with alerts, as in `../pine/`, on a
   TradingView paper account at one MNQ for four weeks, before any funded
   attempt.

## Reproduce

```bash
python -m evotrader.cli tv-fetch --symbols CME_MINI:NQ1! --timeframes 5,15,60 --bars 40000 --timeout 300
python strategies/intraday/run_study.py 60 15 5
```

Timing notes. Hourly bars start on the hour, so `minute_of_day == 840` is
the 14:00 bar; the decision is taken at its 15:00 close and fills at the
15:00 bar's open, and the `minute_of_day >= 900` exit is decided at the
15:00 bar's 16:00 close and fills at the 16:00 bar's open. On 15-minute
bars the same trade is `minute_of_day == 885` in and `>= 945` out; on
5-minute bars, `>= 955`. The session count in `run_study.py` is calendar
dates with bars, Sunday evening Globex opens included.
