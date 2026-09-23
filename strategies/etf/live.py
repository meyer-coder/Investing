"""Run the top strategies through the latest close: what each holds, what it
does at the next open, and which closes today would change that.

    python strategies/etf/live.py [--ranks 1,2,3] [--no-levels]

Each strategy runs on the real funds (MUU, TSMX, ...) from their launch, and as
a check on the rebuilt series it was bred on, with the engine used for every
backtest.  The engine decides on a close and fills at the next open, so the
run gets one placeholder bar after the last close: the orders it fills there
are the orders for the next open.  Yahoo's daily chart leaves a finished
session's close blank for a while; that close is taken from the quote.

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
from evotrader.data import Bars, Universe, load_symbol                     # noqa: E402
from evotrader.features import build_features                              # noqa: E402
from evotrader.genome import Genome, compile_genome                        # noqa: E402
from evotrader.runner import run_backtest                                  # noqa: E402

PUBLISHED = ROOT / "profitable-strategies" / "leveraged-etfs"
OUT = PUBLISHED / "live"
END_REASON = "end of backtest"
_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{}?range=5d&interval=1d"


def _quote_sessions(symbol: str) -> Tuple[List[dict], dict]:
    req = urllib.request.Request(_CHART.format(symbol), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read())["chart"]["result"][0]
    q, meta = res["indicators"]["quote"][0], res["meta"]
    rows = []
    for i, ts in enumerate(res.get("timestamp") or []):
        rows.append({"date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                     **{k: q[k][i] for k in ("open", "high", "low", "close", "volume")}})
    return rows, meta


def session_close(day: str) -> datetime:
    """4 pm New York on ``day``, in UTC."""
    ny = datetime.fromisoformat(day + "T16:00:00").replace(tzinfo=ZoneInfo("America/New_York"))
    return ny.astimezone(timezone.utc)


def latest_bars(symbol: str) -> Tuple[Bars, bool]:
    """Full daily history through the last session; True when that session is
    still trading, so its close is provisional."""
    b = load_symbol(symbol, "2005-01-01", "2100-01-01", refresh=True)
    rows, meta = _quote_sessions(symbol)
    dates, cols = list(b.dates), [list(x) for x in (b.open, b.high, b.low, b.close, b.volume)]
    provisional = False
    for r in rows:
        if r["date"] <= dates[-1] or r["open"] is None:
            continue
        close = r["close"]
        stamp = datetime.fromtimestamp(meta.get("regularMarketTime", 0), tz=timezone.utc)
        if close is None and stamp.strftime("%Y-%m-%d") == r["date"]:
            close = float(meta["regularMarketPrice"])
            provisional = stamp < session_close(r["date"])
        if close is None:
            continue
        hi = max(float(r["high"] or close), close)
        lo = min(float(r["low"] or close), close)
        for col, x in zip(cols, (float(r["open"]), hi, lo, close, float(r["volume"] or 0.0))):
            col.append(x)
        dates.append(r["date"])
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
