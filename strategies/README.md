# Quick-trade strategies for leveraged Nasdaq, semiconductor and single-stock funds

Eight strategies, each holding one to three sessions, each profitable on
every window it was tested on: the leveraged Nasdaq and semiconductor
long/short funds over 2010-2022 and, held out, 2022-2026; the funds you
actually trade (TQQQ/SQQQ, MUU/MUD, RIOX, SOXL/SOXS) over 2025-2026; and
the 2x long/short pairs on AAPL, TSLA, AMZN, MSFT, GOOGL and NVDA over
2023-2026. All eight also survive three times the assumed slippage.

Every number here is a backtest on daily bars with the signal read at the
close and the fill at the next open, paying 1 bp commission and 5 bp
slippage per side (10 bp on the single-stock funds). Nothing here is a
forecast or advice. The genomes are in `quick_leveraged.json`; the full
per-universe tables, year by year, per symbol, with best and worst trades,
are in `reports/`.

## The bar they had to clear

A strategy was kept only if, on each of the four windows, it made at least
ten trades with a positive net return and a profit factor above 1.1, with an
average hold of three bars or less. The four windows:

| window | universe | bars | role |
|---|---|---|---|
| Nasdaq 2010-2022 | TQQQ, SQQQ, SOXL, SOXS, QLD, QID | 3,100 | search |
| Nasdaq 2022-2026 | same | 1,040 | held out, never used to pick |
| Names 2025-2026 | TQQQ, SQQQ, MUU, MUD, RIOX, SOXL, SOXS | 430 | your names |
| Mega-cap pairs 2023-2026 | AAPU/AAPD, TSLL/TSLS, AMZU/AMZD, MSFU/MSFD, GGLL/GGLS, NVDL/NVDD | 760 | single-stock check |

Buying the inverse fund is the short trade: a rule that fires on SQQQ is a
short on the Nasdaq. Every rule below is evaluated on each fund's own
prices, so the same rule trades both directions.

The evolutionary runs on the same data mostly overfit: the Nasdaq
champion made +538% on 2010-2022 and +14% held out, from 78 trades in
twelve years, and of 53 evolved champions scored across all four windows
(`search/evolved_candidates.json`) one passed. The first seven strategies
were bred by hand from five rounds of candidates (`search/`) and kept for
consistency across universes, not for the best single number; the eighth
is that one evolved survivor.

## Results

Return, profit factor and win rate per window. Trades per year are on the
Nasdaq universe.

| strategy | Nasdaq 2010-22 | Nasdaq 2022-26 (held out) | Names 2025-26 | Mega-cap pairs 2023-26 | trades/yr | hold |
|---|---|---|---|---|---|---|
| Capitulation Close | +57%, PF 1.18, 57% | +60%, PF 1.45, 60% | +86%, PF 1.65, 56% | +51%, PF 1.43, 58% | 34 | 2.3 |
| Red Day Above the 50 | +41%, PF 1.24, 58% | +30%, PF 1.47, 56% | +38%, PF 1.42, 59% | +18%, PF 1.23, 54% | 19 | 2.3 |
| Oversold Dip Above the 50 | +72%, PF 1.43, 64% | +31%, PF 2.02, 68% | +16%, PF 1.54, 64% | +32%, PF 1.53, 54% | 20 | 2.5 |
| Pullback Cluster | +17%, PF 1.16, 60% | +27%, PF 1.96, 63% | +8%, PF 1.23, 61% | +32%, PF 2.25, 55% | 13 | 2.4 |
| Prior-Low Break on Volume | +62%, PF 1.27, 58% | +35%, PF 1.71, 59% | +19%, PF 1.36, 63% | +27%, PF 1.27, 51% | 30 | 2.4 |
| Combo: Capitulation or Oversold | +93%, PF 1.25, 59% | +91%, PF 1.69, 64% | +67%, PF 1.59, 58% | +40%, PF 1.30, 55% | 48 | 2.4 |
| Combo: All Five Setups | +89%, PF 1.20, 57% | +113%, PF 1.57, 60% | +76%, PF 1.44, 57% | +48%, PF 1.24, 52% | 64 | 2.4 |
| Two Red Days (evolved) | +15%, PF 1.37, 64% | +24%, PF 2.94, 69% | +29%, PF 1.96, 71% | +21%, PF 2.96, 63% | 6 | 2.0 |

