## How they were bred

evotrader's loop backtests a population of agents on the training window,
keeps the best, and breeds the next generation from them. There is no API key
in this environment, so mutation and crossover bred each generation, and
Claude, in this session, did the breeding the loop normally asks Claude for,
by hand, at three points.

| round | what happened | runs | generations |
|---|---|---|---|
| 1 | Two runs seeded with the `nq_2x` style's twenty archetypes (index-sized dips, trends, calendar effects, breakouts): quick holds of about three sessions, and swing holds of about eight | 2 | 24 |
| 2 | Eight islands, each started by Claude from one family (47 genomes: deep pullbacks, volume flushes, calm trends, calendar, momentum, trend plus dip, quick flushes, price patterns) and bred 15 generations | 8 | 120 |
| 3 | Claude read the island leaderboards, training numbers only, and wrote 19 children: ten iterations of the trend-plus-dip leader with its clutter removed, and cleaned-up flush, pullback, calendar and quick-dip books. They were injected into five islands (`evotrader inject`), which were bred 12 more generations. A second calm-trend island started from six structured seeds after the first bred itself into buy-and-hold with a 49% drawdown | 6 | 75 |

That is 11 runs, 219 generations, and 13,620 backtests of about 9,100
distinct agents. Every agent traded at the full 2x, because the `nq_2x` style
fixes the size. Training covered January 2019 to 20 March 2026, with the
fitness weighting the most recent six or twelve training months at 60% to 70%.
Costs were 0.2 bp commission and 1 bp slippage a side, about $15 per MNQ round
trip, several times the real cost.

Then the gauntlet (`strategies/nq2x/gauntlet.py`) scored 179 candidates on
four windows: the top distinct behaviours of every run plus every
hand-written child.

- 153 made money on both the held-out six months and the training window.
- 140 of those also had a profit factor of at least 1.2 held out and 1.1 in
  training; they reduce to 46 distinct behaviours.
- 23, with a cap per family, also made money over 2010 to 2018, survived
  three times the costs, and kept their training drawdown under 40%.

The twenty here drop seven of those 23 as near-duplicates, the same rules
with slightly different thresholds. They add four that cleared every tier but
were over their family's cap. Eleven of the twenty were bred by the evolution.
Nine were written by Claude and scored exactly as written.

Finally the rules were simplified (`strategies/nq2x/simplify.py`). Clauses,
whole rules and risk settings were removed and thresholds rounded one at a
time, and a change was kept only if every trade from bar 260 on, in all three
windows, stayed the same. Every number on this page comes from re-running the
simplified rules.

## Tighter stops: what a 9-point stop does

A stop sized for a daily loss budget, for example 9 points so that three or
four losses fit inside a $1,000 drawdown, was tested on all twenty strategies
as a resting stop order that fills inside the bar, the way a real stop
fills (`strategies/nq2x/stop_study.py`, results in
`reports/stop_study.json`).

Nine points is 0.03% of NQ at 31,000. Over the last six months NQ's median
session range was 514 points, and it traded at least 9 points below the open
on 94% of sessions. With a 9-point stop, 80% to 100% of trades are stopped
out on the day they are entered.

| stop, resting order | profitable in the last six months | profitable on all three windows | median $ per session, last six months | loss per stop-out at 1 MNQ |
|---|---|---|---|---|
| each strategy's own stop, on the close (as published) | 20 of 20 | 20 of 20 | +$60 | $2,600 at the champion's 4.2% |
| 9 points | 12 of 20 | 0 of 20 | +$15 | $18 |
| 25 points | 17 of 20 | 0 of 20 | +$17 | $50 |
| 50 points | 20 of 20 | 12 of 20 | +$30 | $100 |
| 100 points | 19 of 20 | 9 of 20 | +$31 | $200 |
| 150 points | 19 of 20 | 11 of 20 | +$24 | $300 |
| 250 points | 20 of 20 | 15 of 20 | +$51 | $500 |
| 400 points | 20 of 20 | 18 of 20 | +$51 | $800 |

At 9 points the median strategy lost 7% over 2019-2026 and 5% over
2010-2018. The twelve that stayed positive over the last six months did so
because a strong rally carried the few trades that survived the stop. These
are daily-bar strategies that hold one to thirteen sessions; they need room
of a few hundred points. A stop of 100 to 150 points ($200 to $300 a loss on
one MNQ, three to five losses inside $1,000) keeps 9 to 11 of them profitable
on every window, led by Quiet MACD Trend (+$57 a session at 2x with a
100-point stop), Calm Trend, Volume-Checked Dips (+$53), Managed Long (+$45)
and Calendar Dips (+$43). A true 9-point stop belongs to intraday trading,
several trades a day on one- to five-minute bars, which is a different system.

## The data

- NQ1! from TradingView, daily bars since 1999. Each quarterly roll is
  back-adjusted by ratio. The roll gap, about 1% a quarter at recent rates, is
  carry, not profit, and an unadjusted continuous contract books it as a gain.
  Bars are labelled by trading date: a session that opens Sunday 18:00 New
  York is Monday's bar. Checked against the NDX index, daily returns correlate
  0.99. On roll days the adjusted series matches the index, where the raw
  contract shows a phantom +1%.
- Decisions on the daily settlement, fills at the next open (the 18:00
  reopen). Stops and targets are checked on the close, so a gap through a stop
  fills worse than the stop, as it would live.
- 2x: a 1.0 weight holds twice equity in notional, with no financing charge,
  because futures carry is already in the price.

## What the numbers cannot tell you

- Six months is short. The held-out window holds 5 to 27 trades per
  strategy; the training window (76 to 303 trades) and the older window carry
  the statistical weight.
- The ranking is by one regime: a strong, orderly rally. A choppy or falling
  half year reorders it. The last-twelve-months line in each strategy shows
  what that looked like most recently.
- At 2x every strategy has lost 9% to 13% of the account in a single day
  somewhere in its training window, about $2,200 to $3,300 on $25,000. For
  eleven of them that day was 13 September 2022, when NQ fell more than 5% on a
  hot inflation report; for most of the rest it came in the February-March
  2020 crash.

## Reproduce

```bash
# the four windows for every strategy (the numbers on this page)
python strategies/nq2x/gauntlet.py profitable-strategies/nq-2x/all.json
# year by year and the daily profile, 2010-2026, at 2x on $25,000
python -m evotrader.cli evaluate profitable-strategies/nq-2x/all.json --config configs/nq_2x_quick.json --start 2010-01-01 --test-frac 0 --by-year --daily
# buys for the next open, after 17:00 New York
python -m evotrader.cli signals profitable-strategies/nq-2x/all.json --config configs/nq_2x_quick.json --refresh
# the forward test: every session after the freeze
python -m evotrader.cli evaluate profitable-strategies/nq-2x/all.json --config configs/nq_2x_quick.json --test-frac 0 --since 2026-09-23 --refresh
# breed again: an island, Claude's children injected, more generations
python -m evotrader.cli run --config configs/nq_islands/trend_plus_dip.json
python -m evotrader.cli inject RUN_ID strategies/nq2x/children/r3_trend_plus_dip.json
python -m evotrader.cli resume RUN_ID --generations 12
```

The breeding scripts are `strategies/nq2x/run_islands.sh` and
`strategies/nq2x/round3.sh`; the seeds and children are in
`strategies/nq2x/seeds` and `strategies/nq2x/children`; `final_spec.json`
holds the twenty as published, with their origins.
