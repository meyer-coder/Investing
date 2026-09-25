# The "Three MNQ Setups": do they work outside the day they came from?

Run with `python research/three_setups.py`. Numbers are from 2026-09-25,
after the close.

## What was tested

These are the three 5-minute setups from the "Three MNQ Setups" document:

| Setup | Side | What it looks for |
|---|---|---|
| A. Rejection short | short | A second candle sold at the recent top |
| B. Failed breakdown long | long | Support is swept and reclaimed, then a strong green candle |
| C. Failed breakout short | short | A new session high is made, then lost |

The trade rules are the same for all three:
- 2 MNQ, with a 30-point stop and a 45-point target.
- $0.75 a contract a side, plus a tick of slippage on the entry and on the
  stop.
- At most 6 trades a day, a −$600 day stop, and flat at 15:55.

The document derived the thresholds from 2026-09-25 and checked them on six
sessions of 1-minute data: 7 trades, +$336.

**How the test code was checked:**
- `signal()` in `research/three_setups.py` is copied unchanged from the
  document's `setups.py`.
- A rebuild of that `setups.py`, run on Yahoo's 1-minute MNQ=F data together
  with `strategies/instinct/trader.py` from the `profitable-strategies`
  branch, reproduces the document's table exactly: 7 trades, 4 won, +$336.
- The 5-minute replay used here also reproduces all 7 of those trades, with
  the same entries, prices and outcomes. With a 30/45 bracket no 5-minute
  bar touched both the stop and the target, so the 5-minute bars lose
  nothing.

## Result

Data: Yahoo MNQ=F 5-minute bars, 44 regular sessions from 2026-07-17 to
2026-09-25. The expiry week was dropped because the continuous contract
switches then.

| | Trades | Won | Net |
|---|---|---|---|
| The day the rules came from (Sep 25) | 4 | 3 (75%) | +$407 |
| **Every other day (43 sessions)** | **33** | **12 (36%)** | **−$480** |
| &nbsp;&nbsp;A. Rejection short | 3 | 0 | −$372 |
| &nbsp;&nbsp;B. Failed breakdown long | 12 | 4 | −$284 |
| &nbsp;&nbsp;C. Failed breakout short | 18 | 8 | +$176 |
| Other days, expiry week kept (49 sessions) | 39 | 14 (36%) | −$622 |

**Against chance.** 500 random-entry bots ran on the same 43 days. They used
the same bracket, trade count, 36%/64% long/short mix, time window and daily
limits. Their median was −$236, and the middle 80% ran from −$1,286 to
+$863. **The setups beat only about 35% of them.**

**Break-even.** With a 30-point stop and 45-point target the setups need to
win about 41% of trades. Outside the rules day they won 36%.

## What this means

- **Outside the one day they were read from, the setups lost money and did
  worse than random entries.** That is the standard result for rules fitted
  to a single day.
- **Setup C** was the only one in profit (+$176 on 18 trades). That is far
  too few trades to separate from luck.
- **Setup A** fired only 3 times in 43 days. Its four conditions together
  describe Sep 25 more than a repeating pattern.
- **Limits of this test.** It covers 44 sessions of a rising market (MNQ
  +7.5%), and two of the three setups are shorts. A fair verdict needs a
  year or more of 1-minute data, with the setups fixed *before* looking at
  it.

## 13 years of minute data: can the setups be refined?

**No.** `research/refine_setups.py` searched variants on Dukascopy's
one-minute Nasdaq-100 data (see `research/bot-a-accounts-findings.md` for
the data check). The protocol was fixed before any result was seen:
- **Search** on 2013-2019 (1,715 sessions).
- **Confirm** on 2020-2022 against random entries.
- **Final look** at 2023-2026, once.

**The variants tried (384 in all):**
- **Setups:** each setup alone, their mirror images, and A+B+C together.
- **Volume:** the volume conditions on or off.
- **Time of day:** all day or mornings only.
- **Exits (16):** the document's bracket scaled to today's price; stops of
  1-2 ATR with targets of 1-3x the stop; or no target, held to the close.

**What the search found (2013-2019):**
- **Nothing cleared the bar.** No variant had 100+ trades, a positive mean
  and t ≥ 2. About 9 would by luck alone.
- **Almost nothing was even positive.** Only 3 of 384 had a positive mean
  after costs. The best, B' (the mirror of B) with a 2 ATR stop and a 1.5R
  target, made +0.54 bp a trade with t = 0.3, which is no different from
  zero.
- **The document's own rules** made 1,269 trades, −1.13 bp a trade after
  costs (about −$14 a trade on 2 MNQ), t = −3.3. Before costs they made
  −0.13 bp.

Nothing reached the confirm stage.

**What it means.** These setups have no edge on 13 years of NQ minutes, not
even before costs, and no nearby version does. They are reversal trades:
fading a failed break or a rejection. The branch's liquidity-sweep study
(`futures/breakout-bot` on profitable-strategies) found the same for sweeps.
What does hold up on the same data is the opposite style, Bot A's breakout
(see `research/bot-a-accounts-findings.md`).
