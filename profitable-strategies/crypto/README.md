# Crypto: AAVE, BNB, BTC, INJ and MSTR

As of 2026-09-25. Backtests on daily bars, not advice. Paper only.

**Can they be traded at a profit? Yes, by following the trend, not with our
Micron rules.**

- **Trend and breakout rules have a real edge on crypto.**
  - The rules:
    - in while the close is above its 20-, 50- or 100-day average;
    - or in on a new 20- or 55-day high, out on a 10- or 20-day low.
  - The test: 29 coins, 2017 to September 2026, 611 to 4,210 trades a rule.
  - They beat random entries on the same coins, held just as long, by 1.5%
    to 6% a trade (p < 0.005).
  - They made money on 93-100% of the coins. On the five here, the best of
    them cut the deepest fall from 80-95% (holding) to 59-79%.
- **Our Micron rules do not carry over.** D609, CB51, CBE3 and FBB5 were
  within 0.3% a trade of random entries on these coins (p = 0.10 to 0.81).
- **In dollars the trend rules roughly match holding.** What they add is
  getting out of the long bear markets (2018, 2022), not beating a bull
  market.
- **Variety.** The five together under the 50-day trend rule, $5,000 each:
  - $38 a day since 2021, Sharpe 1.04;
  - a deepest fall of -56% and a worst losing stretch of -$18,223;
  - a daily correlation of only +0.16 with the three Micron bots;
  - 15% of its dollars made on weekends.

## Each of the five

The whole $25,000 in the one asset, no leverage. Signals are taken on the
close (00:00 UTC for the coins) and filled at the next open. Costs are 10 bp
a side for the coins and 2 bp for MSTR (`strategies/crypto/study.py`, all
rows in `study.json` there).

| Asset (from) | Holding: $ a day, Sharpe, deepest fall | 50-day trend | Best simple rule | Our best Micron rule |
| --- | --- | --- | --- | --- |
| BTC (2017) | $47, 0.85, -83% | **$46, 1.14, -59%** | the 50-day trend | CBE3: $37, 0.96, -69% |
| BNB (Nov 2017) | $76, 0.97, -80% | $62, 1.05, -67% | 20-day trend: $68, 1.09, -70% | CBE3: $34, 0.69, -63% |
| AAVE (Oct 2020) | $52, 0.58, -92% | $40, 0.64, -79% | the 50-day trend | none made money |
| INJ (Oct 2020) | $81, 0.77, -95% | $46, 0.61, -92% | 20-day trend: **$78, 1.02, -74%** | CBE3: $42, 0.84, -69% |
| MSTR (2017) | $51, 0.67, -89% | $30, 0.57, -81% | 200-day trend: $48, 0.80, -69%; the dip rule: $34, **1.00, -29%** | CBE3: $42, 0.83, -57%; D609: $41, 0.82, -56% |

**By asset:**

- **BTC is the cleanest.** Every trend length from 20 to 200 days and both
  breakouts had a Sharpe of 0.9 to 1.1, against 0.85 for holding.
- **BNB is similar.**
- **INJ and AAVE are the wildest.** INJ held fell 95% at its worst and AAVE
  92%.
  - The 20-day trend kept INJ's worst fall to 74%.
  - Nothing made AAVE much better than holding it.
- **MSTR is Bitcoin at about 1.8 times.**
  - The Micron rules do as well there as the trend rules.
  - The dip rule never fell more than 29%, and made less. It buys a 10% fall
    over three days above the 100-day average, and sells after five days
    or 8% up.

**The five together, the 50-day trend, $5,000 each, by year:** $98 a day in
2021, -$30 in 2022, $80 in 2023, $43 in 2024, $4 in 2025 and $28 in 2026 so
far.

## The rules on 29 coins

Per trade, on log returns (a plain average would be one coin's one trade:
single trades ran from -90% to +10,000%), 2017 to September 2026.

| Rule | Trades | Mean trade | Random entries | Edge, p | Coins profitable | Better Sharpe than holding |
| --- | --- | --- | --- | --- | --- | --- |
| 20-day trend | 4,210 | +1.45% | -0.06% | +1.5%, 0.000 | 93% | 76% |
| 50-day trend | 2,428 | +2.07% | +0.04% | +2.0%, 0.000 | 97% | 62% |
| 100-day trend | 1,648 | +1.74% | +0.11% | +1.6%, 0.004 | 97% | 45% |
| 200-day trend | 1,107 | +0.14% | +0.44% | -0.3%, 0.64 | 93% | 34% |
| Breakout 20/10 days | 1,542 | +3.69% | +0.13% | +3.6%, 0.000 | 100% | 62% |
| Breakout 55/20 days | 611 | +6.47% | +0.51% | +6.0%, 0.000 | 97% | 62% |
| Dip, 10% in 3 days | 1,065 | +1.43% | -0.17% | +1.6%, 0.000 | 90% | 24% |
| D609 | 3,418 | -0.11% | -0.07% | -0.04%, 0.59 | 72% | 14% |
| CB51 | 4,289 | -0.20% | +0.00% | -0.2%, 0.81 | 72% | 7% |
| CBE3 | 2,754 | +0.40% | +0.10% | +0.3%, 0.12 | 86% | 24% |
| FBB5 | 3,176 | +0.17% | -0.04% | +0.2%, 0.10 | 79% | 21% |

- **The typical trend trade loses.** The median trade is -3% to -5%; a few
  big runs carry the rule, which is how trend following works.
- **Expect streaks of small losses.**

**Caveats:**

- **Fees matter.** 10 bp a side is a low-fee exchange's taker rate. At a
  retail app's 0.4% to 0.6% a side, the 20-day trend's 10-15 round trips a
  year per coin cost several percent a year.
- **Survivorship.** The 29 coins are today's large ones; coins that died are
  not in the sample.
- **Recent years are thin.** Crypto has been weak since 2025, and the rules
  made little then.
- **Bad data dropped.** Yahoo's first AAVE and ICP bars are not real prices,
  and SHIB is priced at zero for hundreds of days, so those bars and SHIB
  were left out.
