# Fixing the TradingView MCP tunnel

What can be changed, what it buys, and the ceiling that no amount of fixing
gets past. Measurements from this session; plan limits verified Sept 2026.

---

## Read this first: the ceiling

TradingView caps historical bars **per account plan**, and that cap sits above
whatever the tunnel does:

| Plan | Max bars | 5m NQ futures (276 bars/day) | 5m US equities (78 bars/day) |
|---|---|---|---|
| Basic (free) | 5,000 | ~18 trading days | ~64 trading days |
| Essential | 10,000 | ~36 days | ~4 months |
| Plus | 10,000 | ~36 days | ~4 months |
| Premium | 20,000 | ~72 days (~3.5 months) | **~1 year** |
| Expert | 25,000 | ~90 days | ~1.3 years |
| Ultimate | 40,000 | ~145 days (~7 months) | **~2 years** |

Ten years of 5-minute NQ is **~695,000 bars**. The best plan available serves
40,000 — **5.8%** of it.

**So: fixing the tunnel is worth 5x to 40x more data, and will never produce a
ten-year 5-minute study.** That ceiling belongs to TradingView, not to the
tunnel. Deep intraday history has to come from a file (see `data-sources.md`).

Note the equities column: on Premium or Ultimate, 5-minute *equity* data reaches
one to two years, because stocks produce a quarter as many bars per day. That is
genuinely usable, and it is the most under-appreciated line in this table.

---

## What is almost certainly underneath

The tunnel is not in this repository — checked every branch and the container's
config. It runs on your side.

Its behaviour matches the `tvdatafeed` library closely:

| Observed | Matches |
|---|---|
| Hard cap, CSV out, UTC timestamps | tvdatafeed's `get_hist()` |
| `NQ1!` continuous-contract symbols | tvdatafeed futures convention |
| **Equity data was regular-hours only** (13:30-19:55 UTC) | tvdatafeed's `extended_session` defaults to **False** |

That last row is the strongest signal. Treat the identification as a strong
inference, not a certainty — confirm against the actual source before editing.

---

## The fixes, by payoff per unit of effort

### 1. Check whether the server is logging in at all  *(highest value)*
`tvdatafeed` works anonymously — and anonymous means **Basic tier, 5,000 bars**,
no matter what you personally pay TradingView. If you hold Premium but the
server constructs `TvDatafeed()` with no credentials, you are getting free-tier
limits while paying for 20,000.

```python
tv = TvDatafeed(username="...", password="...")   # not TvDatafeed()
```

Check this before anything else. It may be the entire problem.

### 2. Raise the cap from 1,000 to 5,000  *(one number, 5x)*
The tunnel's own schema says `count: 1-1000`. tvdatafeed supports **5,000**. The
tunnel is discarding 5x its available capacity. Whoever wrote it likely chose
1,000 to keep tool responses small — a real concern, see #3.

### 3. Change how results are returned  *(do this WITH #2)*
A 1,000-bar response already exceeds the tool-output token limit and gets spilled
to a file. At 20,000 bars, returning raw CSV in the response body simply breaks.

The server should write to a file (Parquet or CSV) and return **a path plus a
summary** — row count, first and last timestamp, gaps detected. Raising the cap
without this just produces a different failure.

### 4. Set `extended_session=True`
Fixes the missing pre-market and after-hours on equities. Also makes the
gap-and-go brief (`prompt-library/07-smallcap-gap.md`) runnable, since it
selects candidates on pre-market volume.

### 5. Add a date-range / anchor parameter
The tunnel takes only `symbol`, `timeframe`, `count`, so every call returns the
most recent bars and history cannot be walked backwards. An anchor parameter
lets successive pulls be stitched — still bounded by the plan cap, but it makes
the data reproducible rather than always "whatever is newest."

### 6. Add `fut_contract`
Selects front vs back month on futures, which matters around quarterly rolls.

---

## Reference implementations

- `github.com/ranjan98/tradingview-mcp` — an existing TradingView MCP server
  (screener, technical ratings, OHLCV history), built on tvdatafeed
- `github.com/rongardF/tvdatafeed` — the maintained downloader fork
- `pypi.org/project/tvdatafeed-enhanced` — a fork advertising extra capability

---

## Recommendation

Do #1 and #2 — they are cheap and together may turn 1,000 bars into 20,000. Do
#3 at the same time or the win is unusable. Then stop.

Use the tunnel for what it is genuinely good at: live quotes, screening
thousands of symbols at once, recent intraday context, technical ratings, and
4 years of daily bars. Use a file source for deep intraday history. Trying to
force a ten-year 5-minute study through it is fighting a cap that cannot be won.

## Sources

- https://www.tradingview.com/support/solutions/43000480679-historical-intraday-data-bars-and-limits-explained/
- https://github.com/rongardF/tvdatafeed
- https://github.com/ranjan98/tradingview-mcp
