# How deep can NQ 5-minute history actually go?

Measured against the TradingView feed on 2026-09-22, not estimated. Every number
below came from a direct `get_bars` call.

## The cap is per-symbol and anchored to now

| Request | Result |
|---|---|
| `NQ1!` 5m, `bars=250000` | 5,798 bars — ≈1 month |
| `NQ1!` 5m, `bars=1000` | exactly 1,000 bars, still ending at the present |
| `NQ1!` 15m | 5,413 bars — ≈3 months |
| `NQ1!` 60m | 10,154 bars — ≈1.7 years |
| `CFI:US100` (CFD) 5m | 5,779 bars — ≈1 month |

Two things follow. The cap is a **bar count** (~5.3–5.8k below hourly, ~10k
hourly), not a date — which is why 15m reaches three times further back than 5m
for the same bar budget. And `bars` is only a ceiling: the window always ends at
the present, and the tool exposes no `from`/`to` anchor, so **you cannot
paginate backwards through one symbol.** Asking repeatedly returns the same
recent window.

The CFD rung is worth noting separately: it returns the same one month as the
future, so as a fallback for *depth* it buys nothing. It is a fallback for
*availability* only.

## Expired contracts are individually addressable — this is the batching route

Each quarterly contract keeps its own history, capped the same way but anchored
to **its expiry** rather than to today:

| Symbol | Bars | Span |
|---|---|---|
| `CME_MINI:NQZ2022` | 5,333 | 2022-11-20 → 2022-12-16 |
| `CME_MINI:NQZ2023` | 5,335 | 2023-11-19 → 2023-12-15 |
| `CME_MINI:NQZ2024` | 5,335 | 2024-11-24 → 2024-12-20 |
| `CME_MINI:NQU2025` | 5,369 | 2025-08-24 → 2025-09-19 |
| `CME_MINI:NQZ2025` | 5,201 | 2025-11-23 → 2025-12-19 |

Stable back to at least 2022. So history *can* be batched — across contract
symbols, not across pages.

## What stitching actually buys

Each contract yields ~5,335 bars ≈ **19 trading days** (the month before expiry).
Four expiries a year:

| Stitched | Bars | Trading days | Share of the calendar span |
|---|---|---|---|
| 4 quarterlies (1 year) | 21,340 | 77 | 31% |
| 12 quarterlies (3 years) | 64,020 | 232 | 31% |
| 20 quarterlies (5 years) | 106,700 | 387 | 31% |

Against the 576-variation example grid at a 400-trade floor:

| Data | Variations clearing the floor |
|---|---|
| `NQ1!` continuous only (~1 month) | **0 / 576** |
| 12 quarterlies stitched (3-year span) | 16 / 576 |
| 20 quarterlies stitched (5-year span) | 112 / 576 |
| True continuous 3 years (purchased) | **304 / 576** |

Stitching moves the needle off zero, which is not nothing. It does not get near
what the programme needs.

## The structural problem stitching cannot fix

The covered windows are always the ~26 days before a March, June, September or
December expiry. So coverage by calendar month is:

```
Jan  ---- NO DATA AT ALL        Jul  ---- NO DATA AT ALL
Feb  #### covered               Aug  #### covered
Mar  #### covered               Sep  #### covered
Apr  ---- NO DATA AT ALL        Oct  ---- NO DATA AT ALL
May  #### covered               Nov  #### covered
Jun  #### covered               Dec  #### covered
```

**A third of the calendar is permanently invisible, and adding more years never
fixes it** — more years add more Februaries, never a January. Any month-to-month
seasonality built on stitched data is not merely thin for Jan/Apr/Jul/Oct, it is
empty, and the remaining months are all expiry-adjacent, which is itself an
unusual volume regime. Stitched data is therefore usable as a **regime
robustness check** (does the edge survive 2022's bear, 2023–24's rally,
2025–26?) and unusable as the basis for a seasonality claim.

## Equities and ETFs reach much further than futures

