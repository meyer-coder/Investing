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

Costs change that. Bid-ask spreads measured at today's open were wider than
the cent assumed here: 1 to 3 bp on the biggest names, 10 to 40 bp on
software mid caps. At half those spreads (paid going in; the closing auction
costs nothing coming out), the stock half earns much less. The book then
makes about $40 to $90 a day, with a Sharpe of 1.1 and a worst stretch of
about $13,700.

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
- **Weaker over the long run:** 2013 to August 2020 (1,856 sessions, not
  used to choose anything) made +1.9 bp a day, Sharpe 0.65, about $19 a day
  at QQQ 4x.
  - It was positive in 6 of 8 years, but 2018 alone made +10 bp a day.
  - 2016 and early 2020 were slightly negative.
  - Across 2013-2026 it is a real but small and uneven edge.
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
- **Sensitive to the spread** (`stock_orb.py`, `spread_bp`). Opening
  spreads are wide on gap days. Using spreads sampled from Nasdaq's quote
  service at the 2026-09-24 open (`spreads.py`; likely Nasdaq's own book, so
  an upper bound on the best national quote):

  | Cost per trade | Sep 2022-Aug 2024 | Sep 2024-Sep 2026 |
  | --- | --- | --- |
  | A cent of spread plus $0.007 a share (the tables above) | $29 a day | $47 |
  | Half the measured spread plus 2 bp (spread paid going in, closing auction out) | $9 | $28 |
  | The full measured spread plus 2 bp | -$10 | $12 |

  Real costs are probably near the middle row. Paper results with real fills
  will settle it. Midday spreads measured about half the opening ones, but
  these trades enter in the first minutes, when spreads are widest.
- **2024 was slightly negative**, at -$7 a day.
- **Volatile stocks are no better over time** (`gap_volatile.py`, 77 names
  such as MSTR, COIN, SMCI, HOOD, IONQ and RKLB).
  - Over the last month on 47 of them, the rule averaged $197 a day.
  - Over 60 days of five-minute bars, the best version made $111 a day,
    give or take $86.
  - Over two years of hourly bars, a first-hour version made $20 to $30 a
    day, falling from about $45 in the first year to $8 in the second.
  - The one good month was luck, not a bigger edge.

Pine Script: [gap_breakout.pine](gap_breakout.pine). It runs one chart at a
time; the paper bot picks the day's three gappers. Research:
`strategies/quick/stock_orb.py`.

## TQQQ, SOXL, MSTR and other funds and stocks

The same two trades were run on 34 other funds and stocks (`funds.py`). The
long one-minute history used above does not cover these, so this uses
Yahoo's bars:

- **Hourly bars, two years.** The noise area is checked at each hourly
  close, alongside a first-hour range breakout.
- **Five-minute bars, 60 days.** The noise area is checked every half hour,
  alongside 5- and 30-minute range breakouts.

The hourly version is a coarse copy of the rule. On QQQ it kept only about a
third of what the one-minute rule made over the same two years.

| Name | Hourly, 2 years (1st / 2nd year) | 5-minute, 60 days | Verdict |
| --- | --- | --- | --- |
| **TQQQ** | about 0 bp a day | +18.5 bp a day | The one-minute Nasdaq rule at three times the size: $21 a day at 1x, $84 at 4x since 2024, with a worst stretch of $31,000 at 4x |
| **SOXL** | +6.5 (+19.0 / -6.0) noise area; +15.5 (+20.6 / +10.5) first-hour breakout | -30.6 | Weak and unsteady. At about $27 a share, a round trip costs about 7 bp |
| **MSTR** | +13.5 (+23.2 / +3.8), Sharpe 1.2 | +25.9 | Positive, but fading, and it follows Bitcoin (below). $34 a day at 1x; $135 at 4x with a worst day of -$7,700 and a worst stretch of -$27,900 |
| **COIN** | +9.6 (+13.2 / +6.0), Sharpe 0.9 | +17.3 | Same as MSTR |
| QQQ, SPY, IWM, UPRO, TNA, GLD, TLT, XLE, AMD, SMCI, PLTR, META | mostly negative | mixed | No |

**MSTR and COIN are mostly Bitcoin** (`crypto.py`).
- From 09:30 to 16:00, MSTR moves 1.8 times Bitcoin (correlation 0.73) and
  COIN 1.5 times (0.70).
- On ten years of Bitcoin during US hours (2,304 sessions), the same rule
  made +3.1 bp a day with a Sharpe of 0.4. It was positive in only 5 of 10
  years.
- Bitcoin's good years were 2019 (+23 bp), 2023 (+24) and 2024 (+11); 2018
  (-17) and 2025 (-6) were bad.
- MSTR's two good hourly years sit in that 2023-2024 run, and its second
  year faded as Bitcoin's 2025 turned negative.
- It is a regime that comes and goes, not a steady edge, and it is not a
  $200-a-day trade.

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
| The gap breakout entered on a pullback with a limit order, to skip the spread (`gap_retest.py`) | Lost $72-76 a day from Sep 2024: the breakouts that come back to their level fail |

## Connecting a bot

Both Pine Scripts send an alert with a small JSON message on every entry,
exit and end-of-day flatten. That alert is the plug-in point.

- **Futures (MNQ on a funded account).** A TradingView alert goes to a
  webhook service that routes orders to the account's platform (for
  example Tradovate or NinjaTrader). Check the funded account's own rules
  on automated trading first.
- **Stocks (QQQ, TQQQ or the gappers).** Use a broker that takes
  TradingView alerts or webhooks.

The scripts are written for Pine v6. They were not compiled on TradingView in
this session, because the TradingView connection was down. Load each on a
1-minute chart and fix anything the editor flags.

Run it on paper, or on a funded account's evaluation, before any money.

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
