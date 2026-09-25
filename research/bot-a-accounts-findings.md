# Bot A (the NQ noise-area breakout): checked, and run on the 25K and the 100K

Written 2026-09-25. Data: Dukascopy's one-minute Nasdaq-100 CFD, 3,387
regular sessions from 2013-01 to 2026-09 (`research/duka.py`). In every
month from 2024-05 to 2026-09 its hourly returns line up with Yahoo's NQ
futures at a correlation of 1.00, with no time shift.

## 1. The branch's Bot A numbers hold up

`research/noise_breakout.py` re-implements Bot A from its written rules
(Zarattini and Aziz's noise-area breakout, a 0.30% stop, checks every 30
minutes). It does not reuse the branch's code.

| | profitable-strategies branch | This re-implementation |
|---|---|---|
| Trades | 3,171 | 3,211 |
| $ a day, 1 MNQ at today's price | $21 | $20.3 |
| 2013-2019 / 2020-2026 / last 3 years | $17 / $25 / $16 | $16.0 / $24.7 / $16.8 |
| Sharpe / t | 1.17 / 4.2 | 1.14 / 4.2 |
| Worst losing stretch | −$5,678 | −$5,678 |

Year by year, in $ a day, the two versions agree within $3:

| Year | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| This version | −2 | +20 | +11 | +4 | +7 | +72 | +1 | +10 | +22 | +46 | +40 | +28 | +18 | +4 |

**A bug found on the way.** The first run dropped 27 of the most violent
real days of 2025-2026 (e.g. 2025-04-09, 2025-10-10, 2026-07-29). A
"broken data" rule meant for Yahoo's contract switches flagged their
one-minute jumps as errors, which pulled 2025 down to −$19 a day.
- The rule is now a share of the price (0.8%), above the largest real
  one-minute jump seen (0.7%).
- It is switched off for the CFD, which has no contract rolls.
- The Yahoo results reported earlier were re-checked: they drop exactly the
  same days as before.

## 2. The FundedNext Legacy 25K against the Topstep 100K

`research/accounts_compare.py` runs every fifth session as a fresh start.
Each run lives two years: challenge, funded account, and a new challenge
after every loss. Every fee is counted. Trades are priced at today's NQ
level, with 1 bp of costs a round trip.

**The account rules** (`shortbot/config.py`, from the firms' pages on
2026-09-25):
- **FundedNext Legacy 25K:**
  - $79.99 a challenge, $73.99 a reset.
  - A $1,250 target, with the 40% best-day rule.
  - A $1,000 end-of-day trailing loss limit and no daily limit.
  - 80% of profits to you, after 5 days of $100+ and $500+ profit since
    the last payout.
  - At most half the profit and $3,000 per payout.
- **Topstep 100K:**
  - $99 a month, and $149 on passing.
  - A $6,000 target, with the 55% best-day rule.
  - A $3,000 end-of-day trailing loss limit and a $2,000 daily limit that
    ends the day.
  - On the funded account, 90% to you after 5 winning days of $150+.
  - At most half the balance and $3,000 per payout (current terms for new
    traders).

The table shows the median net a year, with starts from 2013-2019 on the
left of the `|` and starts from 2020-2024 on the right. The first two
columns keep one max loss in the account after each payout; the last
column takes the most allowed. After the first payout the balance is the
only cushion on both firms, so how much you leave matters.

| Size | FundedNext 25K, keep $1,000 | Topstep 100K, keep $3,000 | Topstep 100K, take the most |
|---|---|---|---|
| 1 MNQ | −$65 \| +$1,395 | −$1,054 \| +$1,608 | −$1,133 \| +$767 |
| 2 MNQ | +$224 \| +$3,735 | **+$374 \| +$5,654** | +$509 \| +$2,483 |
| 3 MNQ | −$598 \| +$2,937 | +$402 \| +$4,514 | +$307 \| +$4,180 |
| 4 MNQ | −$1,202 \| +$3,871 | +$529 \| +$6,868 | +$933 \| +$6,855 |

**How often funded accounts were lost within three months:**

| Size | FundedNext 25K | Topstep 100K, keep $3,000 |
|---|---|---|
| 1 MNQ | 65-71% | 1-12% |
| 2 MNQ | 89-90% | 36-39% |
| 4 MNQ | 93-95% | 78-79% |