The cap is a bar count, so **a shorter session stretches the same budget over
more calendar time**. Regular trading hours spend ~78 five-minute bars a day
against a future's ~276:

| Symbol | TF | Bars | Bars/day | Trading days | Span |
|---|---|---|---|---|---|
| `NQ1!` | 5m | 5,798 | 276 | 21 | 1.0 month |
| `QQQ` / `SPY` / `NVDA` | 5m | 5,304 | 78 | 68 | **3.2 months** |
| `NQ1!` | 15m | 5,413 | 92 | 59 | 2.8 months |
| `QQQ` | 15m | 5,240 | 26 | 202 | **9.6 months** |
| `NQ1!` | 60m | 10,154 | 23 | 441 | 1.8 years |
| `QQQ` | 60m | 6,500 | 7 | 929 | **3.7 years** |

`QQQ` at 60-minute covers the full 3-year window continuously, with every
calendar month present — which stitched futures contracts can never do. It
tracks the same index as NQ, so for the question "does this edge exist on the
Nasdaq" it is a legitimate instrument, not a compromise.

Caveats worth stating: RTH only, so "around the clock" testing is impossible on
equities; splits-adjusted rather than dividend-adjusted (do not mix with Yahoo
series in one backtest); and day-trading equities under \$25k runs into the
pattern-day-trader rule, which futures do not have.

## Breadth: many symbols instead of many years

Trade counts pool across symbols, so a short window over a wide universe clears
the 400-trade floor that a single instrument cannot. In the 68 trading days a
5-minute equity pull returns, at one signal per symbol per day:

| Variation selectivity | Symbols needed for 400 trades |
|---|---|
| 1.00 (no filters) | 6 |
| 0.50 | 12 |
| 0.25 | 24 |
| 0.07 (heaviest stack in the grid) | 84 |

**This fixes the arithmetic, not the evidence.** Thirty Nasdaq names over one
quarter samples one stretch of history thirty times over, not thirty stretches.
At an average pairwise correlation of 0.55 the basket is worth roughly **2
independent symbols**, not 30 — `n / (1 + (n-1) x rho)`, a conservative bound.
The builder computes this and every generated prompt now demands the effective
figure be quoted next to every pooled trade count, plus per-symbol counts and a
re-run with the top contributor removed.

## Signing in changed nothing — measured, 2026-09-22

The tunnel was signed in with a stored TradingView session
(`~/.config/evotrader/tradingview.json`) and `evotrader tv-depth` re-run against
both symbols. Every row came back identical to the anonymous measurements:

| Symbol | TF | Anonymous | Signed in | |
|---|---|---|---|---|
| QQQ | 5m | 5,304 | 5,304 | identical |
| QQQ | 15m | 5,240 | 5,240 | identical |
| QQQ | 60m | 6,500 | 6,500 | identical |
| NQ1! | 5m | 5,798 | 5,805 | identical (7 bars of elapsed time) |
| NQ1! | 15m | 5,413 | 5,415 | identical |
| NQ1! | 60m | 10,154 | 10,154 | identical |

In `tv-depth`'s own words: *a row that does not move is a limit an upgrade will
not lift.* So the entitlement hypothesis below was **wrong for this account** —
the caps are imposed by the chart feed on this access path, not withheld pending
a login. Whether a *paid* tier would lift them is still untested and should not
be assumed; do not buy a TradingView upgrade expecting more intraday depth
without measuring it first.

The same run surfaced the one genuinely deep series:

| QQQ | 1D | 6,925 bars | 1999-03-10 → 2026-09-18 | **27.5 years** |
|---|---|---|---|---|

## What the entitlement hypothesis got right and wrong

From the tunnel's own source (`evotrader/tvdata.py` on the `mcp` branch):

> One series request tops out a few thousand bars short of a deep intraday
> history; earlier bars come a page at a time. ... the ceiling is a time budget
> rather than a page count, **and an account that is entitled to the history is
> what decides how far it actually gets.**

