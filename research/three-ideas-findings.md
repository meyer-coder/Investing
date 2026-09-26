# Gold round numbers, crude z-score, euro EMA crossover

Run with `python research/three_ideas.py`. Numbers are from 2026-09-25,
after the close.

## What was tested

Three ideas from the owner. Each rule set was written down before any
result was seen. The full rules are in the script's docstring. Times are
New York time; "NY PM" means 13:30-16:00, and every trade is flat by 15:55.

**1. Gold round-number reaction** (XAU/USD traded as MGC, 15-minute bars,
NY PM):
- **Signal:** a 15-minute bar that trades up to the next round number above
  its open and closes back below it is a short. The mirror image (down to
  the round number below, close back above) is a long.
- **Trade:** one per day, entered at the next bar's open.
- **Stop and target:** the stop is a tick past the bar's extreme. The target
  is 1R or 2R.
- **Versions:** round numbers every $10 or every $50, each with a 1R or a 2R
  target.

**2. Crude z-score reversion** (WTI traded as MCL, 15-minute bars, all
sessions from 18:00 to 15:55):
- **Signal:** z = (close − average of the last N closes) ÷ their standard
  deviation. At z ≤ −T, buy; at z ≥ +T, sell short.
- **Exit:** on a close back across the average, at a stop 2 standard
  deviations away, or at 15:55.
- **Versions:** N = 20 or 40 bars, each with T = 2.0 or 2.5.
- **Contract rolls:** the z-score only uses the current trading day's bars.
  That keeps out the contract-roll jumps at the 18:00 reopen.

**3. Euro EMA crossover** (EUR/USD traded as M6E, 3-minute bars, NY PM):
- **Signal:** trade in the direction of the fast EMA crossing the slow one.
- **Versions:** 9/21 or 20/50 EMAs. Each is run two ways: reverse on every
  cross, or trade only the day's first cross and exit on the next opposite
  cross.

**Costs.** The micro contract's commission plus a tick of slippage each
way:
- gold: 0.75 bp a round trip;
- crude: 3.48 bp;
- euro: 2.60 bp.

For comparison, results are also shown for the full-size contract, at an
assumed $4 commission plus a tick each way. That costs 0.56, 2.60 and 1.16
bp.

**Protocol.** The same as the other studies:
1. **Search, 2013-2019.** A version passes with 100+ trades, a positive mean
   and t ≥ 2.
2. **Confirm, 2020-2022.** Still positive, and beats 90% of random sign
   flips.
3. **Final look, 2023-2026.** Looked at once.

## Result: none of the 12 versions passes

| Version | Trades | Before costs, bp a trade (search / confirm / final) | After micro costs, search | Verdict |
|---|---|---|---|---|
| Gold $10, 1R | 1,400 | +0.63 / −0.54 / +0.70 | −0.12 bp, t −0.2 | failed |
| Gold $10, 2R | 1,400 | +0.79 / −0.32 / +0.16 | +0.05 bp, t +0.1 | failed |
| Gold $50, 1R | 346 | −1.95 / +0.11 / +0.32 | −2.69 bp, t −1.6 | failed |
| Gold $50, 2R | 346 | −1.11 / +0.74 / +0.26 | −1.86 bp, t −1.0 | failed |
| Crude 20 bars, z 2.0 | 14,892 | −0.10 / +0.02 / +1.42 | −3.59 bp, t −4.7 | failed |
| Crude 20 bars, z 2.5 | 7,834 | +0.31 / −1.78 / +3.46 | −3.17 bp, t −2.9 | failed |
| Crude 40 bars, z 2.0 | 9,514 | −1.04 / −1.24 / +0.90 | −4.52 bp, t −3.7 | failed |
| Crude 40 bars, z 2.5 | 6,380 | −1.67 / +0.21 / +0.85 | −5.15 bp, t −3.5 | failed |
| Euro 9/21, reverse | 6,417 | −0.35 / −0.04 / +0.07 | −2.96 bp, t −20.5 | failed |
| Euro 9/21, first cross | 2,947 | −0.46 / +0.06 / −0.14 | −3.07 bp, t −13.4 | failed |
| Euro 20/50, reverse | 2,586 | −0.43 / +0.20 / −0.13 | −3.04 bp, t −11.6 | failed |
| Euro 20/50, first cross | 1,774 | −0.53 / +0.46 / −0.09 | −3.13 bp, t −9.4 | failed |

**Before costs, all three ideas are close to zero.**
- **Gold:** its round-number trades averaged under 1 bp a trade either way.
  Even on the cheaper full-size contract none is reliably positive.
- **Crude:** before costs its z-score trades averaged between −1.8 and
  +3.5 bp a trade. Each round trip costs 3.5 bp on the micro and 2.6 on the
  full-size, so every version loses.
- **Euro:** the EMA crossover is essentially zero before costs (±0.5 bp).
  It trades often, so the 2.6 bp cost makes it lose steadily. That is what
  the large negative t values show.

**On 1 micro, the results are:**
- crude 20 bars, z 2.0: lost about $21,000 over 2013-2019;
- euro 9/21, reverse: lost about $14,000 over 2013-2019;
- gold: close to flat.

## What it means

None of the three has an edge on 13 years of minute data. The two that trade
often (crude and euro) lose steadily to costs. This fits everything else
found so far:
- fading moves in a market doesn't pay after costs (the Judas swing, the
  three setups, now crude reversion and gold rejections);
- simple indicator crossovers are noise;
- the one idea that has held up is Bot A, the Nasdaq breakout.

## Caveats

- **CFD data, not futures.** The prices are Dukascopy CFDs.
- **Crude contract rolls** are kept out of the z-score, but the crude CFD's
  prices around them are rougher than the index data.
- **Mechanical versions only.** Rules that include judgment calls were not
  tested.
