# Stacking strategies to $50-60 a day: what 13 markets say

Run with:
- `python research/edges.py` (the search);
- `python research/portfolio.py` (sizing for one account);
- `python research/edges_needed.py` (how far off the goal is).

Numbers are from 2026-09-25, after the close.

## The question

Can we find several strategies that each make $50-60 a day, and stack them
on the two accounts (the Topstep 100K and the FundedNext Legacy 25K)?

## What was tested

**Markets.** 13 markets Topstep allows, with one-minute Dukascopy data. Each
is priced as its CME micro contract, except the T-bond, which has no micro
and is priced as the full-size ZB.

| Contract | Data from | Sessions | Cost a round trip |
|---|---|---|---|
| MNQ (Nasdaq-100) | 2013-01 | 3,387 | 0.36 bp |
| MES (S&P 500) | 2013-01 | 3,108 | 0.95 bp |
| MYM (Dow) | 2013-01 | 3,385 | 0.85 bp |
| M2K (Russell 2000) | 2018-08 | 2,010 | 1.55 bp |
| MGC (gold) | 2013-01 | 3,425 | 0.75 bp |
| MCL (crude) | 2013-01 | 3,126 | 3.48 bp |
| MNG (natural gas) | 2013-02 | 1,717 | 9.90 bp |
| M6E (euro) | 2013-01 | 3,539 | 2.60 bp |
| M6B (pound) | 2013-01 | 3,541 | 2.98 bp |
| MJY (yen) | 2013-01 | 3,534 | 4.65 bp |
| M6A (Australian dollar) | 2013-01 | 3,525 | 4.59 bp |
| MCD (Canadian dollar) | 2013-01 | 3,535 | 4.54 bp |
| ZB (T-bond) | 2019-01 | 338 | 6.33 bp |

The cost is the commission plus one tick of slippage each way, as a share
of the contract's value.

**Strategies.** Four families, with four versions each, give 16 per market
and 208 in all:
- **noise:** the noise-area breakout, which is Bot A;
- **orb:** the opening-range breakout;
- **momentum:** the first half hour predicts the last half hour;
- **gap:** follow or fade a big opening gap.

`research/edges.py` describes each one.

**Protocol.** It was fixed before any result was seen:
1. **Search, data up to 2019.** A version passes with 100+ trades, a
   positive mean after costs and t ≥ 2.
2. **Confirm, 2020-2022.** Still positive, and its long/short calls beat at
   least 90% of 2,000 random sign flips of the same trades.
3. **Final look, 2023-2026.** Looked at once, for information.

## Result: one idea survives, on one market

| Contract | Positive in search | Passed search | Confirmed | Best search result (after costs) |
|---|---|---|---|---|
| **MNQ** | 6 / 16 | **4** | **4** | noise 30m: +3.33 bp, t = 3.2 |
| MES | 5 / 16 | 0 | 0 | noise 60m: +1.51 bp, t = 1.3 |
| MYM | 1 / 16 | 0 | 0 | noise 60m: +0.61 bp, t = 0.7 |
| M2K | 12 / 16 | 0 | 0 | gap follow 60m: +10.7 bp, t = 1.3 |
| MGC | 8 / 16 | 0 | 0 | gap fade 60m: +1.45 bp, t = 1.4 |
| MCL | 8 / 16 | 0 | 0 | noise 60m: +2.89 bp, t = 1.1 |
| MNG | 2 / 16 | 0 | 0 | gap follow to close: +15.0 bp, t = 1.0 |
| M6E, M6B, MJY, M6A, MCD | 0 / 16 each | 0 | 0 | all negative |
| ZB | 0 / 16 | 0 | 0 | all negative |

- **The only survivor is the Nasdaq noise breakout (Bot A).** All four of
  its versions passed every stage, and they held up on 2023-2026 (+4.75 bp
  a trade, t = 2.3, for the 30-minute version). They are one idea, not
  four.
- **The S&P 500 is the near miss.** Its noise breakout was strong only in
  2020-2022 (+5 to +6 bp a trade). It was flat before 2020 and flat again
  after 2022.
