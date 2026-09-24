"""Paper-trade the options levels on MNQ, the way the screenshot trades them.

    python strategies/mnq/levelbot.py            # replay every finished session that has saved levels

Each morning `levels.py --save` writes the day's levels (call wall, put wall,
gamma flip, max pain) in NQ points to data/levels/<date>.json.  After the
close this replays the session's one-minute MNQ bars (Yahoo's MNQ=F) against
them:

* the first time price trades up to the call wall, sell 10 MNQ there;
* the first time it trades down to the put wall, buy 10 MNQ there;
* the first touch of the gamma flip, from either side, is faded the same way;
* each trade has a 15-point stop and a 45-point target (three to one), and
  anything still open at 15:55 is closed at the market;
* a touch shows at a minute's close and the order fills at the next minute's
  open (what an alert-driven bot gets); the stop fills at the stop price, or
  at the open when a bar gaps through it; a bar that
  reaches both the stop and the target counts the stop, and so does the
  entry bar when it runs through the stop; 1.25 points a round trip per
  contract.

Entries only 09:35 to 15:30, one trade per level per day.  A second rule
rides along, its settings fixed before the test: on a quiet day, go with the
first break of the day's range after 14:00 (see calm_breakout).  The ledger,
profitable-strategies/futures/options-levels/paper.json, is written once per
session and never recomputed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "soxl"))
import minute                                                                # noqa: E402

LEVELS = ROOT / "data" / "levels"
OUT = ROOT / "profitable-strategies" / "futures" / "options-levels"
LEDGER = OUT / "paper.json"
CONTRACTS, STOP, TARGET, COST = 10, 15.0, 45.0, 1.25
POINT = 2.0                                  # dollars a point per MNQ
TOUCH = 1.0                                  # a level counts as reached within a point


def bars(day: str) -> List[tuple]:
    rows = minute.read("MNQ=F")
    return sorted((t, *v) for t, v in rows.items() if minute.session_of(t) == day)


def et(stamp: str) -> str:
    import datetime as dt
    from zoneinfo import ZoneInfo
    t = dt.datetime.strptime(stamp, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc)
    return t.astimezone(ZoneInfo("America/New_York")).strftime("%H:%M")


def replay(day: str, levels: Dict[str, float]) -> dict:
    b = bars(day)
    if len(b) < 380:
        return {"skipped": f"only {len(b)} bars"}
    trades = []
    busy_until = -1
    plan = []                                                     # (name, level, side)
    if levels.get("call_wall"):
        plan.append(("call wall", levels["call_wall"], -1))
    if levels.get("put_wall"):
        plan.append(("put wall", levels["put_wall"], 1))
    if levels.get("gamma_flip"):
        plan.append(("gamma flip", levels["gamma_flip"], 0))       # side set by the direction it is reached from
    done = set()
    for i in range(1, len(b)):
        t, o, h, l, c, v = b[i]
        clock = et(t)
        if not ("09:35" <= clock <= "15:30") or i <= busy_until:
            continue
        prev_c = b[i - 1][4]
        for name, lvl, side in plan:
            if name in done or i <= busy_until:
                continue
            if side == -1 and prev_c < lvl - TOUCH and h >= lvl - TOUCH:
                s = -1
            elif side == 1 and prev_c > lvl + TOUCH and l <= lvl + TOUCH:
                s = 1
            elif side == 0 and prev_c < lvl - TOUCH and h >= lvl - TOUCH:
                s = -1
            elif side == 0 and prev_c > lvl + TOUCH and l <= lvl + TOUCH:
                s = 1
            else:
                continue
            done.add(name)
            if i + 1 >= len(b):
                break
            k = i + 1                                               # the touch shows at this bar's close: in at the next open
            entry = b[k][1]
            stop, target = entry - s * STOP, entry + s * TARGET
            exit_px, exit_i, why = None, None, ""
            if s * ((b[k][3] if s > 0 else b[k][2]) - stop) <= 0:  # the entry bar itself ran through the stop
                exit_px, exit_i, why = stop, k, "stop"
            for m in range(k + 1, len(b)):
                if exit_px is not None:
                    break
                tm, om, hm, lm, cm, _ = b[m]
                if et(tm) >= "15:55":
                    exit_px, exit_i, why = om, m, "15:55"
                    break
                adverse = hm if s < 0 else lm
                favour = lm if s < 0 else hm
                if s * (adverse - stop) <= 0:
                    exit_px = om if s * (om - stop) < 0 else stop
                    exit_i, why = m, "stop"
                    break
                if s * (favour - target) >= 0:
                    exit_px = om if s * (om - target) > 0 else target
                    exit_i, why = m, "target"
                    break
            if exit_px is None:
                exit_px, exit_i, why = b[-1][4], len(b) - 1, "close"
            pts = s * (exit_px - entry) - COST
            trades.append({"level": name, "side": "short" if s < 0 else "long", "in": et(b[k][0]), "out": et(b[exit_i][0]),
                           "entry": round(entry, 2), "exit": round(exit_px, 2), "why": why, "points": round(pts, 2),
                           "usd": round(pts * POINT * CONTRACTS, 2)})
            busy_until = exit_i
    trades += calm_breakout(day, b, busy_until)
    return {"levels": levels, "trades": trades, "usd": round(sum(x["usd"] for x in trades), 2)}


CALM, CALM_STOP_BP, CALM_TARGET_BP = 0.6, 10.0, 20.0


def calm_breakout(day: str, b: List[tuple], busy_until: int) -> List[dict]:
    """The second rule, fixed before the paper test (strategies/mnq/calmbreak.py): on a day whose
    range by 14:00 is under 60% of the typical pace (the median full-day range of the 20 sessions
    before, times the square root of the time gone), go with the first close beyond the day's range
    between 14:00 and 15:30, at the next minute's open, stop 10 bp, target 20 bp, out by 15:55."""
    rows = minute.read("MNQ=F")
    by: Dict[str, list] = {}
    for t, v in rows.items():
        by.setdefault(minute.session_of(t), []).append(v)
    before = [d for d in sorted(by) if d < day][-20:]
    if len(before) < 15:
        return []
    typical = sorted((max(v[1] for v in by[d]) - min(v[2] for v in by[d])) / by[d][-1][3] for d in before)[len(before) // 2]
    at2 = next((i for i, x in enumerate(b) if et(x[0]) >= "14:00"), None)
    if at2 is None or at2 < 60:
        return []
    hi, lo = max(x[2] for x in b[:at2]), min(x[3] for x in b[:at2])
    if (hi - lo) / b[at2 - 1][4] >= CALM * typical * (at2 / 390) ** 0.5:
        return []
    for i in range(at2, len(b) - 1):
        if et(b[i][0]) > "15:30":
            return []
        c = b[i][4]
        if c > hi or c < lo:
            if i < busy_until:
                return []
            s = 1 if c > hi else -1
            k = i + 1
            entry = b[k][1]
            stop, target = entry * (1 - s * CALM_STOP_BP / 1e4), entry * (1 + s * CALM_TARGET_BP / 1e4)
            exit_px, exit_i, why = None, None, ""
            for m in range(k, len(b)):
                tm, om, hm, lm, cm, _ = b[m]
                if et(tm) >= "15:55":
                    exit_px, exit_i, why = om, m, "15:55"
                    break
                adverse, favour = (lm, hm) if s > 0 else (hm, lm)
                if s * (adverse - stop) <= 0:
                    exit_px, exit_i, why = (om if s * (om - stop) < 0 else stop), m, "stop"
                    break
                if s * (favour - target) >= 0:
                    exit_px, exit_i, why = (om if s * (om - target) > 0 else target), m, "target"
                    break
            if exit_px is None:
                exit_px, exit_i, why = b[-1][4], len(b) - 1, "close"
            pts = s * (exit_px - entry) - COST
            return [{"level": "quiet-day breakout", "side": "long" if s > 0 else "short", "in": et(b[k][0]),
                     "out": et(b[exit_i][0]), "entry": round(entry, 2), "exit": round(exit_px, 2), "why": why,
                     "points": round(pts, 2), "usd": round(pts * POINT * CONTRACTS, 2)}]
        hi, lo = max(hi, b[i][2]), min(lo, b[i][3])
    return []


def main() -> int:
    minute.update(["MNQ=F", "NQ=F"])
    ledger = json.loads(LEDGER.read_text()) if LEDGER.exists() else {
        "rules": {"contracts": CONTRACTS, "stop_points": STOP, "target_points": TARGET, "cost_points": COST,
                  "entries": "09:35-15:30, first touch per level", "flat": "15:55"}, "sessions": {}}
    done_days = set(minute.sessions(["MNQ=F"]))
    OUT.joinpath("paper").mkdir(parents=True, exist_ok=True)
    for f in sorted(LEVELS.glob("*.json")):
        day = f.stem
        if day in ledger["sessions"] or day not in done_days:
            continue
        lv = json.loads(f.read_text())
        res = replay(day, lv.get("nq", {}))
        ledger["sessions"][day] = res
        lines = [f"# Options levels on MNQ, {day}", "",
                 f"Paper, {CONTRACTS} MNQ, {STOP:g}-point stop, {TARGET:g}-point target. P&L ${res.get('usd', 0):+,.2f}.", "",
                 "Levels (NQ): " + ", ".join(f"{k.replace('_', ' ')} {v:,.2f}" for k, v in lv.get("nq", {}).items()), ""]
        if res.get("trades"):
            lines += ["| Level | Side | In | Out | Entry | Exit | Why | Points | $ |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
            lines += [f"| {x['level']} | {x['side']} | {x['in']} | {x['out']} | {x['entry']:,.2f} | {x['exit']:,.2f} | {x['why']} | "
                      f"{x['points']:+.2f} | {x['usd']:+,.2f} |" for x in res["trades"]]
        else:
            lines.append(res.get("skipped", "No level was reached."))
        OUT.joinpath("paper", f"{day}.md").write_text("\n".join(lines) + "\n")
        print(f"{day}: ${res.get('usd', 0):+,.2f} over {len(res.get('trades', []))} trades", flush=True)
    usd = [v.get("usd", 0.0) for v in ledger["sessions"].values() if "trades" in v]
    ledger["summary"] = {"sessions": len(usd), "total": round(sum(usd), 2),
                         "per_day": round(sum(usd) / len(usd), 2) if usd else 0.0,
                         "days_150_plus": sum(u >= 150 for u in usd), "days_down": sum(u < 0 for u in usd),
                         "worst_day": min(usd) if usd else 0.0}
    OUT.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=1))
    print(json.dumps(ledger["summary"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
