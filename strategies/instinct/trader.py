"""A paper trader that reads MNQ's candles as they finish and trades on judgment, not a fixed rule.

    python strategies/instinct/trader.py watch       # through the session: a line per finished 5-minute candle
    python strategies/instinct/trader.py view        # the chart as the trader sees it at the last finished candle
    python strategies/instinct/trader.py decide long --stop 25 --target 50 --why "..."
    python strategies/instinct/trader.py decide short --stop 25 --why "..."     # no target: exit by hand or stop
    python strategies/instinct/trader.py decide exit --why "..."
    python strategies/instinct/trader.py report

The owner asked for a reactive trader: watch the chart, read the wicks and
candles, and buy on instinct.  Candle rules (pin bars, engulfing, dojis) lost
money in every test here and in the 10,000-strategy study on the
video-breakdowns branch, so the only fair test of judgment is forward, on
paper, scored against random entries once there are enough trades.

How a trade is booked:

* the data is Yahoo's MNQ=F one-minute bars (CME micro Nasdaq futures, about
  ten minutes late); 5-minute candles are built from them for 09:30-16:00
  New York;
* a decision is stamped with the close of the last finished 5-minute candle
  the trader saw (`view`), and fills at the open of the next one-minute bar,
  one tick against it;
* stops rest in the market and fill at the stop (or the open, if the bar
  gaps through it) plus a tick; targets fill at the target; when a bar
  reaches both, the stop is taken;
* $0.75 a contract a side in commission;
* the account is a Topstep 100K: at most 2 MNQ, at most $250 at risk a trade,
  the day ends at -$600 (open trades included), at most six trades a day, no
  new trade after 15:30 and flat at 15:55.

Every decision and trade, with the reason given, goes to
profitable-strategies/instinct/paper.json; the working files are in
data/cache/instinct/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "profitable-strategies" / "instinct"
LEDGER = OUT / "paper.json"
WORK = ROOT / "data" / "cache" / "instinct"
STATE = WORK / "state.json"
VIEW = WORK / "view.md"
NY = ZoneInfo("America/New_York")
SYMBOL = "MNQ=F"
POINT, TICK, COMM = 2.0, 0.25, 0.75          # $ a point per MNQ, the tick, commission a contract a side
SIZE, MAX_RISK, DAY_STOP, MAX_TRADES = 2, 250.0, 600.0, 6
OPEN, LAST_ENTRY, FLAT, CLOSE = (9, 30), (15, 30), (15, 55), (16, 0)
Bar = Tuple[int, float, float, float, float, float]                     # epoch minute, open, high, low, close, volume


# ------------------------------------------------------------------ data

def fetch(days: str = "5d") -> List[Bar]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{SYMBOL}?interval=1m&range={days}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=20))["chart"]["result"][0]
    q = d["indicators"]["quote"][0]
    by: Dict[int, Bar] = {}
    for i, t in enumerate(d["timestamp"]):
        o, h, lo, c, v = (q[k][i] for k in ("open", "high", "low", "close", "volume"))
        if None in (o, h, lo, c):
            continue
        m = int(t) - int(t) % 60
        by[m] = (m, float(o), float(h), float(lo), float(c), float(v or 0))
    out = [by[k] for k in sorted(by)]
    return out[:-1]                                                            # the newest minute is still forming


def et(t: int) -> dt.datetime:
    return dt.datetime.fromtimestamp(t, NY)


def hm(t: int) -> Tuple[int, int]:
    x = et(t)
    return x.hour, x.minute


def rth(bars: List[Bar], day: dt.date) -> List[Bar]:
    return [b for b in bars if et(b[0]).date() == day and OPEN <= hm(b[0]) < CLOSE]


def candles(day_bars: List[Bar], last_minute: int) -> List[dict]:
    """5-minute candles of the day, finished ones only (a later minute exists past each one's end)."""
    groups: Dict[int, List[Bar]] = {}
    for b in day_bars:
        groups.setdefault(b[0] - b[0] % 300, []).append(b)
    out = []
    for start in sorted(groups):
        g = groups[start]
        if start + 300 > last_minute + 60:                                     # not finished yet
            continue
        o, c = g[0][1], g[-1][4]
        h, lo = max(b[2] for b in g), min(b[3] for b in g)
        out.append({"start": start, "end": start + 300, "o": o, "h": h, "l": lo, "c": c, "v": sum(b[5] for b in g)})
    return out


def context(bars: List[Bar], day: dt.date) -> dict:
    """Yesterday's regular session, the overnight session and today's so far."""
    days = sorted({et(b[0]).date() for b in bars if OPEN <= hm(b[0]) < CLOSE and et(b[0]).date() < day})
    ctx: dict = {}
    if days:
        y = rth(bars, days[-1])
        ctx["prior"] = {"day": str(days[-1]), "high": max(b[2] for b in y), "low": min(b[3] for b in y), "close": y[-1][4]}
        start = dt.datetime.combine(days[-1], dt.time(18, 0), NY).timestamp()
        end = dt.datetime.combine(day, dt.time(9, 30), NY).timestamp()
        on = [b for b in bars if start <= b[0] < end]
        if on:
            ctx["overnight"] = {"high": max(b[2] for b in on), "low": min(b[3] for b in on)}
    t = rth(bars, day)
    if t:
        pv = sum((b[2] + b[3] + b[4]) / 3 * max(b[5], 1) for b in t)
        vol = sum(max(b[5], 1) for b in t)
        ctx["today"] = {"open": t[0][1], "high": max(b[2] for b in t), "low": min(b[3] for b in t), "vwap": pv / vol}
    lv = ROOT / "data" / "levels" / f"{day}.json"
    if lv.exists():
        ctx["levels"] = json.loads(lv.read_text()).get("nq", {})
    return ctx


# ------------------------------------------------------------------ the ledger

def load() -> dict:
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else {"account": "Topstep 100K, paper", "days": {}}


def save(led: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(led, indent=1))


def today(led: dict, day: dt.date) -> dict:
    return led["days"].setdefault(str(day), {"decisions": [], "trades": [], "position": None, "pending": None,
                                             "realized": 0.0, "done": None, "processed": 0})


def close_trade(d: dict, t: int, px: float, why: str) -> None:
    p = d["position"]
    usd = p["side"] * (px - p["entry"]) * POINT * p["size"] - 2 * COMM * p["size"]
    d["trades"].append({"side": "long" if p["side"] > 0 else "short", "size": p["size"], "entry_time": p["entry_time"],
                        "entry": p["entry"], "stop": p["stop"], "target": p["target"], "exit_time": et(t).strftime("%H:%M"),
                        "exit": round(px, 2), "exit_reason": why, "usd": round(usd, 2), "why": p["why"]})
    d["realized"] = round(d["realized"] + usd, 2)
    d["position"] = None


def process(d: dict, day_bars: List[Bar]) -> None:
    """Walk the one-minute bars not yet seen: fill what is pending, then stops, targets, the day stop, the close."""
    for b in day_bars:
        t, o, h, lo, c, _ = b
        if t < d["processed"]:
            continue
        pend = d["pending"]
        if pend and t >= pend["after"]:
            d["pending"] = None
            if pend["action"] == "exit" and d["position"]:
                close_trade(d, t, o - d["position"]["side"] * TICK, "by hand: " + pend["why"])
            elif pend["action"] in ("long", "short") and not d["position"] and not d["done"]:
                side = 1 if pend["action"] == "long" else -1
                entry = o + side * TICK
                d["position"] = {"side": side, "size": pend["size"], "entry": round(entry, 2),
                                 "entry_time": et(t).strftime("%H:%M"), "stop": round(entry - side * pend["stop"], 2),
                                 "target": round(entry + side * pend["target"], 2) if pend["target"] else None,
                                 "why": pend["why"]}
        p = d["position"]
        if p:
            s = p["side"]
            if (s > 0 and lo <= p["stop"]) or (s < 0 and h >= p["stop"]):
                px = min(o, p["stop"]) if s > 0 else max(o, p["stop"])
                close_trade(d, t, px - s * TICK, "stop")
            elif p["target"] and ((s > 0 and h >= p["target"]) or (s < 0 and lo <= p["target"])):
                close_trade(d, t, p["target"], "target")
            elif hm(t) >= FLAT:
                close_trade(d, t, o - s * TICK, "flat for the close")
        p = d["position"]
        open_usd = p["side"] * (c - p["entry"]) * POINT * p["size"] if p else 0.0
        if not d["done"] and d["realized"] + open_usd <= -DAY_STOP:
            if p:
                close_trade(d, t, c - p["side"] * TICK, "day stop")
            d["done"], d["pending"] = "day stop at -$600", None
        if not d["done"] and len(d["trades"]) >= MAX_TRADES and not d["position"]:
            d["done"] = "six trades"
        d["processed"] = t + 60


# ------------------------------------------------------------------ commands

def refresh() -> Tuple[dict, dict, List[dict], dict, dt.date]:
    bars = fetch()
    day = et(bars[-1][0]).date()
    led = load()
    d = today(led, day)
    tb = rth(bars, day)
    process(d, tb)
    save(led)
    cs = candles(tb, bars[-1][0])
    return led, d, cs, context(bars, day), day


def render(d: dict, cs: List[dict], ctx: dict, day: dt.date, n: int = 30) -> str:
    lines = [f"# MNQ, {day}, 5-minute candles to {et(cs[-1]['end']).strftime('%H:%M') if cs else 'the open'} New York", ""]
    if "prior" in ctx:
        p = ctx["prior"]
        lines.append(f"Yesterday ({p['day']}): high {p['high']:.2f}, low {p['low']:.2f}, close {p['close']:.2f}")
    if "overnight" in ctx:
        lines.append(f"Overnight: high {ctx['overnight']['high']:.2f}, low {ctx['overnight']['low']:.2f}")
    if "today" in ctx:
        t = ctx["today"]
        lines.append(f"Today: open {t['open']:.2f}, high {t['high']:.2f}, low {t['low']:.2f}, VWAP {t['vwap']:.2f}")
    if ctx.get("levels"):
        lv = ctx["levels"]
        lines.append("Options levels (NQ points): " + ", ".join(f"{k.replace('_', ' ')} {v:,.0f}" for k, v in lv.items()))
    pos = d["position"]
    lines.append(f"Position: {('long' if pos['side'] > 0 else 'short') + ' ' + str(pos['size']) + ' at ' + str(pos['entry']) + ', stop ' + str(pos['stop']) + ', target ' + str(pos['target']) if pos else 'flat'}"
                 f"; pending: {d['pending']['action'] if d['pending'] else 'none'}; realized ${d['realized']:+.2f}, "
                 f"{len(d['trades'])} trades{'; DONE: ' + d['done'] if d['done'] else ''}")
    lines += ["", "| time | open | high | low | close | body | upper wick | lower wick | range | volume |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for x in cs[-n:]:
        body = x["c"] - x["o"]
        up, dn = x["h"] - max(x["o"], x["c"]), min(x["o"], x["c"]) - x["l"]
        lines.append(f"| {et(x['start']).strftime('%H:%M')} | {x['o']:.2f} | {x['h']:.2f} | {x['l']:.2f} | {x['c']:.2f} | "
                     f"{body:+.2f} | {up:.2f} | {dn:.2f} | {x['h'] - x['l']:.2f} | {x['v']:,.0f} |")
    return "\n".join(lines) + "\n"


def cmd_view(_args) -> int:
    led, d, cs, ctx, day = refresh()
    WORK.mkdir(parents=True, exist_ok=True)
    text = render(d, cs, ctx, day)
    VIEW.write_text(text)
    STATE.write_text(json.dumps({"day": str(day), "seen_to": cs[-1]["end"] if cs else 0}))
    print(text)
    return 0


def cmd_decide(args) -> int:
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    if not st.get("seen_to"):
        print("look at the chart first: trader.py view")
        return 1
    led = load()
    d = today(led, dt.date.fromisoformat(st["day"]))
    after = st["seen_to"]
    rec = {"at": et(after).strftime("%H:%M"), "action": args.action, "why": args.why}
    if args.action in ("long", "short"):
        if d["done"] or d["position"] or d["pending"]:
            print(f"no new trade: {d['done'] or 'already in a trade or one is pending'}")
            return 1
        if et(after).time() >= dt.time(*LAST_ENTRY):
            print("no new trade after 15:30")
            return 1
        if args.stop <= 0:
            print("every trade needs a stop: --stop in points")
            return 1
        size = min(args.size, SIZE)
        while size > 0 and args.stop * POINT * size + 2 * COMM * size > MAX_RISK:
            size -= 1
        if size == 0:
            print(f"a {args.stop}-point stop risks more than ${MAX_RISK:.0f} even on 1 MNQ")
            return 1
        d["pending"] = {"action": args.action, "after": after, "stop": args.stop, "target": args.target, "size": size,
                        "why": args.why}
        rec.update(stop=args.stop, target=args.target, size=size)
    elif args.action == "exit":
        if not d["position"]:
            print("flat already")
            return 1
        d["pending"] = {"action": "exit", "after": after, "why": args.why}
    d["decisions"].append(rec)
    save(led)
    print(f"booked: {rec}")
    return 0


def cmd_watch(_args) -> int:
    """Refresh every 30 seconds; print a line each time a 5-minute candle finishes, until 16:05."""
    last_end, last_err = 0, 0.0
    while True:
        now = dt.datetime.now(NY)
        if now.time() >= dt.time(16, 5):
            print("SESSION OVER", flush=True)
            return 0
        try:
            led, d, cs, ctx, day = refresh()
            if cs and cs[-1]["end"] != last_end:
                last_end = cs[-1]["end"]
                x = cs[-1]
                pos = d["position"]
                print(f"CANDLE {et(x['start']).strftime('%H:%M')} o {x['o']:.2f} h {x['h']:.2f} l {x['l']:.2f} c {x['c']:.2f} "
                      f"| {('long' if pos['side'] > 0 else 'short') + ' ' + str(pos['size']) + ' from ' + str(pos['entry']) if pos else 'flat'}"
                      f" | day ${d['realized']:+.2f}, {len(d['trades'])} trades{' | DONE' if d['done'] else ''}", flush=True)
        except Exception as e:                                               # a bad fetch: say so, keep going
            if time.time() - last_err > 300:
                print(f"FEED ERROR {str(e)[:120]}", flush=True)
                last_err = time.time()
        time.sleep(30)


def cmd_report(_args) -> int:
    led = load()
    allt = []
    for day, d in sorted(led["days"].items()):
        print(f"{day}: {len(d['trades'])} trades, ${d['realized']:+.2f}{' (' + d['done'] + ')' if d['done'] else ''}")
        for t in d["trades"]:
            print(f"  {t['entry_time']}-{t['exit_time']} {t['side']} {t['size']} {t['entry']} -> {t['exit']} "
                  f"({t['exit_reason']}) ${t['usd']:+.2f}: {t['why']}")
        allt += d["trades"]
    if allt:
        wins = sum(t["usd"] > 0 for t in allt)
        print(f"all: {len(allt)} trades, {wins} winners, ${sum(t['usd'] for t in allt):+.2f}, "
              f"${sum(t['usd'] for t in allt) / len(allt):+.2f} a trade")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("watch").set_defaults(fn=cmd_watch)
    sub.add_parser("view").set_defaults(fn=cmd_view)
    sub.add_parser("report").set_defaults(fn=cmd_report)
    dp = sub.add_parser("decide")
    dp.add_argument("action", choices=["long", "short", "exit"])
    dp.add_argument("--stop", type=float, default=0.0, help="points from the fill")
    dp.add_argument("--target", type=float, default=0.0, help="points from the fill; 0 = none")
    dp.add_argument("--size", type=int, default=SIZE)
    dp.add_argument("--why", required=True)
    dp.set_defaults(fn=cmd_decide)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