The paging machinery exists — `request_more_data`, `MAX_PAGES = 2_000`,
`PAGE_SIZE = 20_000`, up to 10M bars. The wall hit above is therefore **an
entitlement wall, not a technical one**: the client asks for earlier pages and
the feed declines to serve them, because the session is anonymous
(`ANONYMOUS_TOKEN = "unauthorized_user_token"` is the fallback when no
credential is found).

Signing in is consequently the highest-leverage change available, and it costs a
login rather than a data purchase. On the machine running the tunnel:
`evotrader tv-login` stores the browser `sessionid` cookie, or set
`TRADINGVIEW_SESSION` / `TRADINGVIEW_SESSION_SIGN`, or `TRADINGVIEW_AUTH_TOKEN`
directly. How much further it reaches depends on the plan tier and is worth
re-measuring immediately after signing in — rerun the depth probes above and
compare.

## The four options, ranked

0. ~~Sign in to TradingView and re-measure.~~ **Done — it changed nothing.**
   Every row identical to anonymous. Keep the login (it costs nothing and the
   screener/quote endpoints may want it), but it is not the answer to depth.
1. **Start accumulating forward today.** The MCP server reads from a local store
   that `evotrader tv-fetch` fills. A scheduled weekly pull grows true
   continuous 5-minute history from now on — six months from now you have six
   real months, gap-free. Free, and worth starting whatever else is decided.
   *(Unverified from here: that the store persists and dedupes across fetches.
   Confirm on the machine running the tunnel before relying on it.)*
2. **Run the 3-year window at 60-minute.** Free, continuous, no gaps, full
   seasonal coverage. A different and slower question than the 5-minute one, but
   an honest one, and available right now.
3. **Stitch the quarterlies** as a regime robustness check, never as the primary
   backtest and never for seasonality.
4. **Buy the history.** Databento GLBX.MDP3 or equivalent — the only route to
   true continuous multi-year 5-minute data, and the only one that gets the full
   grid to 304/576.

These are not exclusive: 2 and 1 together cost nothing and answer most of the
question while the data for 4 accumulates or is purchased.

---

# Getting around the cap — brainstorm, with what was actually tested

*2026-09-22. Every "tested" line below is a measurement from this session, not
an assumption.*

## The cap's shape is the whole opportunity

Three properties, all measured: the wall is **per symbol**, **per timeframe**,
and **anchored to the end of the series**. Signing in did not move it; paying
did not move it; a different vendor's listing of the same underlying did not
move it (below). So it is not a quota to be bought through — it is a fixed
window, ~5,200 bars wide, hung off the last bar of whatever series you ask for.

That means two levers, and nothing else: **pick series whose last bar is in the
past** (expired contracts), and **pick a bar size where 5,200 bars covers the
stretch you need**. Combined, they are the way around.

## Route 1 — tested, works today: coarser bars × expired contracts

Each quarterly contract's window ends at *its* expiry. At 5-minute that window
is ~19 sessions, a third of a quarter. At 15-minute it is nearly the whole
quarter; at 30-minute it is more than the quarter:

| Contract | TF | Bars | Window | Notes |
|---|---|---|---|---|
| `NQH2026` | 15m | 5,090 | 2026-01-01 → 03-20 | full front-month quarter |
| `NQM2026` | 15m | 5,167 | 2026-03-31 → 06-18 | expiry pulled to Thu by Juneteenth |
| `NQU2026` | 15m | 5,274 | 2026-06-30 → 09-18 | full front-month quarter |
| `NQM2026` | **30m** | 5,223 | **2026-01-01 → 06-18** | its quarter *and* the one before |

| TF | Trading days per contract | Share of a 63-day quarter | Stitched gaps |
|---|---|---|---|
| 5m | 19 | 31% | ~2 months per quarter; Jan/Apr/Jul/Oct never covered |
| **15m** | **57** | **90%** | ~8 trading days after each roll |
| **30m** | 114 | 100% | none — windows overlap |

