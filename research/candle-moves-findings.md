# Candle-move study: do big NQ/MNQ moves continue or snap back?

Run it with `python research/candle_moves.py`. The numbers below are from
2026-09-25, after the bug fixes listed at the end.

**Data:** Yahoo NQ=F. MNQ trades at the same price, at $2 per point.

**Days removed before testing:**
- The week of each quarterly expiry, when Yahoo's continuous series mixes
  two contracts.
- Days with broken price jumps.
- Today's unfinished session.

**Costs:** 1.1 points ($2.20) per round turn. "Win" means the trade made
money *after* costs.

## 1. When do the big drops happen?

5-minute bars, 44 sessions, 2026-07-17 to 2026-09-24.

| Time (NY) | Normal 5-min candle | $/MNQ | Share of the worst 2% of drop candles |
|---|---|---|---|
| 09:30–10:00 | 80 pts | $159 | **44%** |
| 10:00–10:30 | 61 pts | $121 | 16% |
| 10:30–11:00 | 50 pts | $101 | 12% |
| 11:00–12:00 | 38–44 pts | $76–88 | 10% |
| 12:00–15:00 | 25–33 pts | $51–66 | 6% |
| 15:00–16:00 | 27–33 pts | $54–66 | 13% |

- **59%** of the sharpest selloff candles came in the first hour
  (09:30–10:30).
- Midday candles are about a third the size of opening candles.
- So a "big" move has to be judged against the normal size for that time
  of day.

## 2. After a fast 15-minute drop, did buying work?

Same 44 sessions.

- **Setup:** price fell 1.5 normal candles in 15 minutes. Buy at the next
  bar and hold 60 minutes.
- **Result:** +24.7 points average (+$47 per MNQ after costs), 64% winners,
  70 trades, t = 2.55. Both halves of the period were positive (+24.3 and
  +24.9).
- **Why it's suspect:**
  - MNQ rose 7.5% over these weeks (28,607 at the first open to 30,757 at
    the last close), so buying dips was bound to look good.
  - The mirror trade (shorting 15-minute rallies) made nothing.
  - About 70 variations were tried.
- Treat it as dip-buying in an uptrend until more data says otherwise.

## 3. Day already moved 0.5–1× its normal range: fade it to the close?

Hourly bars, 545 sessions, May 2024 – Sep 2026, measured from the 09:00
price.

- **Result:** every variant lost money after costs, with |t| ≤ 1.35.
- **Meaning:** days that move a lot tend to keep moving, so fading them into
  the close did not pay.

## 4. Two-year check on hourly candles

545 sessions. The trigger was one hourly candle of at least 2× the normal
size for that hour, starting at or after 10:00 (never the 09:00 bar, which
includes pre-market trading). The position was held for 1 hour.

| Trade | Trades | Avg pts | Winners after costs | Notes |
|---|---|---|---|---|
| **Short after a big hourly drop** (go with it) | 26 | **+40** | 14 of 26 | Positive in 2024 (+34), 2025 (+26) and 2026 (+102). Spread over 16 months. Still +417 pts total after removing the best 3 trades. |
| Short after a big hourly rally (fade it) | 18 | +79 | 12 of 18 | Mostly 3 trades, one of them a Fed-day reversal (2026-07-29, +721 pts). Without the best 3: +200 pts. Fragile. |
| Buy after a big hourly drop (fade it) | 26 | −40 | — | The mirror of the first row: drops kept falling. |

- **Most promising lead:** big hourly drops tended to *continue*.
- **Weakness:** 26 trades is far too few to call it an edge (t ≈ 2 before
  accounting for the many variants tried).

## What this does and does not show

- It shows where to look. Short-side momentum after large hourly drops is
  the best candidate so far; fading whole-day moves is the worst.
- It does not show a tradable edge:
  - The samples are small.
  - Many variants were tested.
  - The t-stats are overstated, because trades inside a day are correlated
    and so many variants were tried.

## Corrections made after review (2026-09-25)

**Code bugs:**
- **Off-by-one.** The first 15-minute window of each day (09:30–09:45, the
  most volatile) was never tested, and on hourly bars neither was the first
  bar.
  - Section 2 went from +27.3 pts (t 3.09) to +24.7 (t 2.55).
  - Section 4 "short after a big drop" went from +58 to +40 pts.
- **Contract mix-ups.** Yahoo's NQ=F mixed the December and March contracts
  on 2025-12-16/17, giving 400-point fake bar ranges. Expiry weeks are now
  dropped (42 hourly sessions, 5 five-minute sessions).
- **Unfinished sessions.** Running the script mid-session could include
  today's unfinished day and a stray live-quote row. Both are now dropped.
- **Win rate.** It was counted before costs, while the $ column was after
  costs. Both are now after costs.
- **Exit bar.** The bar a trade exited on could not trigger the next trade.
  Now it can.

**Wrong statements in the earlier version of this document:**
- "Two-thirds of the sharpest drops came in the first hour": it was 56%
  (59% on the cleaned data).
- "Two Fed-day reversals" among the best short-rip trades: only one was a
  Fed day.
- "Every variant had |t| ≤ 1.5": one had t = −1.54 (on the cleaned data
  the largest is 1.35).
- "MNQ rose from about 27,300 to 31,000": those were the low and the high.
  From the first open to the last close it rose 7.5%.
