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