**What it says:**
- **The best setting found is the Topstep 100K at 2 MNQ, keeping $3,000
  after each payout.** On 2020-2024 starts it made a median +$5,654 a year,
  with only 7% of runs ending below zero. On 2013-2019 starts it made
  +$374, with 43% below zero.
- **The FundedNext 25K cannot keep a funded account.** The $1,000 limit is
  less than one bad NQ day at 2 MNQ. It pays only as throwaway accounts,
  bought again and again.
- **Bot A barely paid on 2013-2019 starts on either account**, when it made
  $16 a day at 1 MNQ. All the good numbers come from 2020 onward.

## 3. Can the 25K strategy be 4x-ed on the Topstep 100K?

No:
- **The room is 3x, not 4x.** The loss limit is $3,000 against $1,000, and
  the target is 4.8x ($6,000 against $1,250).
- **At the same 2 MNQ, the 100K made about 1.5x the 25K** (+$5,654 against
  +$3,735 a year on 2020-2024 starts), and it kept funded accounts far
  longer.
- **Four times the size (4 MNQ) made +$6,868,** only a little more than 2
  MNQ, while losing 78% of funded accounts within three months.

## 4. Does sizing by the day's volatility help?

No. `research/size_bot_a.py` tried six sizing rules, all fixed before any
result was seen:
- fixed 1 or 2 MNQ;
- volatility-scaled with a base of 1, 2 or 3. Contracts = base × (median
  daily range of the prior year ÷ average daily range of the prior 14
  sessions), from 0 to 4. That means fewer contracts on wild days and more
  on calm ones;
- volatility-scaled base 2, with no more trades that day after a losing
  trade.

The account is the Topstep 100K funded account, keeping $3,000 after each
payout. A rule was chosen on 2013-2022 starts (most paid, with at least 80%
of one-year funded runs surviving) and judged on 2023-2026 starts.

Each cell shows three numbers:
- the share of one-year funded runs that survive;
- what is paid to you a day;
- the two-year plan's median a day, after fees.

| Rule | Avg MNQ | 2013-2022 (choose) | 2023-2026 (judge) |
|---|---|---|---|
| Fixed 1 MNQ | 1.0 | 68% · $9.4 · −$2.6 | 74% · $11.3 · +$1.8 |
| Fixed 2 MNQ | 2.0 | 18% · $16.0 · +$5.5 | 52% · $20.2 · +$2.4 |
| Vol-scaled, base 1 | 1.0 | 81% · $7.3 · −$4.2 | 57% · $9.1 · −$4.4 |
| Vol-scaled, base 2 | 1.9 | 16% · $11.3 · +$2.1 | 28% · $22.8 · +$11.7 |
| Vol-scaled, base 3 | 2.8 | 3% · $11.3 · +$8.6 | 13% · $22.4 · +$28.0 |
| Vol-scaled base 2 + stop after a loss | 1.9 | 14% · $8.2 · −$2.0 | 22% · $13.6 · +$3.8 |

**What it says:**
- **The chosen rule, vol-scaled base 1, did worse on the unseen years than
  plain 1 MNQ.** It kept 57% of accounts against 74%, and paid $9.1 a day
  against $11.3. Scaling by volatility is not worth the complexity.
- **Bigger sizes pay more a day, but they lose most funded accounts.** The
  two-year plan's median can still be positive, because each lost account
  is bought again. That is a lottery, not an income.
- **On one Topstep 100K, Bot A pays about $10-20 a day before fees**
  (1-2 MNQ). After fees, the two-year plan's median is only a few dollars
  a day.

## Differences from the branch's own table

The branch reports more for the Topstep 100K, e.g. +$3,485 | +$8,680 a year
at 2 MNQ. It assumed Topstep's older payout terms: 100% of the first
$10,000, then 90%, and up to $5,000 a payout. Traders who joined after
2026-01-12 get 90% from the first dollar, and the 100K's payout cap is
$3,000 (doubled only under a limited-time offer). Which terms apply depends
on when the account was opened.

## Caveats
- **Not the futures.** The data is Dukascopy's index CFD. It follows NQ
  minute for minute, but there is no exchange volume, and the 1 bp costs
  are rough.
- **Scaling plan not modelled.** Topstep's funded-account contract limits by
  balance are not in the simulation.
- **Overlapping runs.** The two-year runs overlap, so each column is a
  handful of independent histories, not hundreds.