So **NQ futures at 15-minute can be rebuilt back to 2015 at ~90% coverage, and
at 30-minute with no gaps at all** — real futures, not an ETF proxy, with every
calendar month present. Against the 576-variation grid at the 400-trade floor,
a stitched 3-year 15-minute NQ series clears **304/576**, identical to what
true continuous data would clear.

The tool already exists on the `mcp` branch and takes a timeframe:

```bash
evotrader tv-archive --root NQ --timeframe 15 --since 2023 --pause 1
evotrader tv-archive --root NQ --timeframe 30 --since 2015 --pause 1
```

It back-adjusts the roll jumps by default and — this is the part that makes it
work here — measures each roll's basis on the contracts' *daily* overlap when
the intraday windows do not touch, so the seams are priced rather than guessed.
It reports `largest_gap_days` per run; check it. Two things to treat carefully:
a position should never be carried across a seam (the 8-day hole at 15m is
counted in bars by `max_hold_bars`, not in days), and an expiry that lands on a
holiday moves — `NQM2026` expired on a Thursday because of Juneteenth.

For the six-month window specifically: `NQH2026 + NQM2026 + NQU2026 + NQ1!` at
15-minute is January to today on actual NQ, with two ~8-day holes. Put beside
QQQ at 15-minute (9.7 months, continuous, RTH only) that is **two independent
instruments over the window that matters**, which is a robustness check nobody
has to pay for.

## Route 2 — tested, dead: another vendor's listing of the same thing

| Symbol | TF | Bars | Span |
|---|---|---|---|
| `NASDAQ:NDX` (the index) | 5m | 5,056 | 3.0 months |
| `OANDA:NAS100USD` (FX-broker CFD) | 5m | 5,818 | 1.0 month |
| `CFI:US100` (CFD) | 5m | 5,779 | 1.0 month |

Same window everywhere. The cap sits on the chart feed, not on any vendor's
data. Do not spend further effort here. (Supported bar sizes, for reference:
1, 3, 5, 15, 30, 45, 60, 120, 180, 240, 1D, 1W, 1M — no 10-minute.)

## Route 3 — untested, an engineering spike: replay-mode anchoring

The chart protocol has a *bar replay* mode that positions a chart at a past
instant; the feed then serves its ~5,200-bar window ending **there** instead of
now. If the server honours `replay_reset` to arbitrary timestamps for this
account, that is backward pagination by another name — every step back is a
fresh window on the *same* symbol, which would give continuous 5-minute NQ1!
history with no contract seams at all. Intraday replay is a paid-plan feature
on the web app, so entitlement may bind here where it did not bind above.
Half a day in `tvdata.py` to find out; the websocket client is already there.
Highest ceiling of anything on this page, and the least certain.

## Route 4 — external sources, ranked by friction

| Source | Cost | Instrument | Depth | Friction |
|---|---|---|---|---|
| **Databento** (GLBX.MDP3, `ohlcv-1m`) | free credit on signup; OHLCV is their cheapest schema | NQ futures, true continuous | years | API key — the original brief asked for this |
| **Alpaca** market data | free key | QQQ and every Nasdaq name | 5-minute back to ~2016 | endpoint reachable (401 without key) |
| **Polygon / Massive** free tier | free key, 5 calls/min | QQQ, equities | ~2 years intraday | endpoint reachable (401 without key) |
| **FirstRateData** | ~one-time, tens of dollars | NQ 1-minute, full history | 10+ years | download, one file |
| **Dukascopy** | free, keyless | USA100 index CFD, tick | back to ~2013 | reachable but returned `429` on a single request — throttled, needs pacing |
| **Interactive Brokers** TWS API | free with an account | NQ futures | years, paced | only if an account exists |

Databento is the one that matches the brief exactly; Alpaca is the one that
costs nothing and needs ten minutes.

## Route 5 — accumulate forward, starting today

