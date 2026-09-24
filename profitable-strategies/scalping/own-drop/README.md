# Own-Drop Scalper

One bot. Every trade lasts four minutes, and nothing is ever held past the
close: the day's last sale is at 09:50 New York. Found 2026-09-23 on one month
of one-minute data. Backtests and paper trading, not advice.

## What it does

It watches 47 liquid names: the 17 the first scalper used (SOXL, SOXS, MUU,
NVDL, SMCI, MSTR, COIN, MRVL, MU, ARM, PLTR, AMD, META, TSLA, AVGO, NVDA and
TQQQ) and 30 that nothing was ever chosen on (HOOD, RKLB, IONQ, NET, CRWD,
SHOP, UBER, NFLX, ANET, APP, CVNA, SNOW, DDOG, ORCL, GOOGL, AMZN, AAPL, MSFT,
INTC, QCOM, LRCX, AMAT, KLAC, CRWV, OKLO, HIMS, AFRM, RDDT, DELL and ASTS).

- **Buy** a name when, on any one-minute bar from 09:35 to 09:45, both of these
  hold:
    - it fell more than 0.75 of its 14-minute average range (ATR as a share of
      price);
    - it fell on its own: its return, less the average return of the other 46
      names that minute, is more than two standard deviations below normal
      for it, judged on its last 20 minutes.

  The buy fills at the next minute's open.
- **Sell** at the open four minutes after the buy.
- **At most three positions**, each a third of buying power. When more names
  signal in the same minute than there are free slots, the one that fell
  hardest on its own goes first.
- **Never past the close:** a hard exit at 15:55. In practice the last sale
  is at 09:50.

A drop the whole market shares is news, and it tends to keep going. A drop
one name takes alone is usually one seller leaning on the book, and it snaps
back within minutes.

## Results

A $25,000 account, 21 sessions (2026-08-25 to 2026-09-23). Each name is
charged a cent plus 1 bp each way at its own price. The first session had no
history to judge a drop against, so it counts as a $0 day.

| Buying power | Average day | Typical day (median) | Days up | Days at $100+ | Worst day |
| --- | --- | --- | --- | --- | --- |
| 1x ($25,000 of positions) | $73 | $58 | 67% | 33% | -$176 (0.7%) |
| 1.5x | $109 | $86 | 67% | 43% | -$265 (1.1%) |
| 2x ($50,000) | $146 | $112 | 67% | 52% | -$353 (1.4%) |

It makes about 7.5 trades a day. 57% of trades win, and a trade averages
+11.7 bp after costs. The paper trail runs at 2x.

| Check | Result |
| --- | --- |
| Each week on its own (2x) | $96, $150 and $191 a day |
| The 17 original names / the 30 new ones (2x, all 21 sessions) | +$1,053 / +$2,155 |
| Names | All 47 traded, and 28 made money. DELL, HOOD, SNOW, MRVL and ANET made the most; COIN, INTC, ARM and CVNA lost the most |
| Without its best day (Sep 2, +$924 at 2x) | $107 a day at 2x |
| Losing streaks (2x) | At most four losing days in a row. The worst five-day stretch lost $254 |
| Costs doubled | $50 a day at 1x (62% of days up), $99 at 2x |
| Costs tripled | $26 a day at 1x (52% of days up) |
| Every fill a full minute late | $62 a day at 1x and $124 at 2x, but the last week lost money ($20 a day at 1x) |
| Which names get the slots (1x) | Hardest own drop first: $73 a day. Alphabetical: $76. A random order, 12 times: $51 on average ($22 to $68) |

**About that last row.** The first version of this page took names that
signalled together alphabetically and reported $153 a day at 2x. Taken in a
random order, the same bot made a third less. The alphabetical order had
simply landed on good names this month. Taking the hardest own drop first is
a rule with a reason behind it. It beat all 12 random orders, in each of the
three weeks and on both groups of names, and that is the version here.

## How it was found

1. **Event study** (`strategies/scalp/events.py`). About 250 one-to-four-minute
   setups were tried on the 17 names. Only buying sharp drops in the opening
   minutes kept its edge in both halves of the month.
2. **The Opening Dip Scalper** (`bot.py`, [its README](../opening-dip/README.md)).
   It made $119 a day at 1x on those 17 names. On the 30 new names it made
   about $10 a day, so the edge was in the names it was found on, not the rule.
3. **Dead ends.** Trading only the day's most active names (`inplay.py`)
   reached $40-60 a day. Ten years of NQ futures sessions (`nq_events.py`)
   had no one-to-four-minute setup that survived costs. The mirror image,
   shorting a name's own sharp rise, lost 4-20 bp a trade on both groups of
   names (`mirror.py`). A lone rise at the open keeps going; a lone drop comes
   back. More, smaller positions (6 to 15 at once) made less (`slots.json`).
4. **Residual drops** (`residual.py`). A name's drop was measured against the
   other names' average that minute. The setup was chosen on the 17 names'
   first 14 sessions. It held on their last 7 sessions and on the 30 new names
   (+6.9 bp a trade there).
5. **One bot** (`residbot.py`, `owndrop.py`). Both conditions together, run in
   the engine: next-minute fills, each name's own cost and three positions.
   It kept both groups of names profitable.
6. **Who gets the slots** (`owndrop.py --orders`). The hardest own drop goes
   first, as above.

## Read this before trusting it

- **One month is short.** It covers 21 sessions in one regime, a strong,
  volatile semiconductor rally. The settings were picked on this month, so the
  paper trail from 2026-09-24 is the real test.
- **About one day in three loses.** At 2x the typical day is $112 and the
  average is $146, because a few big days lift the average. Judge it over
  weeks, not days.
- **Speed matters.** The signal is gone within a minute or two. Every fill a
  minute late still made money over the month, but lost in the last week. The
  order has to go in within seconds of the minute's close.
- **The opening minutes are the hardest to fill.** Spreads are wider then than
  the one-cent cost assumes on some names. Doubled costs leave $50 a day at 1x.
- **It needs day-trading buying power.** At 2x each position is about $16,700
  on a $25,000 account. A margin account over $25,000 gets up to 4x intraday.
  A funded account's buying power and daily loss limit vary, so check both.
  The worst day at 2x, -$353, is 1.4% of $25,000.
- **No TradingView version yet.** The signal needs all 47 names every
  minute, which is more than one Pine script can request. It runs from Python.

## Running it

- `paper.json` and `paper/<date>.md`: the paper trail at 2x. Each evening
  `python strategies/scalp/replay.py` replays the day from its one-minute
  bars, and each trade is written once.
- `backtest.json`: the numbers above, from `python strategies/scalp/owndrop.py`.
  `orders.json`, `slots.json` and `grid.json` come from its `--orders`,
  `--slots` and `--grid` options.
- `strategies/scalp/`: the studies, the bot and the replay.
- `tests/test_scalp.py` checks that the residual reads only minutes already
  closed. It also checks that a drop the whole market shares is not bought,
  that each trade lasts four minutes, and that the hardest own drop gets the
  last slot.
