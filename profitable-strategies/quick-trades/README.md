# Quick trades: in and out the same day, $200 a day on $25,000?

The ask on 2026-09-24 relaxed the three-minute cap. It was the earlier goal
again: up to ten strategies that each make $200 or more a day on a $25,000
account, trading in and out the same day and flat every night. Everything
here is a backtest plus a paper trail; nothing places an order.

## The answer

None of the ten reaches $200 a day reliably.

Two quick trades held up across every period and setting tested. Each makes
about $30 to $55 a day at the day-trading maximum of 4x buying power. They
barely move together, so run as one book they make about $60 to $110 a day.
They do that with a Sharpe of 1.4 and a worst losing stretch of about $11,000,
45% of the account. (Sharpe is return per unit of daily swing, over a year: 1
is decent, 2 is rare for anything a retail bot can run.)

A $200 average day on $25,000 with that kind of risk would need a Sharpe of
about 3 to 4. Getting to $200 by adding leverage instead (the 3x funds, or
more micro futures) means a losing stretch bigger than the account. The
tables show it.

The combined book at 3.3 times this size would have averaged $200 a day
since 2024. Its worst stretch would then have been about $37,000, more than
the account.

| Book, $25,000 account | 2020/22-2023 | 2024-Sep 2026 | Sharpe | Days at $200+ | Worst day | Worst losing stretch |
| --- | --- | --- | --- | --- | --- | --- |
| **1. Nasdaq-100 noise-area breakout**, QQQ at 4x | $53 a day | $28 | 1.2 | 16% | -$2,431 | -$10,424 (42%) |
| **2. Gap breakout** on large caps, 2% risk a trade | $58 | $32 | 1.05 | 32% | -$1,510 | -$8,791 (35%) |
| **Both at once** (1 at QQQ 4x, 2 at 2% risk) | $112 | $61 | 1.4 | 34% | -$2,229 | -$11,150 (45%) |
| 1 through TQQQ at 4x (12x the index) | $158 | $84 | 1.2 | 22% | -$7,293 | -$31,272 (125%) |

The first column starts in Sep 2020 for book 1, and in Sep 2022 for book 2 and
the combined book.

**By year** (dollars a day):

| Book | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 at QQQ 4x | +14 | +34 | +76 | +59 | +35 | +27 | +20 |
| 2 | | | +48 | +60 | -7 | +28 | +92 |
| Both | | | +87 | +119 | +29 | +56 | +112 |

The Nasdaq edge is shrinking year by year since 2022. The rule was
published in 2023.

**On a Topstep 100K with micro Nasdaq futures:** fresh Combines started every
fifth session since 2020, each running until it passed or breached.

| Size | Passes | Breaches the $3,000 loss limit |
| --- | --- | --- |
| 2 MNQ | 35% | 62% |
| 5 MNQ | 24% | 73% |

The average day is big enough, but the swings are too big for a $3,000
limit.

A resting stop 0.25% from the entry helps a little (`trend.py`, `hard_stop`).
It halves the worst day at QQQ 4x, to -$1,300, and with 2 MNQ it gets 45% of
Combines through and breaches 48%. Recent days make a little less ($24
instead of $28), and 0.4% and 0.6% stops do not line up with it, so treat it
as an option rather than a proven improvement.

## 1. Nasdaq-100 noise-area breakout

From Zarattini and Aziz (2023), *Beat the Market: An Effective Intraday
Momentum Strategy*. The rule, run on a 1-minute chart:

- **The band.** Every half hour from 10:00 to 15:30 New York, compare the
  price with the band the Nasdaq-100 usually stays within by that time of day.
  - The band's width is the average absolute move from the open at that time
    over the last 14 sessions.
  - It is measured from the larger of today's open and yesterday's close
    (the smaller, for the lower band).
- **Entry.** Buy above the band; sell short below it. The order fills at the
  next minute's open.
- **Exit.** At a later check, get out if the price is back inside the band or
  through the day's average price (VWAP).
- **Close.** Flat at the close.

About 0.9 trades a day, in the market about 100 minutes a day. It adds up to
+4.2 bp a day on the amount traded, after 1 bp a round trip.

