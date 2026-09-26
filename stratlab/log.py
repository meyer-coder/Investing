"""The strategy log: every card is written down before it is tested.

research/lab/log.jsonl holds one record per card:

    id, batch, registered (UTC time), control (a random control?), engine
    (the engine version that produced the results), spec (the full card),
    results (per period, once tested), verdict, beats_controls

A card already in the log keeps its id; if its results came from an older
engine version they are cleared and it is tested again (not counted twice).

Because cards are logged before their results exist, the log is also the
count of everything ever tried, which is what "would pass by luck" is
measured against.  research/lab/leaderboard.md is rebuilt from it.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .data import ROOT
from .engine import VERSION
from .spec import card, key, normalize, short_filters

LAB = os.path.join(ROOT, "research", "lab")
LOG = os.path.join(LAB, "log.jsonl")
BOARD = os.path.join(LAB, "leaderboard.md")


def load(path: str = LOG) -> List[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def save(records: List[dict], path: str = LOG) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    os.replace(tmp, path)


def register(specs: List[dict], batch: str, control: bool = False, path: str = LOG) -> List[str]:
    """Log cards before testing them; a card already in the log keeps its id."""
    records = load(path)
    by_key = {r["key"]: r["id"] for r in records}
    ids = []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for spec in specs:
        k = key(spec)
        if k in by_key:
            rec = next(r for r in records if r["id"] == by_key[k])
            if rec.get("engine") != VERSION:              # tested by an older engine: test it again
                rec.update(engine=VERSION, results=None, verdict=None, beats_controls=None)
            ids.append(by_key[k])
            continue
        rid = f"L{len(records) + 1:04d}"
        records.append({"id": rid, "key": k, "batch": batch, "registered": now, "control": control,
                        "engine": VERSION,
                        "spec": normalize(spec), "results": None, "verdict": None, "beats_controls": None})
        by_key[k] = rid
        ids.append(rid)
    save(records, path)
    return ids


def update(rid: str, path: str = LOG, **fields) -> None:
    records = load(path)
    for r in records:
        if r["id"] == rid:
            r.update(fields)
    save(records, path)


def get(rid: str, path: str = LOG) -> Optional[dict]:
    return next((r for r in load(path) if r["id"] == rid), None)


def _row(i: int, r: dict) -> str:
    s, res = r["spec"], r["results"]
    a, c, f = res["search"], res["confirm"], res["final"]
    fam = "RANDOM control" if r["control"] else s["family"].replace("_", " ")
    beats = "-" if r["beats_controls"] is None else f"{r['beats_controls']['search']:.0f}%"
    return (f"| {i} | {r['id']} | {fam} | {s['market']} | {s['tf']}m | {s['session']} | {short_filters(s)} | "
            f"{a['n']} | {a['per_week']:.2f} | {a['win']:.0f}% | {a['avg_rr']:.2f} | {a['net_r']:+.3f}R | "
            f"{a['gross_r']:+.3f}R | {a['total_r']:+.0f} | ${a['usd']:,.0f} | {a['max_dd_r']:.0f} | "
            f"{a['cost_r']:.3f} | {a['t']:+.1f} | {beats} | {c['net_r']:+.3f}R ({c['n']}) | "
            f"{f['net_r']:+.3f}R ({f['n']}) | {r['verdict']} |")


def leaderboard(records: Optional[List[dict]] = None, top: Optional[int] = None, sort: str = "total_r") -> str:
    records = [r for r in (records if records is not None else load())
               if r["results"] and r.get("engine") == VERSION]
    real = [r for r in records if not r["control"]]
    ctrl = [r for r in records if r["control"]]
    records.sort(key=lambda r: r["results"]["search"][sort], reverse=True)
    passed = sum(r["verdict"] != "failed search" for r in real)
    conf = sum(r["verdict"] == "CONFIRMED" for r in real)
    ctrl_rank = [i + 1 for i, r in enumerate(records) if r["control"]]
    lines = [
        "# Strategy leaderboard",
        "",
        f"{len(real)} strategies tested, plus {len(ctrl)} random controls.  Sorted by total net R on the "
        "search years (2013-2019), as a dashboard would.",
        "",
        f"- {passed} passed the search; about {0.023 * len(real):.0f} would by luck alone.",
        f"- {conf} were confirmed on 2020-2022.",
        f"- The best random control ranks #{ctrl_rank[0]} of {len(records)}." if ctrl_rank else "",
        "",
        "Search-year columns first.  R is the first stop distance; $ is net R x $250.  'Beats random' is the "
        "share of the same batch's random controls (same market, candles, session and exits) with a lower "
        "net R a trade.",
        "",
        "| # | ID | Family | Market | TF | Session | Filters | Trades | Per week | Win % | Avg RR | Net R/trade | "
        "Gross R/trade | Total net R | $ at $250 risk | Max DD (R) | Cost in R | t | Beats random | "
        "Confirm net R/trade (n) | Final net R/trade (n) | Verdict |",
        "|" + "---|" * 22,
    ]
    for i, r in enumerate(records[:top] if top else records, 1):
        lines.append(_row(i, r))
    return "\n".join(lines) + "\n"


def write_board(path: str = BOARD) -> None:
    with open(path, "w") as f:
        f.write(leaderboard())


def show(rid: str) -> str:
    r = get(rid)
    if r is None:
        return f"{rid}: not in the log"
    lines = [f"{r['id']}  (batch {r['batch']}, logged {r['registered']})"]
    width = max(len(k) for k, _ in card(r["spec"]))
    lines += [f"  {k:<{width}}  {v}" for k, v in card(r["spec"])]
    if r["results"]:
        lines.append("")
        for p in ("search", "confirm", "final"):
            x = r["results"][p]
            lines.append(f"  {p:<8} {x['n']:>5} trades, {x['per_week']:.2f}/week, win {x['win']:.0f}%, "
                         f"net {x['net_r']:+.3f}R a trade (gross {x['gross_r']:+.3f}R, costs {x['cost_r']:.3f}R), "
                         f"t={x['t']:+.1f}, flips {x['flips']:.0f}%, total {x['total_r']:+.0f}R "
                         f"(${x['usd']:,.0f} at $250 risk), max DD {x['max_dd_r']:.0f}R")
        b = r["beats_controls"]
        lines.append(f"  verdict: {r['verdict']}" + (f"; beats {b['search']:.0f}% of its random controls on "
                                                     f"2013-2019 and {b['confirm']:.0f}% on 2020-2022"
                                                     if b is not None else ""))
    return "\n".join(lines)