- **Currencies lose to costs.** A micro FX contract costs 2.6-4.7 bp a
  round trip. None of the strategies makes more than about 2 bp before
  costs.
- **Crude** was positive before 2020 but lost 5-12 bp a trade after it.
- **The Russell, natural gas and T-bond results are inconclusive.**
  Dukascopy's data for them is short or patchy (the T-bond has 338
  sessions). Their costs are also high.

About 5 of the 208 versions would pass the search by luck alone. Four
passed, all of them the Nasdaq breakout, and that breakout also held up in
the later years. It was checked independently earlier as well (see
`bot-a-accounts-findings.md`).

## Stacked on one account

With one edge there is nothing to stack. `research/portfolio.py` sizes it
for the Topstep 100K funded account, keeping $3,000 after each payout. No
size reached 80% one-year survival on 2020-2022 starts, so it uses the
smallest size, 1 MNQ:

| Period | Bot makes a day | Sharpe | Funded a year: survive | Paid to you a day | Two-year plan, median a day after fees |
|---|---|---|---|---|---|
| Up to 2019 | $19.0 | 1.27 | 70% | $8 | −$3 |
| 2020-2022 | $41.8 | 1.82 | 78% | $21 | +$20 |
| 2023-2026 (unseen) | $25.8 | 1.35 | 93% | $14 | +$5 |

**The FundedNext 25K at 1 MNQ** is the same bot with a $1,000 loss limit.
Keeping $1,000 after each payout:
- 32-41% of funded accounts last three months;
- 7% last a year;
- it pays $5-6 a day;
- the two-year plan's median runs from −$1 to +$10 a day, depending on the
  period.

MNQ is the smallest Nasdaq contract, so this account cannot be run any
smaller.

## How far from $50-60 a day?

`research/edges_needed.py` puts a number on it. Only one real edge exists,
so it uses stand-ins: copies of Bot A's own daily results, shifted in time.
Each copy acts like a second, unrelated edge that is exactly as good.

| Edges like Bot A | Book Sharpe | MNQ each | Bot makes a day | Paid to you a day | Survive a year |
|---|---|---|---|---|---|
| 1 | 1.43 | 0.9 | $23 | $12 | 92% |
| 2 | 2.04 | 0.8 | $41 | $26 | 82% |
| 3 | 2.44 | 0.7 | $54 | $33 | 84% |
| 4 | 2.87 | 0.6 | $62 | $45 | 92% |
| 6 | 3.57 | 0.4 | $62 | $45 | 100% |
| 8 | 4.05 | 0.4 | $83 | $61 | 96% |
| 12 | 5.13 | 0.3 | $93 | $72 | 100% |

(The account is the Topstep 100K, keeping $3,000 after each payout, on
2013-2026 starts.)

**Reading the table:**
- **$50-60 a day paid to you from one 100K needs about 6-8 separate edges.**
  Each must be as good as Bot A and unrelated to the others. For the bot to
  make $50-60 a day before payout rules, about 3-4 are needed.
- **We have one,** after 208 versions on 13 markets.
- **Whole contracts make it harder still.** The table trades 0.3-0.9 of an
  MNQ per edge. Real edges would need contracts smaller than a micro, or a
  bigger account.

## What it means

- **No strategy we tested makes $50-60 a day on these accounts.** The one
  real edge pays about $10-20 a day on the Topstep 100K at 1 MNQ. After
  fees that is a few dollars a day, at the median.
- **The FundedNext 25K cannot carry it.** Its $1,000 limit is smaller than
  Bot A's normal losing streaks at 1 MNQ.
- **Adding copies of the same bot on more accounts** adds pay and fees in
  step. Their bad stretches arrive together, so it adds no safety.

## Caveats

- **CFD data, not futures.** The prices are Dukascopy CFDs, not futures
  prints. There is no exchange volume, and the costs are estimates.
- **Fixed sessions.** Each market was tested in fixed New York hours
  (09:30 for indices, 09:00 for energy, 08:30 for gold, bonds and FX). A
  currency's busiest hours, the London morning, were not tested.
- **The stand-ins are optimistic.** They assume every extra edge would be
  exactly as good as Bot A and fully unrelated to it.