`evotrader tv-fetch` deepens the local store on every run. A daily cron makes
5-minute NQ1! and QQQ continuous from now on, no gaps, no seams. It does
nothing for the past and everything for the future; there is no reason not to
start it regardless of which route above wins.

## Route 6 — the reframe

The stated priority is the last six months. That window is **already served**:
QQQ at 15-minute (9.7 months, continuous), NQ at 15-minute (stitched, two
small holes), QQQ at 5-minute for the most recent 3.2 months of it. Three years
of 5-minute was the original ask; six months weighted heavily is the stated
goal, and the second is achievable today while the first is not.

## Recommendation, in order

1. `tv-archive --root NQ --timeframe 15 --since 2023` — tonight, on the Mac.
   Real futures, three years, ~90% coverage, tool already written.
2. Start the `tv-fetch` cron the same evening.
3. Sign up for Alpaca (free) for a second continuous 5-minute equity feed.
4. If 5-minute *futures* history specifically proves necessary, Databento's
   free credit before anything paid.
5. The replay spike only if all of the above still leaves a gap that matters.

---

# First session breakdown on real NQ — 2026-09-22

The archive built on the Mac (`tv-archive --root NQ --timeframe 15 --since 2023`):
**83,960 bars, 18 contracts, 2022-12-01 → 2026-09-22, 925 of 994 weekday
sessions = 93% covered, largest hole 17 days, 17 rolls back-adjusted.** Better
than the 90% predicted; the 2023 contracts served ~7,000 bars each.

With the session features live, the same crude rule — lower-band poke and
reclaim, trend filter — run over the most recent 20,000 bars (Oct 2025 → Sep
2026, the window that contains the six months that matter), split by session:

| Session filter | Trades | Return | Profit factor | Win rate |
|---|---|---|---|---|
| A. 24h, no filter | 168 | −11.3% | 0.38 | 43% |
| F. Overnight only | 138 | −9.9% | 0.36 | 43% |
| B. RTH 09:30–16:00 | 46 | −1.2% | 0.72 | 48% |
| C. **First hour 09:30–10:30** | 22 | −0.2% | 0.97 | 50% |
| D. Second hour 10:30–11:30 | 13 | −0.3% | 0.67 | 46% |
| H. RTH, Tue–Thu | 25 | −0.6% | 0.77 | 52% |
| G. RTH + above session VWAP | 10 | −0.0% | 1.08 | 40% |
| E. Power hour 15:00–16:00 | 4 | +0.0% | 1.41 | 75% |

Buy-and-hold over the window: **+13.8%**.

What it says, and what it does not. **The rule's losses are an overnight
phenomenon**: 138 of its 168 trades and almost all of its drawdown come from
outside regular hours, at a profit factor of 0.36. Restricted to the opening
hour it is roughly flat. That is a genuine session finding — the first the
engine has been able to produce — and it is the shape the brief predicted:
the edge, if there is one, lives in a session, not around the clock.

It is **not** evidence of an edge anywhere. No bucket reaches even the
67-trade recent-window floor, let alone 400; the buckets that look best (E,
G) are the ones with four and ten trades. This is one crude rule with no
opening-range logic, no short side, long-only, on eleven months. It is the
pipeline proving it can answer the question, not the answer.

**Engine bug found in this run:** the report says `years: 3.02` for an
eleven-month window. `compute_metrics` derives years from *bar count* divided
by a fixed per-timeframe table that assumes regular-hours density; a 23-hour
futures session produces ~3.5x more bars per year, so `years` is overstated
3.5x and CAGR, Sharpe and turnover are deflated by the same factor. Total
return, profit factor, win rate, trade count and drawdown are unaffected. Fix:
derive years from the actual calendar span of the series.

**Per-call cap:** the MCP tools clamp `bars` to 20,000, so a single call sees
11 months of the 3.7-year archive. The full grid should be run locally from
the exported CSV rather than through 500 capped tool calls.
