# The top five, tested over 10,000+ trades each

As of 2026-09-25 (the last three years and FBB5 added that morning).
Backtests on daily and one-minute bars, not advice. Paper only.

**The answer.**

- **The top five.** Every strategy on our lists was ranked on one footing:
  - dollars a day on $25,000, January 2012 to September 2026;
  - each at its own list's size;
  - anything trading TSMX or TSM left out.

  The five that make the most a day are all swing trades on leveraged funds,
  $66 to $92 a day: CB51, D609, CBE3, 852D and 01D4.
- **What the 10,000+ trades showed.** Each rule traded on 173 funds, 40,829
  to 225,822 trades apiece.
  - None of the five picks its entries better than random days on the same
    funds, held just as long. Four are no better than random or worse.
  - 01D4 is better by 3.8 bp a trade (p = 0.002). Three times the
    slippage turns its average trade negative.
  - Their dollars are the funds' rise. Holding the same funds made more on at
    least 98% of them.
  - The two leveraged-fund bots on paper do no better.
    - Split bot 1 beats random entries by 5.6 bp a trade (p = 0.04), gone at
      three times the slippage.
    - Split bot 2 does 42 bp a trade worse than random.
- **The Nasdaq-100 breakout is the one with a real edge.**
  - On the Nasdaq-100: 3,176 trades, +3.55 bp a trade after costs,
    t = 4.2, all 14 years positive.
  - The same rule on the S&P 500, the Dow and the Russell 2000 takes the
    count to 11,801. There it is flat or losing.
  - The edge is the Nasdaq's own.
- **$100 a day.**
  - Retuning the breakout does not help. 162 settings all made money on
    2020-2026, but the ones that led on 2013-2019 did no better afterwards
    than the ones that trailed.
  - Adding NQ Managed Long at 2x lifts the book to $99-113 a day over
    2013-2026, with a smaller worst losing stretch than the $70-80 book.
  - But Managed Long failed the same 10,000-trade test (142,787 trades, no
    timing skill). It is long the index most of the time. On NQ back to
    2000 its own worst losing stretch was -$38,145 on $25,000, through
    2001-2002 and 2008.
  - One leg did pass: FBB5, the MUU / SOXL Uptrend Dip (below). The
    breakout at TQQQ 2x plus FBB5 made $111 a day over 2013-2026 with a
    worst losing stretch of -$15,069, the $70-80 book's -$14,863 give or
    take.
    - Both legs beat random entries.
    - Holding $25,000 of MUU or SOXL overnight can leave too little
      day-trading buying power for the TQQQ leg in a $25,000 account.
- **The last three years** (September 2023 to September 2026) were led by
  the Micron and chip funds.
  - The top four:
    - D609 made $275 a day;
    - CB51 $188;
    - CBE3 $182;
    - FBB5 $156.
  - Holding Micron at 2x made $215 a day.
  - Only FBB5's trades beat random entries in those three years across the
    173 funds (+16 bp a trade, p = 0.05). It did the same over the whole
    history (+14.7 bp over 41,791 trades, p = 0.002).

## The ranking

67 strategies, dollars a day on $25,000 at each list's own size, January
2012 to September 2026 (`strategies/top5/rank.py`, all rows in `rank.json`
there). "Holding" is the same funds held for the whole window.

