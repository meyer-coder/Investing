# harvest

Pulls candles from TradingView and keeps them on disk, so a machine can build
up years of intraday history once and then read it back instantly.

It is a standalone copy of the data layer from the trading-bot repo — no MCP
server, no tunnel, no backtester. Just the harvesting.

## Install

```sh
git clone <this repo> tunnel
cd tunnel
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Then either `pip install -e .` (gives you a `harvest` command) or run it as
`python -m harvester` everywhere below.

Python 3.9 or newer. numpy is the only dependency.

## Sign in first

An anonymous session gets shallower history than a logged-in one, so do this
before anything else:

```sh
harvest login
```

It asks for two cookies from a browser already logged in to TradingView:
DevTools → Application → Cookies → `https://www.tradingview.com` → copy
`sessionid` and `sessionid_sign`. Input is hidden and the values are written
to `~/.config/harvest/tradingview.json` with mode 0600, nowhere else.
`harvest login --forget` deletes it.

If `~/.config/evotrader/tradingview.json` already exists, that login is used
and you can skip this step.

## What it does

### `harvest depth` — how far back one request reaches

```sh
harvest depth --symbol NASDAQ:AAPL
```

Prints, per timeframe, how many bars and how many years come back from a
single pull. Run this first on any new symbol: the answer is a **bar count**
cap, not a date cap, so a 1-minute series reaches back weeks where a daily
series reaches back decades.

### `harvest fetch` — fill the store

```sh
harvest fetch --symbols NASDAQ:AAPL,AMEX:SPY --timeframes 5,60,1D
```

Each pull is merged with whatever is already stored for that symbol and
timeframe, so running it again next week extends the series rather than
replacing it. **That is how the store gets deeper than any single request:**
run it on a schedule and the history accumulates past the per-request cap.

Series are held as numpy `.npz`, which reads about 25× faster than CSV at
half a million bars.

### `harvest archive` — deep futures history

```sh
harvest archive --root NQ --timeframe 5 --since 2015
```

A single continuous futures symbol (`CME_MINI:NQ1!`) only reaches back as far
as the bar cap allows. But every **expired quarterly contract** — NQH2023,
NQM2023, NQU2023, NQZ2023, … — is still on the feed with its own full
history. This walks the contract chain back to `--since`, pulls each one, and
stitches them into one series at `CME_MINI:NQ#ARCHIVE`.

Rolls are back-adjusted by default (the panama method): at each roll the older
contract is shifted by the median close difference over the days the two
contracts overlap, so the seam does not show up as a tradeable gap. Pass
`--raw-prices` to leave the jumps in.

**Read the coverage line before you trust the output.** A real run:

```
CME_MINI:NQ#ARCHIVE 5: 81,136 bars from 18 contracts, 2023-02-20..2026-09-18,
320 sessions of 935 weekdays, 34% covered, largest hole 73 days,
back-adjusted across 17 rolls (14 measured on daily overlap)
```

Each contract's 5-minute history is itself bar-capped, so you get the last
few months of each contract's life, not all of it — 34% of sessions, with
holes up to 73 days. It is real data with real gaps, not a continuous series.
Daily and hourly archives cover far better than 5-minute ones. The three
rolls that could not be measured had no overlapping daily bars; those seams
are joined without a shift.

### `harvest status` — what you have

```sh
harvest status
```

Every stored series with its bar count and date range, and the totals.

### `harvest export` / `harvest import` — CSV in and out

```sh
harvest export --symbol CME_MINI:NQ#ARCHIVE --timeframe 5 --file nq.csv
harvest import --file nq.csv --symbol CME_MINI:NQ --timeframe 5
```

Import merges by default; `--replace` overwrites. Use import to fold in data
from a broker or a paid vendor alongside what TradingView gives you.

## Where things live

| | |
|---|---|
| candle store | `data/cache/tv/` — override with `HARVEST_CACHE` |
| login | `~/.config/harvest/tradingview.json` — override with `TRADINGVIEW_CREDENTIALS` |

Point `HARVEST_CACHE` at an external drive if you are building up years of
1-minute data; it grows to gigabytes.

## Using it from Python

```python
from harvester import cached_bars, build_archive, fetch_bars

bars = cached_bars("NASDAQ:AAPL", "1D", 5000)   # store first, network if needed
print(len(bars), bars.dates[0], bars.dates[-1])
print(bars.close[-5:])                          # numpy arrays
```

`Bars` holds `dates` plus `open/high/low/close/volume` as numpy arrays, so it
drops straight into pandas or any backtester.

## Fair warnings

- Bar caps are per request and per timeframe. Depth on 1-minute data comes
  from fetching repeatedly over time, not from one big pull.
- The archive's coverage number is the honest measure of what you got. A
  strategy evaluated on 34%-covered history has been evaluated on 34% of the
  history.
- Back-adjusted prices are not the prices anything traded at. They are for
  measuring returns across rolls, not for reading levels off.
