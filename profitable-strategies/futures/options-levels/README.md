# Options levels on MNQ (forward paper test)

A test of the style in the screenshot trade: short the Nasdaq-100 future into
an options-derived resistance, buy it at support, a 15-point stop, a target
three times as far, 10 MNQ. Started 2026-09-24. **No track record yet**, so do
not trade it with money until the paper trail below has at least 20 to 40
sessions.

## Why a forward test and not a backtest

The levels come from options open interest, and there is no free history of
it, so they can only be built from today on. What the history does say
(`strategies/mnq/README.md`): the same stop-and-target shape on entries
with no edge breaks even (35% of trades win at three to one), and NQ's price
path alone gives no short-term edge. So any profit has to come from where the
levels are. At three to one with costs, trades at the levels must win more
than about 27% of the time to make money.

The walls almost always sit on round QQQ strikes, which do have a price
history. On six years of Nasdaq-100 minutes (`strategies/mnq/strikes.py`),
the same stop and target at the first touch of each day's round strikes
reached the target 23-27% of the time. That holds whether the trade fades
the touch or goes with it. Round strikes did no better than prices halfway
between two strikes, where no option sits. So round numbers alone are not
levels. That lowers the odds but does not settle them: the real walls are
the few strikes with the most open interest on the day, and only the
forward test can check those.

## The levels, each morning before the open

From the delayed QQQ option chain on nasdaq.com (all contracts expiring in
the next 45 days), `strategies/mnq/levels.py`:

- **Gamma exposure by strike:** gamma x open interest x 100 x price squared x
  1%, calls positive and puts negative. Each contract's gamma comes from its
  implied volatility, backed out of the bid/ask mid.
- **Call wall:** the strike with the most call exposure, which acts as resistance.
- **Put wall:** the strike with the most put exposure, which acts as support.
- **Gamma flip:** the price where total exposure changes sign, recomputed at
  each candidate price.
- **Max pain:** the nearest expiry's strike at which option holders collect
  the least.
- **In NQ points:** QQQ levels times NQ over QQQ at the previous close. These
  approximate what paid GEX services sell.

## The rules

- The first time each day price trades up to the call wall, sell 10 MNQ.
  The first time it trades down to the put wall, buy 10 MNQ. The first touch
  of the gamma flip is faded from whichever side it comes.
- The order fills at the open of the minute after the touch.
- Each trade gets a 15-point stop ($300 on 10 MNQ) and a 45-point target
  ($900). Anything open at 15:55 New York is closed.
- Entries run from 09:35 to 15:30, one trade per level per day, one position
  at a time. Costs are 1.25 points a round trip per contract.
- **A second rule rides along:** on a quiet day (range by 14:00 under 60% of
  the typical pace), go with the first close beyond the day's range between
  14:00 and 15:30. It uses a 10 bp stop and a 20 bp target (about 29 and 58
  points). Over six years it was the one filter that cleared break-even in
  both halves (`strategies/mnq/calmbreak.py`). It fires about once a month.

## Risk on a Topstep 100K

With up to three trades a day, a bad day is about -$1,000 on 10 MNQ. Three
such days in a row reach the $3,000 limit. Use 5 MNQ in the Combine until the
paper trail says otherwise.

## Files

- `paper.json` and `paper/<date>.md`: the paper trail, replayed each evening
  from the day's one-minute MNQ bars by `strategies/mnq/levelbot.py`.
- `data/levels/<date>.json`: the day's levels, saved before the open.
- `options_levels.pine`: TradingView Pine v6 for a one-minute MNQ1! chart.
  Type the day's levels into the inputs; alerts fire on entries and exits.
