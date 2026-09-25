# Candle-move study: do big NQ/MNQ moves continue or snap back?

Run: `python research/candle_moves.py` (the numbers below are from 2026-09-25).
Data: Yahoo NQ=F. MNQ trades at the same price, at $2 per point. Costs are
charged at 1.1 points ($2.20) per round turn.

## 1. When do the big drops happen? (5-minute bars, 49 sessions, Jul 17 – Sep 24 2026)

| Time (NY) | Normal 5-min candle | $/MNQ | Share of the worst 2% of drop candles |
|---|---|---|---|
| 09:30–10:00 | 76 pts | $152 | **42%** |
| 10:00–10:30 | 58 pts | $117 | 14% |
| 10:30–11:00 | 49 pts | $97 | 10% |
| 11:00–12:00 | 38–42 pts | $76–85 | 10% |
| 12:00–15:00 | 24–32 pts | $49–64 | 9% |
| 15:00–16:00 | 27–33 pts | $54–66 | 14% |

- Two-thirds of the sharpest selloff candles came in the first hour.
- Midday candles are about a third the size of opening candles.
- A "big" move therefore has to be judged against the normal size for that
  time of day.

## 2. After a fast 15-minute drop, did buying work? (same 49 sessions)

- **Setup:** price fell 1.5 normal candles in 15 minutes. Buy at the next
  bar and hold 60 minutes.
- **Result:** +27 points average (+$52 per MNQ after costs), 66% winners,
  71 trades, t = 3.1. Both halves of the period were positive.
- **Why it's suspect:** MNQ rose from about 27,300 to 31,000 over these
  weeks, so buying dips was bound to look good. The mirror trade (shorting
  15-minute rallies) made nothing. About 70 variations were tried. Treat it
  as dip-buying in an uptrend until more data says otherwise.

## 3. Day already moved 0.5–1× its normal range: fade it to the close? (hourly, 587 sessions, May 2024 – Sep 2026)

- **Result:** every variant lost money after costs, with |t| ≤ 1.5.
- **Meaning:** days that move a lot tend to keep moving, so fading them into
  the close did not pay.

## 4. Two-year check on hourly candles (587 sessions)

The trigger was one hourly candle of at least 2× the normal size for that
hour, with the position held for 1 hour.

| Trade | Trades | Avg pts | Winners | Notes |
|---|---|---|---|---|
| **Short after a big hourly drop** (go with it) | 25 | **+58** | 14 of 25 | Spread over 17 different months. Still +581 pts total after removing the best 3 trades. |
| Short after a big hourly rally (fade it) | 19 | +70 | 12 of 19 | Almost all from 3 trades, two of them Fed-day reversals (2026-07-29: +721 pts). Without the best 3: +112 pts. Fragile. |
| Buy after a big hourly drop (fade it) | 25 | −58 | 11 of 25 | The mirror of the first row: drops kept falling. |

- **Most promising lead:** big hourly drops tended to *continue*, and
  shorting them was positive across 2024, 2025 and 2026.
- **Weakness:** 25 trades is far too few to call it an edge.
- **News risk:** Fed announcement days (2 PM ET) produced the largest moves
  in both directions.

## What this does and does not show

- It shows where to look. Short-side momentum after large hourly drops is
  the best candidate so far, and fading whole-day moves is the worst.
- It does not show a tradable edge yet:
  - The samples are small.
  - Many variants were tested.
  - Nothing here yet includes the Topstep trailing drawdown, the daily loss
    limit or a flat-by-3:10 PM CT exit.
- Next step: get several years of 5-minute or 1-minute MNQ history and test
  "short after a big drop" with stops, inside the Topstep 50K rule
  simulator, on data the rules were not tuned on.