| # | Strategy (list) | $ a day | 2012-18 | 2019-26 | Sharpe | Worst losing stretch | Holding the funds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | MUU / SOXL Uptrend Dip, bred CB51 (leveraged #25) | $92 | $64 | $117 | 1.27 | -$29,427 | $85 |
| 2 | MUU Trend Breakout, bred D609 (leveraged #2, paper bot #2) | $81 | $43 | $116 | 1.33 | -$25,851 | $88 |
| 3 | MUU / SOXL Uptrend Dip, bred CBE3 (leveraged #18) | $74 | $57 | $90 | 1.14 | -$30,328 | $85 |
| 4 | AMDL Uptrend Dip, bred 852D (leveraged #12) | $66 | $60 | $71 | 1.10 | -$23,123 | $91 |
| 5 | SOXL / TQQQ / TECL Uptrend Dip, bred 01D4 (leveraged #35) | $66 | $25 | $103 | 1.00 | -$22,086 | $66 |
| 8 | NVDL / AMDL Short-Trend Rider (leveraged #24, paper split bot 2) | $59 | $42 | $75 | 0.90 | -$23,651 | $97 |
| 11 | MUU Quick Dip, 2%/2%/10%/4 days (leveraged #5, paper split bot 1) | $56 | $40 | $71 | 1.15 | -$15,364 | $88 |
| 16 | Nasdaq-100 breakout, 0.30% stop, TQQQ at 2x (quick trades) | $51 | $47 | $54 | 1.17 | -$13,931 | - |
| 23 | NQ at 2x, Managed Long (nq-2x #15) | $44 | $33 | $54 | 1.44 | -$7,915 | $18 at 1x |
| 53 | Combo: All Five Setups, the best of the first fourteen | $10 | $4 | $15 | 0.70 | -$6,809 | $59 |

- Dollars a day are the account's mean daily return times $25,000.
- The worst losing stretch is that of a fixed $25,000 account: a stretch
  larger than $25,000 would have emptied it.
- The funded day trades ($2 to $15 a session in their report) and the
  scalpers (none held up on real quotes) are not rerun.

## The last three years

September 22, 2023 to September 22, 2026 (`strategies/top5/rank.py --by 3y`,
`strategies/top5/last3.py`). Own funds, each at its list's size:

| # (3 years) | Strategy | $ a day, 3 years | Sharpe | Worst losing stretch | Holding the funds | $ a day, 2012-2026 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | MUU Trend Breakout, bred D609 (paper bot #2) | $275 | 3.15 | -$14,744 | $215 | $81 |
| 2 | MUU / SOXL Uptrend Dip, bred CB51 | $188 | 1.98 | -$21,734 | $177 | $92 |
| 3 | MUU / SOXL Uptrend Dip, bred CBE3 | $182 | 1.98 | -$24,622 | $177 | $74 |
| 4 | MUU / SOXL Uptrend Dip, bred FBB5 | $156 | 2.74 | -$8,806 | $177 | $57 |
| 5 | MUU / SOXL Quick Dip, 2%/2%/6%/4 days | $156 | 1.93 | -$13,891 | $177 | $58 |
| 6 | AMDL / MUU Volume Momentum | $150 | 1.71 | -$16,320 | $182 | $45 |
| 7 | MUU Quick Dip, 2%/2%/10%/4 days (paper split bot 1) | $146 | 1.96 | -$15,364 | $215 | $56 |
| 8 | AMDL Uptrend Dip, bred 852D | $144 | 2.08 | -$12,451 | $149 | $66 |
| 31 | NQ at 2x, Calm Trend Champion | $65 | 2.24 | -$4,521 | $22 at 1x | $34 |
| 35 | NQ at 2x, Managed Long | $55 | 1.67 | -$6,973 | $22 at 1x | $44 |
| 43 | Nasdaq-100 breakout, TQQQ at 2x | $40 | 0.81 | -$13,931 | - | $51 |
| 57 | MSTR sleeve, Bitcoin's breakout x1.8 | $14 | 0.51 | -$13,658 | - | $14 |

**The same three years across the 173 funds.** These are the trades that
opened in the window, against random entries on the same funds with the same
holding times (500 draws):

| Strategy | Trades | Mean trade | Random entries | Edge, p | $ a day, median fund | Holding it |
| --- | --- | --- | --- | --- | --- | --- |
| D609 | 6,002 | +128 bp | +123 bp | +5.2 bp, 0.35 | $9 | $28 |
| CB51 | 8,671 | +128 bp | +135 bp | -7.3 bp, 0.71 | $13 | $28 |
| CBE3 | 7,141 | +114 bp | +138 bp | -23.8 bp, 0.96 | $9 | $28 |
| **FBB5** | 6,351 | +68 bp | +52 bp | **+16.1 bp, 0.05** | $7 | $28 |
| MUU / SOXL Quick Dip 2/2/6/4 | 9,299 | +30 bp | +36 bp | -5.6 bp, 0.78 | $2 | $28 |
| AMDL / MUU Volume Momentum | 2,551 | +187 bp | +338 bp | -151 bp, 1.00 | $4 | $28 |
| MUU Quick Dip (split bot 1) | 9,004 | +39 bp | +41 bp | -2.7 bp, 0.62 | $3 | $28 |
| 852D | 30,049 | +13 bp | +14 bp | -0.5 bp, 0.55 | $7 | $28 |
| 01D4 | 32,571 | +13 bp | +10 bp | +3.0 bp, 0.15 | $5 | $28 |
| Short-Trend Rider (split bot 2) | 6,602 | +52 bp | +97 bp | -45 bp, 1.00 | $5 | $28 |
| NQ Managed Long | 15,598 | +35 bp | +40 bp | -5.1 bp, 0.95 | $20 | $35 |

The Nasdaq-100 breakout's 708 trades in the window made +2.8 bp each (t =
1.3). That is ahead of random sides (p = 0.03), but thinner than its
2013-2026 record. On all four indexes it lost 1.0 bp a trade.

**FBB5, the MUU / SOXL Uptrend Dip** (leveraged-etfs #9,
`L09/summary.json`):

- **Buy** on any of:
  - a 2% down day after a 24%+ run over 20 days, still above the 20-day mean;
  - a close at the bottom of the Bollinger band within 10% of the 200-day;
  - a MACD histogram under -0.26 with 20-day volatility under 55% and the
    market's 20-day return under 3.5%.
- **Sell** when the close reaches the upper quarter of the band, on a 9%
  five-day drop, or at a 10% stop.
- **Wide set, 2005-2026.** Over 41,791 trades it beat random entries by
  14.7 bp a trade (p = 0.002), still +19 bp a trade at three times the
  slippage.
  - Positive in 17 of 22 years.
  - 2008 was -1.7% a trade; the three leaders above lost 3.4% to 4.0%.
- **Its own funds.** $53 a day over 2011-2026, Sharpe 1.28, worst losing
  stretch -$11,691; holding them had -$50,718.
  - 2025 made $160 a day and 2026 so far $370, so the three-year number is
    mostly the Micron run.
  - 2011-2024 ran from -$13 to +$133 a day a year.

## The five, trade by trade

Each rule was run unchanged through evotrader's engine, one fund at a time
(`strategies/top5/rigor.py`):

- **Fills.** Signal on the close, fill at the next open, 8 bp slippage a
  side, the genome's own stops, targets and holding limits.
- **Funds.** Its own funds from 2005 (or when they start), plus:
  - 143 synthetic 2x funds on large US stocks;
  - 30 synthetic 3x funds on index, sector and country ETFs
    (`universe.py`).

Every trade is in `<key>/trades.csv.gz`.

| Strategy | Own funds: $ a day (holding them) | Own funds: worst stretch (holding) | Trades, 173 funds | Mean trade (95% range) | Random entries, same funds and holds | Timing edge, p | Beat holding | Mean trade at 3x slippage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CB51 | $87 ($77), 2011-2026 | -$29,427 (-$50,718) | 62,918 | +68 bp (+59 to +77) | +75 bp | -6.5 bp, 0.90 | 1% of funds | +36 bp |
| D609 | $58 ($65), 2005-2026 | -$38,299 (-$103,528) | 40,829 | +48 bp (+37 to +58) | +66 bp | -18.2 bp, 1.00 | 0% | +16 bp |
| CBE3 | $69 ($77), 2011-2026 | -$30,328 (-$50,718) | 52,411 | +60 bp (+51 to +68) | +76 bp | -16.1 bp, 1.00 | 1% | +28 bp |
| 852D | $46 ($60), 2005-2026 | -$34,364 (-$138,102) | 213,748 | +6 bp (+4 to +8) | +7 bp | -0.6 bp, 0.68 | 0% | -26 bp |
| 01D4 | $60 ($61), 2010-2026 | -$23,885 (-$33,634) | 225,822 | +8 bp (+6 to +11) | +5 bp | +3.8 bp, 0.002 | 1% | -24 bp |
| MUU Quick Dip (split bot 1) | $41 ($65), 2005-2026 | -$16,352 (-$103,528) | 60,246 | +25 bp (+19 to +30) | +19 bp | +5.6 bp, 0.04 | 0% | -7 bp |
| Short-Trend Rider (split bot 2) | $50 ($71), 2005-2026 | -$42,209 (-$108,468) | 49,537 | +9 bp (+1 to +17) | +51 bp | -42.3 bp, 1.00 | 0% | -23 bp |

How to read it:

- **The average trade is positive and significant for all of them**
  (t-statistics 2 to 14). That is what made them look good.
- **Random entries on the same funds do as well.** Random entries with the
  same number of trades and the same holding times do as well or better
  (500 draws each). What pays is being in a leveraged fund while it rises,
  not when the rule gets in.
- **Actually trading the other funds.**
  - The median fund made $3 to $10 a day under these rules.
  - Holding it made $25.
  - The rules' only gain is smaller losing stretches, from time out of the
    market.
- **2008.** CB51, D609 and CBE3 lost 3.4% to 4.0% a trade on average across
  the funds; the rules kept buying all the way down.
- **Nudges.** Every number in each rule was moved 20% either way; all stayed
  profitable, on the funds' rise.
- **Order of trades.** Reshuffling their own trades 2,000 times put the
  median worst losing stretch at $27,800 to $32,800 on $25,000.

## $100 a day

**Retuning the breakout does not help** (`strategies/top5/tune_ndx.py`).

- 162 settings, all run on 2013-2019 and then 2020-2026:
  - checks every 15, 30 or 60 minutes;
  - bands from 10, 14 or 20 sessions, width x0.8 to x1.25;
  - stops of 0.2% to 0.4%;
  - with and without the VWAP exit.
- Every one made money on 2020-2026, but the best on 2013-2019 did not stay
  best:
  - the ten best on 2013-2019 averaged a Sharpe of 1.11 on 2020-2026;
  - the ten worst averaged 1.14.
- The settings as booked (14 sessions, every 30 minutes, VWAP exit, 0.30%
  stop) ranked 17th of 162 on 2020-2026.

**More legs** (`strategies/top5/book.py`, 2013-01-24 to 2026-09-22):

| Book | $ a day | 2013-19 | 2020-26 | Sharpe | Worst day | Worst losing stretch | Days of $100+ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| The $70-80 book: TQQQ 2x + MSTR 1x | $67 | $50 | $83 | 1.22 | -$4,336 | -$14,863 | 27% |
| TQQQ 2x + NQ Managed Long | $99 | $78 | $121 | 1.79 | -$3,378 | -$11,744 | 37% |
| TQQQ 2x + MSTR 1x + NQ Managed Long | $113 | $85 | $141 | 1.76 | -$4,104 | -$13,737 | 38% |
| TQQQ 2x + NQ Managed Long x1.5 | $123 | $96 | $150 | 1.85 | -$4,370 | -$12,856 | 40% |
| TQQQ 3x + MSTR 1x + NQ Managed Long | $140 | $107 | $173 | 1.70 | -$5,269 | -$16,409 | 39% |
| FBB5 alone, the whole $25,000 | $58 | $35 | $81 | 1.34 | -$4,527 | -$10,181 | 15% |
| **TQQQ 2x + FBB5** | **$111** | $78 | $144 | 1.83 | -$4,081 | **-$15,069** | 29% |
| TQQQ 2x + MSTR 1x + FBB5 | $125 | $85 | $165 | 1.82 | -$4,315 | -$16,725 | 33% |

(MSTR is Bitcoin's breakout from mid-2017; before that the MSTR sleeve is
flat, so the first row is $79 over 2017-2026.)

- **Why the books look so good.**
  - Managed Long barely moves with the breakout (correlation 0.06).
  - 2013-2026 held no crash like 2001 or 2008.
- **What Managed Long's own test showed.**
  - 142,787 trades on the 30 ETFs and 143 stocks themselves at 2x, from
    2000.
  - The average trade was +22.5 bp; random entries made +24.7 bp.
  - It stays long about 80% of the days.
- **Managed Long's record on NQ, 2000 to 2026.**
  - $25 a day and a Sharpe of 0.69; 21 of 27 years up.
  - Its worst years were 2001 (-$56 a day) and 2008 (-$103 a day).
  - A worst losing stretch of -$38,145 on $25,000; holding NQ at 2x was
    -$76,119.
- **What the $100+ books need.** They are for someone who accepts that
  crash risk. They are not the same risk as the $70-80 book.
- **Buying power.** In a $25,000 stock account, Managed Long at 2x (about
  $50,000 of QQQ, or $25,000 of QLD) held overnight cuts the day-trading
  buying power the TQQQ leg needs. One MNQ in a futures account is 2.5x.
- **Funded accounts.** Prop accounts that allow no overnight holds cannot run
  Managed Long.

**What gets $100 a day at the $70-80 book's risk: TQQQ 2x + FBB5.**

- **The numbers.** $111 a day over 2013-2026, a worst losing stretch of
  -$15,069 against the $70-80 book's -$14,863, $144 a day over 2020-2026.
- **Both legs passed the random-entry test.** The two barely move together
  (correlation -0.03).
- **The caveats:**
  - FBB5's own-fund record starts in 2011, so there is no 2008 on MU and
    SOXL. On the other funds, 2008 cost it 1.7% a trade.
  - It was bred on 2019 to March 2026 on those two funds.
  - Its dollars there are also Micron's and the chip index's rise.
- **Buying power.** FBB5 holds the whole $25,000 in MUU or SOXL overnight. A
  broker's margin on a leveraged fund can then leave less than the $50,000 of
  day-trading buying power the TQQQ leg uses. Running them in two accounts,
  or on more capital, avoids that.
- **Without FBB5:**
  - the breakout book on more capital ($32,000 with MSTR, $49,000 for the
    breakout alone at TQQQ 2x);
  - or more size, with its risk: TQQQ 4x made $102 a day but its worst
    losing stretch was $27,863, more than the account.

## The Nasdaq-100 breakout over 11,801 trades

The rule as booked, on one-minute bars, 2013 to September 2026, 1 bp a round
trip (`strategies/top5/rigor_ndx.py`; every trade in `ndx/trades.csv.gz`):

| Index | From | Trades | Mean trade | Win rate | Profit factor | t | Years up | Longs | Shorts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Nasdaq-100 | Jan 2013 | 3,176 | +3.55 bp | 36% | 1.27 | 4.2 | 14 of 14 | +5.0 bp | +2.1 bp |
| S&P 500 | Feb 2013 | 2,981 | +0.94 bp | 35% | 1.08 | 1.4 | 7 of 14 | +1.8 bp | +0.1 bp |
| Dow | Jan 2013 | 3,361 | -0.80 bp | 33% | 0.93 | -1.4 | 4 of 14 | -0.4 bp | -1.2 bp |
| Russell 2000 | Sep 2018 | 2,283 | -2.05 bp | 30% | 0.88 | -2.2 | 2 of 9 | -1.2 bp | -2.8 bp |
| All four | | 11,801 | +0.57 bp | 34% | 1.04 | 1.5 | | | |

- **Taking the other side at random.**
  - The same 11,801 trades with the side drawn at random average -1.01 bp
    (2,000 draws).
  - The rule's direction is worth about 1.6 bp a trade across the four
    (p < 0.001), almost all of it on the Nasdaq-100.
- **Costs.** At 2 bp a round trip the four together lose. The Nasdaq-100
  alone still makes +2.55 bp.
- **The Russell 2000 CFD** keeps few enough minutes before September 2018
  that those days are dropped.
- **No crash test.** Dukascopy's Nasdaq-100 minutes start in January 2012, so
  the rule cannot be tested on 2000-2002 or 2008. It made money in 2020 and
  2022.

## How the tests work

- **Synthetic funds.**
  - Each is k times its underlying's daily move from the previous close.
  - Less 1% a year and, for each unit of leverage above one, that year's
    short rate plus 3%.
  - Built the same way as MU.2X (`strategies/etf/synth.py`), from Yahoo's
    daily bars back to 1998.
- **Survivorship.** The 143 stocks are today's large caps, which flatters
  anything that buys. Random entries on the same funds carry the same bias,
  so the rule-versus-random column is the fair test. The raw dollars are
  not.
- **Random timing.** On each fund, as many trades as the rule made there,
  each with one of the rule's own holding times. Each is entered at the open
  of a random day and sold at the open that many days later, paying the same
  slippage. The random books are rebuilt 500 times; p is the share of them
  that did as well as the rule.
- **Nudges.** Each number in the rules and the risk settings was scaled by
  0.8 and 1.2, one at a time, on the strategy's own funds and on 25 of the
  others.
- **Reshuffled order.** The own-fund trades were resampled 2,000 times into
  new sequences on $25,000 a trade, for the spread of the worst losing
  stretch.

## Reproduce

```
python strategies/top5/rank.py        # the ranking (--by 3y for the last three years)
python strategies/top5/last3.py       # the last three years across the 173 funds
python strategies/top5/universe.py    # the synthetic 2x and 3x funds
python strategies/top5/rigor.py       # the five, the two split bots and Managed Long
python strategies/top5/rigor.py L09 L08 L42 L14   # the other three-year leaders
python strategies/top5/rigor_ndx.py   # the Nasdaq-100 breakout on four indexes
python strategies/top5/tune_ndx.py    # 162 settings of the breakout
python strategies/top5/book.py        # the books toward $100 a day
```
