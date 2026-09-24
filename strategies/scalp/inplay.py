"""The opening dip scalper on the day's "in play" names, from a pool of 47.

    python strategies/scalp/inplay.py

The fixed list of 17 names the scalper was found on did not carry over to 30
fresh names.  This tries the usual scalper's answer instead of a fixed list:
each morning, rank the pool by how hard each name trades in its first five
minutes (09:30-09:34) against its own typical one-minute range over the
sessions before, and run the unchanged scalper (bot.py: 0.75-ATR drop, 09:35 to
09:45, four-minute hold, two positions) on the top N.  The ranking uses only
data available at 09:35.  Every name in the pool is eligible, so no name was
picked by its results.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "soxl"))
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import minute                                                                # noqa: E402
from bot import bot                                                          # noqa: E402
from events import cost_bp                                                   # noqa: E402
from evotrader.features import build_features                               # noqa: E402
from evotrader.genome import compile_genome                                 # noqa: E402
from evotrader.runner import run_backtest                                   # noqa: E402

FRESH = list(minute.FRESH_NAMES)
POOL = list(minute.SCALP_NAMES) + FRESH
ACCOUNT = 25_000.0
OUT = ROOT / "strategies" / "scalp" / "inplay.json"


def opening_scores(day: str, prior: List[str], data: Dict[str, dict]) -> Dict[str, float]:
    """Each name's 09:30-09:34 range over its typical one-minute range in the
    prior sessions; names a cent costs more than 4 bp of are left out."""
    scores = {}
    for s, rows in data.items():
        first = [v for t, v in sorted(rows.items()) if minute.session_of(t) == day][:5]
        past = [(v[1] - v[2]) / v[3] for t, v in rows.items() if minute.session_of(t) in prior]
        if len(first) < 5 or len(past) < 200:
            continue
        px = first[-1][3]
        if 1e4 * 0.01 / px > 4.0:
            continue
        rng = (max(v[1] for v in first) - min(v[2] for v in first)) / first[0][0]
        scores[s] = rng / float(np.median(past))
    return scores


def day_pnl(day: str, before: str, names: List[str], leverage: float = 1.0, mult: float = 1.0) -> dict:
    u = minute.universe(names, [before, day])
    f = build_features(u)
    idx = [i for i, t in enumerate(u.calendar) if minute.session_of(t) == day]
    slip = {s: cost_bp(np.asarray(u.bars[s].close)[idx]) * mult for s in names}
    r = run_backtest(compile_genome(bot(0.75, 15, "", 4, 2)), u, f, starting_cash=ACCOUNT, commission_bps=0.0,
                     slippage_bps=2.0, record_thoughts=False, intrabar_stops=True, slippage_by_symbol=slip,
                     leverage=leverage, start_bar=max(idx[0] - 30, 1))
    trades = [t for t in r.journal.trades if minute.session_of(t.entry_date) == day]
    return {"pnl": sum(t.pnl for t in trades), "trades": len(trades),
            "bp": [t.ret * 1e4 for t in trades], "names": [t.symbol for t in trades]}


def main() -> int:
    data = {s: minute.read(s) for s in POOL}
    days = minute.sessions(POOL)
    out: Dict[str, dict] = {}
    for top in (5, 8, 12, 47):
        for mult in (1.0, 2.0):
            rows = {}
            for i, d in enumerate(days):
                if i < 3:
                    continue                      # a few sessions to learn each name's typical range
                sc = opening_scores(d, days[:i], data)
                names = sorted(sc, key=sc.get, reverse=True)[:top]
                rows[d] = day_pnl(d, days[i - 1], names, mult=mult)
            usd = np.array([v["pnl"] for v in rows.values()])
            bps = np.concatenate([v["bp"] for v in rows.values()]) if rows else np.zeros(1)
            ds = sorted(rows)
            dev = np.array([rows[d]["pnl"] for d in ds if d <= days[13]])
            test = np.array([rows[d]["pnl"] for d in ds if d > days[13]])
            key = f"top {top} in play, costs x{mult:g}"
            out[key] = {"usd_per_day": round(float(usd.mean()), 1), "median": round(float(np.median(usd)), 1),
                        "days_up": round(float((usd > 0).mean()), 3), "worst": round(float(usd.min()), 0),
                        "trades_per_day": round(float(np.mean([v["trades"] for v in rows.values()])), 1),
                        "bp_per_trade": round(float(bps.mean()), 1), "win": round(float((bps > 0).mean()), 3),
                        "dev_per_day": round(float(dev.mean()), 1), "test_per_day": round(float(test.mean()), 1),
                        "test_days_up": round(float((test > 0).mean()), 3),
                        "by_day": {d: round(rows[d]["pnl"], 0) for d in ds}}
            x = out[key]
            print(f"{key:28s} ${x['usd_per_day']:6.0f}/day median ${x['median']:5.0f} up {x['days_up']:.0%} worst ${x['worst']:5.0f} "
                  f"{x['trades_per_day']:4.1f} tr/d {x['bp_per_trade']:+5.1f}bp win {x['win']:.0%} | sessions 4-14 ${x['dev_per_day']:5.0f} "
                  f"| last 7 ${x['test_per_day']:5.0f} up {x['test_days_up']:.0%}", flush=True)
    OUT.write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
