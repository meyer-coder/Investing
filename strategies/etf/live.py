"""Run the top strategies through the latest close: what each holds, what it
does at the next open, and which closes today would change that.

    python strategies/etf/live.py [--ranks 1,2,3] [--no-levels]

Each strategy runs on the real funds (MUU, TSMX, ...) from their launch, and as
a check on the rebuilt series it was bred on, with the engine used for every
backtest.  The engine decides on a close and fills at the next open, so the
run gets one placeholder bar after the last close: the orders it fills there
are the orders for the next open.  Yahoo's daily chart leaves a finished
session's close blank for a while; that close is taken from the quote
(see latest_bars).

Levels: the last session is followed by a hypothetical one in which a single
fund closes anywhere from -25% to +25% (the other funds unchanged, ordinary
volume, the day's range from the open to the close), and the orders each close
would bring at the following open are listed.

Writes profitable-strategies/leveraged-etfs/live/<date>.json and .md.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import date as Date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "etf"))
from gauntlet import ACCOUNT, REAL, SLIP, START                           # noqa: E402
from synth import SYNTH, synth                                             # noqa: E402
from evotrader.data import Bars, Universe, fetch_yahoo                     # noqa: E402
from evotrader.features import build_features                              # noqa: E402
from evotrader.genome import Genome, compile_genome                        # noqa: E402
from evotrader.runner import run_backtest                                  # noqa: E402

PUBLISHED = ROOT / "profitable-strategies" / "leveraged-etfs"
OUT = PUBLISHED / "live"
END_REASON = "end of backtest"


def _chart(symbol: str, query: str) -> dict:
    req = urllib.request.Request(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{query}",
                                 headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["chart"]["result"][0]


def _quote_sessions(symbol: str) -> Tuple[List[dict], dict]:
    """The last five daily rows, each scaled by Yahoo's dividend adjustment as
    the history is, and the quote: its session's date, price and the close of
    the session before."""
    res = _chart(symbol, "range=5d&interval=1d&events=div%2Csplit")
    q = res["indicators"]["quote"][0]
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose") or []
    rows = []
    for i, ts in enumerate(res.get("timestamp") or []):
        row = {k: q[k][i] for k in ("open", "high", "low", "close", "volume")}
        a = adj[i] if i < len(adj) else None
        row["ratio"] = a / row["close"] if a and row["close"] else 1.0
        rows.append({"date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"), **row})
    meta = _chart(symbol, "range=1d&interval=5m")["meta"]
    quote = {"date": datetime.fromtimestamp(meta["regularMarketTime"], tz=timezone.utc).strftime("%Y-%m-%d"),
             "price": float(meta["regularMarketPrice"]), "previous_close": meta.get("previousClose"),
             "adjusted_previous_close": meta.get("chartPreviousClose")}
    return rows, quote


def _intraday(symbol: str) -> Dict[str, List[float]]:
    """Daily open, high, low, last and volume from the last five days' 5-minute
    bars in regular hours, by New York date."""
    res = _chart(symbol, "range=5d&interval=5m")
    q = res["indicators"]["quote"][0]
    ny, out = ZoneInfo("America/New_York"), {}
    for i, ts in enumerate(res.get("timestamp") or []):
        t = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(ny)
        o, h, l, c, v = (q[k][i] for k in ("open", "high", "low", "close", "volume"))
        if (t.hour, t.minute) < (9, 30) or t.hour >= 16 or None in (o, h, l, c):
            continue
        d = t.strftime("%Y-%m-%d")
        if d not in out:
            out[d] = [o, h, l, c, v or 0.0]
        else:
            b = out[d]
            b[1], b[2], b[3], b[4] = max(b[1], h), min(b[2], l), c, b[4] + (v or 0.0)
    return out


def session_close(day: str) -> datetime:
    """4 pm New York on ``day``, in UTC."""
    ny = datetime.fromisoformat(day + "T16:00:00").replace(tzinfo=ZoneInfo("America/New_York"))
    return ny.astimezone(timezone.utc)


def latest_bars(symbol: str) -> Tuple[Bars, bool]:
    """Full daily history through the last session; True when that session is
    still trading, so its close is provisional.

    The history is Yahoo's, fetched fresh and not cached, up to the last five
    sessions, which are rebuilt: Yahoo shows a session still trading as if it
    were done, and leaves the last finished session's row blank for a day or
    so.  The quote's price is the close of its own session and its previous
    close the close of the session before; a blank row's open, high, low and
    volume come from that day's 5-minute bars.  A row nothing can fill ends
    the history there rather than leave a hole in it."""
    b = fetch_yahoo(symbol, "2005-01-01", "2100-01-01")
    rows, quote = _quote_sessions(symbol)
    keep = [i for i, d in enumerate(b.dates) if not rows or d < rows[0]["date"]]
    dates = [b.dates[i] for i in keep]
    cols = [list(np.asarray(x)[keep]) for x in (b.open, b.high, b.low, b.close, b.volume)]
    intraday: Optional[Dict[str, List[float]]] = None
    provisional = False
    for k, r in enumerate(rows):
        day = r["date"]
        o, h, l, c, v = (r[x] for x in ("open", "high", "low", "close", "volume"))
        ratio = r["ratio"]
        if day == quote["date"]:
            c, ratio = quote["price"], 1.0
        elif k + 1 < len(rows) and rows[k + 1]["date"] == quote["date"] and quote["previous_close"]:
            raw, adj = quote["previous_close"], quote["adjusted_previous_close"] or quote["previous_close"]
            c, ratio = raw, adj / raw
        if None in (o, h, l, v) or c is None:
            if intraday is None:
                intraday = _intraday(symbol)
            bar = intraday.get(day)
            if bar is None:
                if day == quote["date"] and datetime.now(timezone.utc) < session_close(day):
                    break                 # not open yet
                break
            o = bar[0] if o is None else o
            h = bar[1] if h is None else h
            l = bar[2] if l is None else l
            c = bar[3] if c is None else c
            v = bar[4] if v is None else v
        o, h, l, c = (float(x) * ratio for x in (o, h, l, c))
        provisional = datetime.now(timezone.utc) < session_close(day)
        for col, x in zip(cols, (o, max(h, o, c), min(l, o, c), c, float(v or 0.0))):
            col.append(x)
        dates.append(day)
    return Bars(symbol, dates, *[np.asarray(c, dtype=float) for c in cols]), provisional


def next_session(d: str) -> str:
    x = Date.fromisoformat(d) + timedelta(days=1)
    while x.weekday() >= 5:
        x += timedelta(days=1)
    return x.isoformat()


def align(bars: Dict[str, Bars]) -> Universe:
    common = sorted(set.intersection(*(set(b.dates) for b in bars.values())))
    out = {}
    for s, b in bars.items():
        idx = {d: i for i, d in enumerate(b.dates)}
        k = [idx[d] for d in common]
        out[s] = Bars(s, list(common), b.open[k], b.high[k], b.low[k], b.close[k], b.volume[k])
    return Universe(out, list(common))


def extend(u: Universe, day: str, closes: Optional[Dict[str, float]] = None) -> Universe:
    """One more session: each fund opens at the last close and closes at
    ``closes[fund]`` (default unchanged) on its 20-day average volume."""
    out = {}
    for s, b in u.bars.items():
        last = float(b.close[-1])
        c = (closes or {}).get(s, last)
        v = float(np.mean(b.volume[-20:]))
        out[s] = Bars(s, b.dates + [day], np.append(b.open, last), np.append(b.high, max(last, c)),
                      np.append(b.low, min(last, c)), np.append(b.close, c), np.append(b.volume, v))
    return Universe(out, u.calendar + [day])


def run(item: dict, u: Universe):
    return run_backtest(compile_genome(Genome.from_dict(item["genome"])), u, build_features(u),
                        starting_cash=ACCOUNT, commission_bps=0.0, slippage_bps=SLIP,
                        record_thoughts=False)


def orders(result, day: str) -> Tuple[List[dict], List[dict], List[dict]]:
    """(buys, sells, holds) at the open of ``day``, the placeholder session."""
    buys, sells, holds = [], [], []
    for t in result.journal.trades:
        if t.entry_date == day:
            buys.append({"fund": t.symbol, "why": t.entry_reason})
        elif t.exit_date == day and t.exit_reason != END_REASON:
            sells.append({"fund": t.symbol, "why": t.exit_reason, "entry_date": t.entry_date})
        elif t.exit_date == day:
            holds.append(t)
    return buys, sells, holds


def state(item: dict, u: Universe) -> dict:
    """Holdings after the last close and the orders for the next open."""
    last = u.calendar[-1]
    day = next_session(last)
    r = run(item, extend(u, day))
    buys, sells, holds = orders(r, day)
    risk = item["genome"].get("risk", {})
    held = []
    for t in holds:
        b = u.bars[t.symbol]
        i0 = b.dates.index(t.entry_date)
        closes = b.close[i0:]
        px = float(b.close[-1])
        peak = max(float(np.max(closes)), t.entry_price)
        h = {"fund": t.symbol, "since": t.entry_date, "entry": round(t.entry_price, 2),
             "last_close": round(px, 2), "gain": round(px / t.entry_price - 1.0, 4),
             "sessions": len(closes), "why": t.entry_reason}
        if risk.get("stop_loss_pct"):
            h["stop_close"] = round(t.entry_price * (1 - risk["stop_loss_pct"]), 2)
        if risk.get("take_profit_pct"):
            h["target_close"] = round(t.entry_price * (1 + risk["take_profit_pct"]), 2)
        if risk.get("trailing_stop_pct"):
            h["trail_close"] = round(peak * (1 - risk["trailing_stop_pct"]), 2)
        held.append(h)
    recent = [{"fund": t.symbol, "in": t.entry_date, "out": t.exit_date, "ret": round(t.ret, 4),
               "exit": t.exit_reason} for t in r.journal.trades if t.exit_date < day][-5:]
    return {"last_close_date": last, "next_open": day, "buys": buys, "sells": sells,
            "holding": held, "recent_trades": recent}


def _label(buys, sells, holds) -> str:
    parts = [f"sell {s['fund']}" for s in sells] + [f"buy {b['fund']}" for b in buys]
    if not parts:
        return "hold " + ", ".join(t.symbol for t in holds) if holds else "stay in cash"
    return " + ".join(parts)


def levels(item: dict, u: Universe, step: float = 0.005, span: float = 0.25) -> Dict[str, List[dict]]:
    """For each fund, the ranges of today's close (as a change from the last
    close, the other funds unchanged) and what each brings at the next open."""
    today = next_session(u.calendar[-1])
    after = next_session(today)
    grid = np.round(np.arange(-span, span + 1e-9, step), 4)
    out: Dict[str, List[dict]] = {}
    for s in u.symbols:
        last = float(u.bars[s].close[-1])

        def act(g: float) -> str:
            hyp = extend(extend(u, today, {s: last * (1 + g)}), after)
            return _label(*orders(run(item, hyp), after))

        acts = [act(g) for g in grid]
        ranges: List[dict] = []
        for k, (g, a) in enumerate(zip(grid, acts)):
            if ranges and ranges[-1]["action"] == a:
                ranges[-1]["to"] = float(g)
                continue
            if ranges:
                # the change lies between the last two grid closes: narrow it to a cent
                lo, hi = float(grid[k - 1]), float(g)
                while (hi - lo) * last > 0.005:
                    mid = (lo + hi) / 2
                    if act(mid) == ranges[-1]["action"]:
                        lo = mid
                    else:
                        hi = mid
                ranges[-1]["to"] = lo
                g = hi
            ranges.append({"action": a, "from": float(g), "to": float(g)})
        for rg in ranges:
            rg["price_from"] = round(last * (1 + rg["from"]), 2)
            rg["price_to"] = round(last * (1 + rg["to"]), 2)
        out[s] = ranges
    return out


def load_items(ranks: Sequence[int]) -> List[dict]:
    items = {}
    for f in PUBLISHED.glob("[0-9][0-9]_*.json"):
        v = json.loads(f.read_text())
        items[v["rank"]] = v
    return [items[r] for r in ranks]


def pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def report(rows: List[dict], provisional: bool) -> str:
    first = rows[0]["real"]
    lines = [f"# Live: orders for the {first['next_open']} open",
             "", f"From the {first['last_close_date']} close"
             + (" (provisional: the session was still trading)" if provisional else "")
             + f", generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC. Paper signals, not orders placed.",
             ""]
    for row in rows:
        st, chk = row["real"], row["rebuilt"]
        lines += [f"## {row['rank']}. {row['name']}", ""]
        if st["sells"] or st["buys"]:
            for s in st["sells"]:
                lines.append(f"- **Sell {s['fund']} at the open** ({s['why']}).")
            for b in st["buys"]:
                lines.append(f"- **Buy {b['fund']} at the open** with the whole slot ({b['why']}).")
        for h in st["holding"]:
            if any(s["fund"] == h["fund"] for s in st["sells"]):
                continue
            extra = ", ".join(x for x in (
                f"stop on a close at or under ${h['stop_close']}" if "stop_close" in h else "",
                f"target on a close at or over ${h['target_close']}" if "target_close" in h else "",
                f"trailing stop on a close at or under ${h['trail_close']}" if "trail_close" in h else "") if x)
            lines.append(f"- **Hold {h['fund']}**, bought {h['since']} at ${h['entry']:.2f}: "
                         f"{pct(h['gain'])} at the ${h['last_close']:.2f} close after {h['sessions']} sessions"
                         + (f"; {extra}" if extra else "") + ".")
        if not (st["sells"] or st["buys"] or st["holding"]):
            lines.append("- **Nothing to do**: in cash, no entry fired on the last close.")
        same = (sorted(x["fund"] for x in st["buys"]) == sorted(REAL.get(x["fund"], x["fund"]) for x in chk["buys"])
                and sorted(x["fund"] for x in st["sells"]) == sorted(REAL.get(x["fund"], x["fund"]) for x in chk["sells"]))
        lines.append(f"- On the rebuilt series it was bred on: "
                     f"{'the same orders' if same else 'different orders: ' + json.dumps({k: chk[k] for k in ('buys', 'sells')})}.")
        if row.get("levels"):
            lines += ["", "What today's close would bring at the next open (the other funds unchanged):", ""]
            for fund, ranges in row["levels"].items():
                parts = []
                for k, r in enumerate(ranges):
                    if len(ranges) == 1:
                        where = "anywhere within 25%"
                    elif k == 0:
                        where = f"${r['price_to']:,.2f} or lower ({pct(r['to'])})"
                    elif k == len(ranges) - 1:
                        where = f"${r['price_from']:,.2f} or higher ({pct(r['from'])})"
                    else:
                        where = f"${r['price_from']:,.2f} to ${r['price_to']:,.2f} ({pct(r['from'])} to {pct(r['to'])})"
                    parts.append(f"{where}: {r['action']}")
                lines.append(f"- {fund} closes " + "; ".join(parts))
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ranks", default="1,2,3")
    ap.add_argument("--no-levels", action="store_true")
    args = ap.parse_args(argv)
    items = load_items([int(x) for x in args.ranks.split(",")])
    cache: Dict[str, Tuple[Bars, bool]] = {}

    def bars(sym: str) -> Tuple[Bars, bool]:
        if sym not in cache:
            if sym in SYNTH:
                under, k, _ = SYNTH[sym]
                ub, prov = bars(under)
                cache[sym] = (synth(ub, k, sym).slice(START, None), prov)
            else:
                cache[sym] = latest_bars(sym)
        return cache[sym]

    rows, provisional = [], False
    for item in items:
        syn = item["symbols"]
        real = [REAL.get(s, s) for s in syn]
        ur = align({s: bars(s)[0] for s in real})
        us = align({s: bars(s)[0] for s in syn})
        provisional |= any(bars(s)[1] for s in real)
        row = {"rank": item["rank"], "name": item["name"], "funds": real,
               "real": state(item, ur), "rebuilt": state(item, us)}
        if not args.no_levels:
            row["levels"] = levels(item, ur)
        rows.append(row)
        print(f"{item['rank']}. {item['name']}: {row['real']['buys']} {row['real']['sells']} "
              f"{[h['fund'] for h in row['real']['holding']]}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    day = rows[0]["real"]["last_close_date"]
    (OUT / f"{day}.json").write_text(json.dumps({"provisional": provisional, "strategies": rows}, indent=1))
    md = report(rows, provisional)
    (OUT / f"{day}.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
