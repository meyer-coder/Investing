"""The residual dip scalper: buy a name's own drop in the opening minutes.

    python strategies/scalp/residbot.py

The residual study (residual.py) found the one setup that kept an edge on 30
names it was never tuned on: a name whose one-minute return, less the average
of the other names that minute, sits three or more standard deviations below
its last 20 minutes of residuals, bought in the first quarter hour and sold a
few minutes later.  Here it runs as one bot across all 47 names in the
engine: next-minute fills, each name's own cost (a cent plus 1 bp each way),
a few positions at once, nothing held after 15:55.  Each run adds the
residual as a feature ("resid_z"), computed only from minutes already closed.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "soxl"))
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import minute                                                                # noqa: E402
from events import cost_bp                                                   # noqa: E402
from inplay import FRESH                                                     # noqa: E402
from evotrader.features import FEATURE_SET                                  # noqa: E402
from evotrader.features import build_features                               # noqa: E402
from evotrader.genome import Genome, compile_genome                         # noqa: E402
from evotrader.runner import run_backtest                                   # noqa: E402

POOL = list(minute.SCALP_NAMES) + FRESH
ACCOUNT = 25_000.0
FLAT = "minute_of_day >= 955"
ALLOWED = frozenset(FEATURE_SET) | {"resid_z"}
OUT = ROOT / "strategies" / "scalp" / "residbot.json"


def add_residual(u, f, window: int = 20) -> None:
    """resid_z for every name: its one-minute return less the others' average,
    over the standard deviation of its previous `window` residuals."""
    names = list(u.symbols)
    stamps = u.calendar
    sess = np.array([minute.session_of(t) for t in stamps])
    new = np.concatenate([[True], sess[1:] != sess[:-1]])
    C = np.array([np.asarray(u.bars[s].close, dtype=float) for s in names])
    R = np.full_like(C, np.nan)
    R[:, 1:] = C[:, 1:] / C[:, :-1] - 1.0
    R[:, new] = np.nan
    tot, cnt = np.nansum(R, axis=0), np.sum(~np.isnan(R), axis=0)
    for i, s in enumerate(names):
        mine = ~np.isnan(R[i])
        others = (tot - np.nan_to_num(R[i])) / np.maximum(cnt - mine.astype(int), 1)
        resid = R[i] - others
        z = np.full(len(stamps), np.nan)
        for k in range(window, len(stamps)):
            w = resid[k - window:k]
            sd = np.nanstd(w)
            if sd > 0 and not np.isnan(resid[k]):
                z[k] = resid[k] / sd
        f.matrix[s]["resid_z"] = z
    f.first_valid["resid_z"] = window + 1


def bot(z: float, window: int, hold: int, slots: int) -> Genome:
    return Genome.from_dict({
        "name": f"Residual Dip z<-{z}/{window}m/hold {hold}m/{slots} slots",
        "thesis": "a name's own sharp drop in the opening minutes snaps back",
        "entry_rules": [{"when": f"resid_z < -{z} and minutes_since_open >= 5 and minutes_since_open <= {window}",
                         "weight": 1.0}],
        "exit_rules": [{"when": FLAT}],
        "risk": {"max_position_pct": 1.0 / slots, "max_positions": slots, "max_gross_exposure": 1.0,
                 "stop_loss_pct": 0.0, "take_profit_pct": 0.0, "trailing_stop_pct": 0.0,
                 "max_hold_bars": hold - 1}})


def run(g: Genome, u, f, slip: Dict[str, float], leverage: float = 1.0, mult: float = 1.0) -> dict:
    r = run_backtest(compile_genome(g, ALLOWED), u, f, starting_cash=ACCOUNT, commission_bps=0.0,
                     slippage_bps=2.0, record_thoughts=False, intrabar_stops=True, leverage=leverage,
                     slippage_by_symbol={s: v * mult for s, v in slip.items()})
    j = r.journal
    last: Dict[str, float] = {}
    for st, e in zip(j.equity_dates, j.equity):
        last[minute.session_of(st)] = float(e)
    prev, days = ACCOUNT, {}
    for d in sorted(last):
        days[d] = (last[d] / prev - 1.0) * ACCOUNT
        prev = last[d]
    usd = np.array(list(days.values()))
    t = j.trades
    orig = set(minute.SCALP_NAMES)
    return {"usd_per_day": round(float(usd.mean()), 1), "median": round(float(np.median(usd)), 1),
            "days_up": round(float((usd > 0).mean()), 3), "worst_day": round(float(usd.min()), 0),
            "trades_per_day": round(len(t) / len(usd), 1),
            "win_rate": round(float(np.mean([x.pnl > 0 for x in t])), 3) if t else 0.0,
            "avg_trade_bp": round(float(np.mean([x.ret for x in t])) * 1e4, 1) if t else 0.0,
            "avg_hold_min": round(float(np.mean([x.bars_held for x in t])), 2) if t else 0.0,
            "pnl_original_names": round(sum(x.pnl for x in t if x.symbol in orig), 0),
            "pnl_fresh_names": round(sum(x.pnl for x in t if x.symbol not in orig), 0),
            "by_day": {d: round(v, 0) for d, v in days.items()}}


def universe(sessions: Sequence[str]):
    u = minute.universe(POOL, sessions)
    f = build_features(u)
    add_residual(u, f)
    return u, f


def main() -> int:
    days = minute.sessions(POOL)
    blocks = {"sessions 1-7": days[:7], "sessions 8-14": days[7:14], "sessions 15-21": days[14:]}
    data = {k: universe(v) for k, v in blocks.items()}
    slip = {s: cost_bp(np.asarray(data["sessions 1-7"][0].bars[s].close)) for s in POOL}
    out = {}
    for z, w, h, slots in itertools.product((2.5, 3.0, 4.0), (15, 20), (3, 4), (2, 3, 4)):
        g = bot(z, w, h, slots)
        res = {k: run(g, u, f, slip) for k, (u, f) in data.items()}
        out[g.name] = res
        print(f"{g.name[:46]:46s} " + " | ".join(
            f"${r['usd_per_day']:5.0f} up {r['days_up']:.0%} {r['trades_per_day']:4.1f}tr {r['avg_trade_bp']:+5.1f}bp"
            for r in res.values()), flush=True)
    OUT.write_text(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
