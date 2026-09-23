# Three one-minute SOXL bots

Built 2026-09-23 to answer one question: can quick SOXL trades, one to four
minutes long, make $400 or more a day? On the month of one-minute data there
is, no. Backtests on one-minute bars, not advice.

## The bots

Each trades its own $25,000, one position at a time, entirely intraday:
entries from 09:35 to 15:45 New York (the opening-drive shapes from 09:31),
out by the 15:55 bar, a hold capped at four minutes. The engine decides on
each minute's close and fills at the next minute's open, with 2 bp of
slippage a side on SOXL and 3 bp on SOXS (a cent is 0.7 bp of SOXL's $146
and 3 bp of SOXS's $34).

| Bot | Rule, chosen on the first 14 sessions | First 14 sessions | Last 7 sessions (never used to choose) | Last 7 at double costs |
| --- | --- | --- | --- | --- |
| Long | Buy SOXL after a minute up 0.5% or more in the first 30 minutes; out after 4 minutes or 0.8% down | $62 a day, 2.6 trades, 51% won | $34 a day, 2.0 trades, 57% won | $16 |
| Short | Buy SOXS (SOXL's 3x inverse) after a SOXS minute up 0.3% or more in the first 30 minutes; out after 4 minutes or 0.8% down | $89 a day, 3.9 trades, 52% won | $8 a day, 2.4 trades, 59% won | -$24 |
| Snapback | Buy whichever of SOXL and SOXS fell 0.6%+ in two minutes and sits 2.5 standard deviations under its 20-minute mean; out after 4 minutes or 1% down | $64 a day, 1.6 trades, 70% won | $36 a day, 2.3 trades, 62% won | $2 |

Run together, a third of $25,000 each, the three made about $26 a day over
the last seven sessions.

## Why not $400

- A one-to-four-minute SOXL trade moves about a quarter of a percent. After
  0.04-0.06% of costs a round trip, the edge per trade is a few hundredths of a
  percent, and the setups worth taking come one to five times a day.
- $400 a day on $25,000 is 1.6% a day. At these edges it would take about
  $250,000 working, and a month of data cannot tell a real edge from luck:
  the short bot went from $89 a day to $8 between the two halves.
- Every other shape tried (volume bursts, dips in a rising tape, VWAP
  reclaims, opening-range breaks, single-minute fades, more snapback settings)
  lost money or made less in the untouched sessions. `bots.json` has all of
  them.

## Data

`data/intraday/SOXL_1m.csv` and `SOXS_1m.csv`: regular-hours one-minute bars
from Yahoo, 2026-08-25 to 2026-09-23 (21 sessions). Yahoo keeps one-minute
bars for 30 days only, so `python strategies/soxl/minute.py` runs after every
close and adds the finished sessions: the archive is what will make a longer
test possible.

## Code

- `minute.py`: the archive, and the short side of SOXL as a series.
- `bots.py`: the shapes, the split into choosing and test sessions, the costs.