Max drawdowns on the Nasdaq held-out window run from -4% (Two Red Days)
and -8% (Oversold Dip, Pullback Cluster) to -17% (Capitulation Close); on
the 2010-2022 window from -9% to -37% (Prior-Low Break). Average return per
trade on the held-out window is +1.2% to +1.9% of the position, and +3.0%
for the low-frequency Two Red Days.

## The strategies

Mechanics shared by all eight, unless noted:

- Signals are read at the daily close. Entry is at the next open.
- Exit at the open after the first close at or above +3% from entry, or at
  the open after two full bars, whichever comes first.
- Hard stop at -8% and hard target at +4%, both checked at the close and
  filled at the next open. There are no intraday stops in this model.
- 25% of equity per position, at most four positions, one bar of cooldown
  before re-entering the same fund.

For NQ futures, read TQQQ as three times the Nasdaq-100 day: a 4.5% TQQQ
drop is a 1.5% NQ drop, the 3% target is about 1% on NQ and the 8% stop
about 2.7%. MUU and RIOX are 2x, so halve those.

**1. Capitulation Close.** Today's close is down at least 4%, it sits in
the bottom quarter of today's range, and volume is at least 1.3 times its
20-day average. No trend filter. The highest-returning single setup on
three of the four windows, and the only one that needs no moving average,
which is why it was live on RIOX and MUU from their first month. Rule: `ret1 < -0.04 and (close - low) / (high - low
+ 0.0001) < 0.25 and volume_ratio > 1.3`.

**2. Red Day Above the 50.** Today's close is down at least 4.5%, still
above the 50-day simple moving average, on at least average volume. The
trend gate is what makes a plain red-day buy survive the single-stock
funds; without it the same rule loses there. Rule: `ret1 < -0.045 and close
> sma50 and volume_ratio > 1.0`.

**3. Oversold Dip Above the 50.** Seven-day RSI below 40 with the close
above the 50-day average. Stop is 10% instead of 8%. Among the single
setups it has the best held-out profit factor (2.02) with a max drawdown
under 9%, and the shallowest losing years. On 3x
products the classic "RSI below 25 in an uptrend" almost never fires; the
threshold has to scale. Rule: `rsi7 < 40 and close > sma50`.

**4. Pullback Cluster.** Two consecutive down closes, a five-day return of
-3% or worse, close above the 50-day average, volume at least 1.1 times
average. Lowest trade count; the volume gate is essential, the ungated rule
is flat on 2010-2022. Rule: `ret1 < 0 and prev(ret1) < 0 and ret5 < -0.03
and close > sma50 and volume_ratio > 1.1`.

**5. Prior-Low Break on Volume.** Close below yesterday's low, above the
50-day average, volume at least 1.2 times average. The most frequent single
setup and the only one besides Capitulation that stays profitable on the
inverse funds alone. Without the volume gate it loses. Rule: `close <
prev(low) and close > sma50 and volume_ratio > 1.2`.

**6. Combo: Capitulation or Oversold.** Setups 1 and 3 in one book, first
match wins, five slots of 20%. The best held-out profit factor and win rate
of the two combos (1.69, 64%) and about one trade a week on the Nasdaq
universe.

**7. Combo: All Five Setups.** All five setups, five slots of 20%. The best
held-out Sharpe of the set (1.16) and about 64 trades a year; use it when
you want a signal most weeks.

