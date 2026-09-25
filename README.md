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

## `harvest all` — pull everything

This is the point of the tool. Not "fetch me this symbol" — walk a whole
universe, take the deepest history the feed will serve for every symbol at
every timeframe, merge it into the store, and keep going when one fails.

```sh
harvest all                      # the built-in universe, full timeframe ladder
harvest all --top 500            # top 500 US stocks from the screener
harvest all --group futures,etfs # just those groups
harvest all --loop --every 6     # forever, a pass every 6 hours
```

Defaults: every group (88 symbols) across `1W,1D,240,60,30,15,5,1` — coarse
first, so an interrupted run still leaves every symbol with usable daily
history.

**It resumes.** Every pull is written to a ledger (`sweep.json` in the store)
the moment it finishes, so a run killed after four hours picks up where it
stopped rather than starting over. A series pulled within the last bar's worth
of time is skipped; `--redo` ignores the ledger, `--floor HOURS` changes the
threshold.

**It does not stop on failures.** A delisted ticker, a bad exchange prefix, a
dropped socket — each is recorded and the sweep moves on, with the failures
listed at the end. Failed series are retried on the next pass.

### Building the universe

| flag | what it pulls |
|---|---|
| `--group etfs,futures,fx,crypto,indices,megacaps,all` | the built-in lists |
| `--top 500` | top N US common stocks from TradingView's screener |
| `--sort-by volume` | rank the screener by volume instead of market cap |
| `--universe file.txt` | your own list, one symbol per line |
| `--symbols NASDAQ:AAPL,AMEX:SPY` | a few extra on top |
| `--list` | print the resolved universe and stop |
| `--save-universe u.txt` | write it to a file to edit and reuse |

Flags combine, and the result is de-duplicated.

### How deep it actually gets

One pull exhausts everything TradingView will serve **backwards** for a
series, and that limit is fixed — asking again immediately gets you nothing
more. Depth beyond it comes from calendar time: each pass merges in whatever
has happened since. A real pass:

```
  [   5/12] TVC:DJI       1D     32,630 bars 1896-05-26..2026-09-23  +32,630
  [   3/12] NASDAQ:NDX    1D     10,492 bars 1985-01-31..2026-09-23  +10,492
  [   2/12] SP:SPX        60      6,521 bars 2023-01-03..2026-09-24   +6,521
            NASDAQ:AAPL   5       5,226 bars 2026-06-22..2026-09-24   +5,226
```

Daily reaches back a century. 5-minute reaches back three months. That gap is
the whole reason for `--loop`: **the 1-minute store is built by sweeping on a
schedule for a year, not by one clever request.** Start it now and it is worth
something later.

### Run it on a schedule

macOS — save as `~/Library/LaunchAgents/com.harvest.sweep.plist`, then
`launchctl load ~/Library/LaunchAgents/com.harvest.sweep.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.harvest.sweep</string>
  <key>ProgramArguments</key>
  <array>
    <string>/PATH/TO/tunnel/.venv/bin/harvest</string>
    <string>all</string><string>--loop</string>
    <string>--every</string><string>6</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>HARVEST_CACHE</key><string>/PATH/TO/candles</string></dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/harvest.log</string>
  <key>StandardErrorPath</key><string>/tmp/harvest.log</string>
</dict></plist>
```

Linux — `crontab -e`:

```
0 */6 * * * cd /PATH/TO/tunnel && .venv/bin/harvest all >> /tmp/harvest.log 2>&1
```

### Futures archives in the same pass

```sh
harvest all --group futures --with-archives --archive-timeframes 1D,60
```

Also walks NQ, ES, RTY and YM back through their expired quarterly contracts
(see `harvest archive` below). Worth doing on daily and hourly; see the
coverage warning before trusting it at 5-minute.

## The rest of the commands

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
| sweep ledger | `sweep.json` inside the store — delete it to force a full re-pull |
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
  from sweeping repeatedly over time, not from one big pull. Running
  `harvest all --redo` twice in an afternoon gains you nothing.
- The archive's coverage number is the honest measure of what you got. A
  strategy evaluated on 34%-covered history has been evaluated on 34% of the
  history.
- Back-adjusted prices are not the prices anything traded at. They are for
  measuring returns across rolls, not for reading levels off.
