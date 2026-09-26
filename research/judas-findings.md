# Judas swing fade on the Nasdaq-100 (1-minute, all sessions)

Run with `python research/judas.py`. Numbers are from 2026-09-25, after
the close.

## What was tested

**What a Judas swing is.** A false move at the start of a session: price
runs past the previous session's high or low, trips the stops there, then
turns back. The fade trades the turn.

**Sessions.** Each session fades a sweep of the session before it. Times
are New York time:

| Session | Entry window | Range it fades | Flat by |
|---|---|---|---|
| Asia | 20:00-00:00 | that day's New York session, 09:30-16:00 | 02:00 |
| London | 02:00-05:00 | the Asian session before it, 20:00-00:00 | 09:25 |
| New York | 09:30-11:00 | that morning's London session, 02:00-05:00 | 15:55 |

**Rules.** They were written down before any result was seen:
1. **Sweep:** the first 1-minute bar in the window that trades beyond the
   range's high or low.
2. **Reclaim:** a 1-minute close back inside the range, within 15 minutes of
   the sweep.
3. **Entry:** the other way, at the next minute's open.
4. **Stop:** one tick beyond the furthest point of the sweep.
5. **Target:** two versions, either the other side of the range or twice
   the stop distance (2R). If neither is hit, out at the flat time.
6. **Limit:** at most one trade a session, so up to three a day.

That gives eight versions: each session alone and all three together, for
each target.

**Costs.** One MNQ: the $1.22 commission plus a tick of slippage each way.
Results are also shown with two ticks each way, because the overnight
sessions are thinner.

**Protocol.** The same as the 13-market search:
1. **Search, 2013-2019.** A version passes with 100+ trades, a positive
   mean and t ≥ 2.
2. **Confirm, 2020-2022.** Still positive, and beats 90% of random sign
   flips.
3. **Final look, 2023-2026.** Looked at once.

**Data.** Dukascopy's one-minute Nasdaq-100 CFD. It has no Asian hours for
most of 2015-2017, so those Asian sessions are skipped.

## Result: no version passes

Each cell shows bp a trade after costs, then t, then dollars a day at
1 MNQ.

| Version | Trades | Median stop | 2013-2019 (search) | 2020-2022 (confirm) | 2023-2026 (final) |
|---|---|---|---|---|---|
| Asia, range target | 402 | 14 pts | +0.62 bp, t 0.5, $0 | +2.22, t 0.9, $2 | +1.16, t 0.9, $1 |
| London, range target | 1,464 | 11 pts | +0.56, t 1.0, $1 | −0.93, t −1.0, −$3 | −0.06, t −0.1, $0 |
| New York, range target | 1,999 | 40 pts | +0.33, t 0.4, $1 | +0.09, t 0.0, $0 | +0.53, t 0.4, $2 |
| All sessions, range target | 3,865 | 21 pts | +0.42, t 0.8, $2 | −0.09, t −0.1, −$1 | +0.34, t 0.5, $3 |
| Asia, 2R | 402 | 14 pts | −0.14, t −0.2, $0 | +0.72, t 0.6, $1 | +0.85, t 0.8, $1 |
| London, 2R | 1,464 | 11 pts | −0.25, t −0.7, $0 | −0.64, t −1.0, −$2 | −0.27, t −0.6, −$1 |
| New York, 2R | 2,001 | 40 pts | −0.10, t −0.1, $0 | −1.67, t −0.8, −$6 | +2.34, t 1.6, $8 |
| All sessions, 2R | 3,867 | 21 pts | −0.15, t −0.3, −$1 | −0.93, t −1.0, −$8 | +1.02, t 1.5, $8 |

Median stops are in points at today's price.

**What it says:**
- **None of the eight versions passed the search.** None has a result that
  stands out from zero (|t| < 2) in any period.
- **The results are close to break-even after costs.** They swing between
  small gains and small losses from period to period, which is what a trade
  with no edge looks like.
- **The New York 2R version made $8 a day in 2023-2026, but lost $6 a day
  in 2020-2022.** With t = 1.6, one good stretch is not an edge.
- **The range target wins rarely.** Only 12-34% of trades win, because the
  other side of the range is far away. A few big winners pay for many small
  losses, and the total comes out near zero.

## What it means

The Judas swing fade on Nasdaq 1-minute has no edge, in any session. This
matches the earlier tests of the same idea in other forms:
- the failed-breakout and failed-breakdown setups
  ([three-setups-findings.md](three-setups-findings.md));
- the branch's liquidity-sweep study.

Fading sweeps doesn't pay on NQ. Following breakouts does: that is Bot A
([bot-a-accounts-findings.md](bot-a-accounts-findings.md)).

## Caveats

- **CFD data, not futures.** Dukascopy's CFD is used, not futures prints.
  Overnight fills on MNQ can be worse than the one or two ticks assumed.
- **One mechanical reading of a loose idea.** ICT-style traders add
  discretion: displacement, fair-value gaps, higher-timeframe bias. None of
  that is tested here. Rules that can't be written down can't be
  backtested either.