- **Stable across settings:** all 24 settings tried (14 or 10 or 20 days,
  checks every 15 or 30 minutes, VWAP exit or not, band x1 or x1.5) made
  money both in 2020-2023 and in 2024-2026.
- **Only on the Nasdaq:** on the same data, the S&P 500 was weak and faded
  to losses by 2025. The Russell 2000, the Dow, crude oil, gold, the euro and
  the 30-year Treasury all lost.
- **How to trade it:** QQQ or TQQQ in a stock account, or MNQ/NQ on a futures
  account. The signal is the same.

Pine Script: [noise_area_breakout.pine](noise_area_breakout.pine). Research:
`strategies/quick/index.py`, `trend.py`, `assets.py`.

## 2. Gap breakout on large caps

A version of Zarattini, Barbon and Aziz (2024), *A Profitable Day Trading
Strategy for the U.S. Equity Market*, limited to what the data here covers.

1. **Pick the names.** Each morning, take the three of 72 large caps that
   opened 2% or more away from yesterday's close.
2. **Set the direction.** The first five minutes set a range and a direction.
   If that bar closed up, buy a break of its high; if down, sell a break of
   its low.
3. **Stop.** One 14-day average daily range from the entry.
4. **Exit.** Out at the close.
5. **Size.** Each trade risks 2% of the account, within 4x buying power in
   all.

About two trades a day. Costs are a cent of spread plus $0.007 a share.

- **Stable across settings:** 89 of 96 nearby settings made money in both
  periods. Those settings were gaps of 1.5% to 3%, stops of 0.5 to 1.5
  ranges, 2 to 4 names, and a 5 or 10 minute opening range. The median
  setting made $31 a day before 2024 and $23 after. At twice the costs, this
  one still makes $24 and $43.
- **Other variants were weaker.** The published "stocks in play" version
  (tight stops, names picked by how wild their first minutes are) lost money
  on these large caps. So did tighter stops.
- **2024 was slightly negative**, at -$7 a day.

Pine Script: [gap_breakout.pine](gap_breakout.pine). It runs one chart at a
time; the paper bot picks the day's three gappers. Research:
`strategies/quick/stock_orb.py`.

## What did not work

Every book below lost money or stayed within noise, in the years it was not
fitted on:

| Idea | Result |
| --- | --- |
| Holds of 3 minutes or less | [The scalping page](../scalping/README.md): the drop bounce is the spread settling |
| First half hour predicting the last half hour | Lost, on every market |
| Gap fades and gap follows on the index | Lost |
| Fading big morning moves on the index | Lost |
| The same noise-area breakout on each single stock | 6 to 10 of 72 names positive in both periods, which is chance |
| Market-neutral long-short books rebalanced every 15, 30 or 60 minutes (reversal, momentum, same-half-hour seasonality, gap reversal) | Lost, mostly to costs, with no edge before them |
| Opening-range breakouts and the opening drive on the index | Positive but noisier; adding them to the noise area lowered its Sharpe |
| One book of the noise area across the Nasdaq, S&P, Russell and Dow | Lost, because the other three lose |

## The paper trail

`python strategies/quick/paper.py` replays both books over each finished
session from 2026-09-24. It runs after every close in the evening routine.

- **Nasdaq breakout:** replayed on Yahoo's one-minute NQ futures bars, and
  booked as 2 MNQ and as QQQ at 4x.
- **Gap breakout:** replayed on Yahoo's bars for the day's gappers.

Each session is written once to [paper.json](paper.json), and a note for
each day goes in `paper/`. A few weeks of it will say more than any
backtest.

## What would move this toward $200 a day

- **More capital.** Scaled up with the account, the combined book on
  $50,000 to $100,000 would make about $120 to $450 a day. Its worst stretch
  would still be about 45% of the account, and most prop firms stop an
  account at 5% to 10%.
- **A bigger stock universe.** The gap breakout here covers only 72 large
  caps. The published results came from all US stocks with news, where moves
  are larger. Testing that needs years of minute bars for thousands of names:
  a free Alpaca account gives those. The key goes in the environment settings
  as an environment variable, never in the chat.

Backtests and paper trading, not advice.