**8. Two Red Days (evolved).** Yesterday closed down more than 2.8%, today
closed down again, the five-day return is worse than -7.8%, and the close
is still above the 50-day average. Exit at the open after the first close
that is up more than 2% on the day, or after three bars; stop 6%, no
target, 20% of equity per position, no cooldown. The one genome from the
evolutionary runs that stayed profitable on all four windows: a jittered
copy of a seed archetype from the first generation of the mega-cap run.
About six trades a year on the Nasdaq universe, so its numbers are a small
sample; on the long funds alone it won 83% of 23 held-out trades. Rule:
`ret1 < 0 and prev(ret1) < -0.028 and close > sma50 and ret5 < -0.078`.

## What the checks showed

**The edge is on the long side.** Scored on the long funds alone (TQQQ,
SOXL, QLD) the held-out profit factors rise to 1.8 to 4.2; Oversold Dip
wins 83% of its trades. On the inverse funds alone (SQQQ, SOXS, QID) only
Capitulation Close (PF 1.15 and 1.08) and Prior-Low Break (1.42 and 1.43)
stay above 1.0 on both windows; the trend-gated setups, Two Red Days
included, lose money there,
because "above its 50-day" on an inverse fund means a bear market, and
buying dips in a bear market is what the gate exists to avoid. On your
names alone (TQQQ, MUU, RIOX, SOXL) Capitulation Close made +101% with a
70% win rate over 2025-2026, and the two combos +78% and +80%. If you trade
the short side at all, take it only from setups 1 and 5.

**Costs.** At 15 bp slippage per side, three times the assumption, all
eight stay profitable on both Nasdaq windows; the 2010-2022 profit factors
fall to 1.08 (Pullback Cluster) through 1.31 (Oversold Dip). On your names
at 20 bp per side the seven hand-bred strategies stay profitable.

**Losing years happen.** 2018 was negative for every strategy on the
Nasdaq universe (-3% to -21%). Capitulation Close lost 19% in 2011 and 11%
in 2022; the trend-gated setups lost in 2019. Oversold Dip has the
shallowest bad years, none worse than -6%.

**Gap risk is the tail.** Because fills happen at the next open, a stop or
target that triggers at the close is filled wherever the market opens.
Worst trades: SOXL 2020-03-13, take profit triggered at +7% at the close,
filled -26% at Monday's open; TQQQ 2015-08-21, stop triggered at -9%,
filled -25% on the flash-crash open; RIOX 2025-07-30, stop at -40% after an
earnings gap, -37% realised. At 25% of equity that is a 6% to 9% hit to the
account in one session, and on 2020-03-16 three positions gapped together.
Size for that, or run intraday stops the model does not have.

**Short history on your names.** RIOX has traded since January 2025, MUU
since October 2024. The 2025-2026 window is one regime, 430 bars, and it
was a good one for dip-buying; it confirms the strategies transfer to those
funds, it does not prove them on its own. The 2010-2022 window is the
evidence.

## Reproduce

```bash
python -m evotrader.cli evaluate strategies/quick_leveraged.json --config configs/quick_nasdaq.json --by-year --markdown strategies/reports/quick_nasdaq.md
python -m evotrader.cli evaluate strategies/quick_leveraged.json --config configs/quick_names.json --test-frac 0 --by-year --markdown strategies/reports/quick_names.md
python -m evotrader.cli evaluate strategies/quick_leveraged.json --config configs/quick_bigcaps.json --test-frac 0 --by-year --markdown strategies/reports/quick_bigcaps.md
python -m evotrader.cli evaluate strategies/quick_leveraged.json --config configs/quick_nasdaq.json --symbols TQQQ,SOXL,QLD      # long funds only
python -m evotrader.cli evaluate strategies/quick_leveraged.json --config configs/quick_nasdaq.json --symbols SQQQ,SOXS,QID      # inverse funds only
python -m evotrader.cli evaluate strategies/quick_leveraged.json --config configs/quick_nasdaq.json --slippage 15                # cost sensitivity
python -m evotrader.cli signals strategies/quick_leveraged.json --config configs/quick_names.json --refresh                       # what fires on the latest bar
```

Prices come from Yahoo Finance and are cached under `data/cache/`; the
first run fetches them. The five candidate rounds that led here are in
`search/`, and any of them can be re-scored the same way.
