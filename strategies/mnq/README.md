# MNQ short-term research: what was tested, and why there is no bot yet

As of 2026-09-24. The ask: a Micro E-mini Nasdaq-100 (MNQ) bot with short
holds (10 seconds to 10 minutes), flat by the close, making $150+ a day
reliably, for a Topstep 100K account ($3,000 maximum loss limit, up to 100
MNQ). Everything below is net of a realistic MNQ cost (1.25 index points a
round trip, a tick of slippage each way plus commission) unless noted, on
data the setups were not chosen on.

## Bottom line

Nothing tested has an edge big enough to trade. NQ's price path alone, from
10 seconds to 10 minutes, carries no direction that pays MNQ's cost in 2020
to 2026. The one effect that held up is small and rare (below). Do not buy
an account to run any of these.

| What | Data | Result |
| --- | --- | --- |
| 1,074 five-to-ten-minute setups, long and short with mirrors (`edges.py`) | Dukascopy Nasdaq-100 minutes, 1,504 sessions, Sep 2020 - Sep 2026; chosen on 2020-2023, tested on 2024-2026 | 7 held in both periods, all one effect: at 15:00, go with a day already up or down 0.5-1% for 7-10 minutes. About +3 bp (~$18 per MNQ) a trade in 2024-2026, on one day in five |
| The same on 199 real NQ futures sessions, 2016-2026 (`nq_events.py` islands) | TradingView expired contracts | A midday dip-buy looked strong here; on six years of data it nets about zero |
| Close momentum, 15:30-15:50 (`closing.py`) | 1,504 sessions | Worked 2020-2022, loses 2-4 bp a trade since 2023 |
| A LightGBM model on 27 minute-level features (`model.py`) | 542,174 minutes; fit 2020-2022, threshold picked on 2023, judged on 2024-2026 | Its call correlates 0.006 with the next 10 minutes; +0.03 bp a trade at the picked threshold |
| Breakouts with resting stops and targets (`brackets.py`) | 1,504 sessions | Nothing holds in both periods; the winners hold 30-45 minutes and fade in 2024-2026 |
| 08:30 data releases (`releases.py`) | 1,564 weekdays with pre-market minutes | +1 to +4 bp going with a big release move, 50-80 days a period, t below 1.2 |
| 10-30 second bursts, go with or fade, 10 s to 2 min holds (`bursts.py`) | Dukascopy 10-second bars, 1,048 days, Sep 2022 - Sep 2026 | 0 of 492 setups positive in both halves; the median setup makes 0.0 points before costs |
| The burst bot, incl. a 15-point stop with a 3:1 target (`burstbot.py`) | 1,008 sessions of 10-second bars | -$2.3 to +$2.7 a day per MNQ; at 5 MNQ, 60-87% of Topstep 100K Combines breach |
| Wait for the bounce: small target, no stop, big size (`bounce.py`) | 1,504 sessions | Long, +0.15% target: 84% of trades win (+42 pts) but losers average -222 pts; at 10 MNQ the median day is +$475, the average day -$166, the worst -$29,730, and 90% of Topstep 100K Combines breach. Shorter targets and shorts do worse |
| Round QQQ strikes as levels, fade or break the first touch (`strikes.py`) | 1,504 sessions | Target hit 23-27% with a 1:3 bracket, the same as prices halfway between strikes: round numbers alone are not levels |
| Filters to raise the win rate at levels: calm or wild day, time, expiry Friday, approach speed, extension, a rejection candle (`winrate.py`) | 7,181 strike touches | Almost all within 2 points of break-even; one narrow cell (calm day, after 14:00, go with the break) cleared it on 31 trades |
| Its general form: on a quiet day, go with the first break of the day's range after 14:00 (`calmbreak.py`) | 1,504 sessions | Positive in both periods at all four stop/target pairs (61% wins at 1:1 against 52% needed), fading it loses; but only 66 trades in six years (t about 1-1.7). Added to the paper trail with its settings fixed |

## Why a no-edge bot still shows $150 days

At 5 MNQ the burst bot, which has no edge, still made $150 or more on 26-34%
of days, while 63-87% of simulated Topstep 100K Combines hit the $3,000
limit. Size makes big days common whether or not there is an edge; the
account's survival is what an edge buys. A posted +$905 trade on 10 MNQ is
a 45-point (0.15%) move at $20 a point; the same position loses $20 a point
the other way.

## What is left

- **Options-derived levels** (dealer gamma exposure, the gamma flip, call
  and put walls, max pain), which the trader in the screenshot uses. CBOE's
  free delayed chains (`cdn.cboe.com/api/global/delayed_quotes/options/QQQ.json`,
  with open interest and gamma) allow computing them each morning, but there
  is no free history, so the method can only be tested forward.
- **Order flow** (trades by aggressor, top of book): paid (Databento, $125
  free credit to start). Research says its predictive power fades within a
  minute.
- **Stocks**: the Own-Drop Scalper (`profitable-strategies/scalping/own-drop/`)
  has a short-term edge in single stocks; Topstep allows futures only.

## Files

`duka.py` (data), `data.py` (sessions), `edges.py`, `closing.py`,
`releases.py`, `model.py`, `brackets.py`, `bursts.py`, `burstbot.py`
(studies), `sim.py` (MNQ simulator, tested in `tests/test_mnq_sim.py`),
`account.py` (Topstep 100K replay). Results in the `.json` files beside them.
