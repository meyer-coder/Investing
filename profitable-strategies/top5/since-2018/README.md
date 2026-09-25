# D609, CB51 and CBE3 from 2018: 20,000+ trades each

As of 2026-09-25 (the last close is 2026-09-24). Backtests on daily bars,
not advice. Paper only.

**The answer: don't release them as edges.**

- **Each made money since 2018, but only because the funds went up.**
  - Every trade was simulated through the engine: the rule reads the close,
    the order fills at the next open, 8 bp of slippage a side, and the
    genome's own stops.
  - Random entry days on the same funds, held just as long, made more a
    trade than all three rules.
- **Holding beat the rules on almost every fund.** On the other funds each
  rule was tested on, holding made more on 92-95% of them.
- **Their dollars since 2018 are mostly Micron's last 21 months.**
  - All three made $260-550 a day in 2025-2026.
  - Each had losing years before that: D609 in 2018, 2021 and 2023; CB51
    in 2018 and 2022; CBE3 in 2018, 2022 and 2024.
- **None of them can go on your funded accounts.**
  - They trade the ETFs MUU and SOXL and hold for days.
  - Topstep and FundedNext Futures allow only CME futures, flat by 3:10 PM
    Chicago each day.
  - Even on a plain $25,000 account, each lost more than $2,000 at the close
    on 55-113 days since 2018. The first time was in January or February
    2018.

| | D609, MUU Trend Breakout | CB51, MUU / SOXL Uptrend Dip | CBE3, MUU / SOXL Uptrend Dip |
| --- | --- | --- | --- |
| **Trades since 2018, 257 funds** | 25,053 | 37,606 | 30,354 |
| **Average trade** | +64.1 bp (95%: +49 to +79) | +75.9 bp (+63 to +89) | +58.7 bp (+46 to +72) |
| **Random days, same funds and holds** | +71.6 bp | +78.9 bp | +81.2 bp |
| **Timing edge** | -7.5 bp a trade (p = 0.84) | -3.1 bp (p = 0.69) | -22.5 bp (p = 1.0) |
| **At 3x / 5x the slippage** | +32.1 / +0.1 bp | +43.9 / +11.9 bp | +26.7 / -5.3 bp |
| **Funds where it made money** | 65% | 80% | 70% |
| **Funds where it beat holding** | 8% | 8% | 5% |
| **Its own funds, $25,000: $ a day** | $94 (holding: $95) | $101 (holding: $93) | $81 (holding: $93) |
| **Sharpe** | 1.38 | 1.26 | 1.13 |
| **Worst day** | -$6,596 | -$7,628 | -$7,628 |
| **Worst losing stretch** | -$25,851 | -$29,427 | -$30,328 |
| **Days losing over $1,000 / $2,000 / $3,000** | 205 / 55 / 15 | 289 / 113 / 38 | 218 / 90 / 25 |
| **$ a day by year, 2018 to 2026** | -58, 44, 60, -9, 6, -8, 96, 285, 550 | -20, 64, 181, 69, -50, 113, 29, 262, 323 | -2, 3, 111, 18, -25, 103, -1, 301, 269 |

**How to read it:**

- **The rules are not fragile.**
  - Every number in them moved 20% either way stays profitable, on their
    own funds and on 25 others.
  - So they are not a curve-fit accident. They are long leveraged funds
    about half to three-quarters of the time.
- **They don't pick good days.** The same number of random entries on the
  same funds, held just as long, made as much or more.
- **The losing stretches are near a full account.** A worst stretch of
  -$26,000 to -$30,000 on $25,000 means the account would have been wiped
  out along the way without new money.
- **As paper bots,** they are a leveraged bet on Micron and chips staying
  strong. That is what holding MUU or SOXL does, with smaller losing
  stretches than holding: -$26,000 to -$30,000 against -$37,000 to
  -$39,000.

**How it was run** (`strategies/top5/since2018.py`, results in
`strategies/top5/since2018.json` and a folder per bot here with every trade):

- **The test:** `rigor.py`'s test, unchanged, from 2018-01-02 to the last
  close.
- **The funds:**
  - the bots' own funds (2x Micron, which matches MUU, plus SOXL);
  - `rigor.py`'s 173 synthetic funds;
  - synthetic 2x funds on 91 more large US stocks, so each rule clears
    20,000 trades. On the 173 alone, D609 had 16,812.
  - JNPR, BK and MMC no longer download and are left out.
- **The checks:**
  - random timing, 500 times;
  - three and five times the slippage;
  - every number in the rules nudged 20% either way;
  - the own-fund trades reshuffled 2,000 times.
- **Survivorship:** the funds are today's large caps. That flatters
  anything that buys, and the random entries share the same flattery.
- **The data:** Yahoo daily bars, built fresh in this container on
  2026-09-25.
