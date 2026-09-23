"""How steadily a strategy made its money over the last six months.

    python strategies/etf/recent.py [--min 200] [--exclude TSM] [--target 250]

For every stored strategy at --min dollars a session or more over the held-out
six months (on the rebuilt series, and on the real funds where the store has
them), this re-runs the backtest and measures the six months month by month:
the dollars a session in each calendar month (the last days of March count
with April), the share of rolling one-month (21-session) stretches that made
money, the worst of them, and the worst drawdown.  A strategy making more than
--target is also measured sized down to --target, with that share of the
account in each trade: the same trades, smaller.

Reliable here means every month made money, at least 90% of one-month
stretches did, and the sized drawdown stayed under 25%.  The six months were
never used to breed the strategies, but choosing among them on these months
makes the months in-sample for the choice; the store's other gates (profit
over 2019-2026 and 2012-2018, and at triple slippage) still apply.

Writes strategies/etf/recent.json (every candidate, best first).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "etf"))
from gauntlet import ACCOUNT, SLIP, WINDOWS, backtest, load_store              # noqa: E402
from evotrader.genome import Genome                                            # noqa: E402

OUT = ROOT / "strategies" / "etf" / "recent.json"
MONTH = 21


def daily(result, a: str, b: str):
    """Dates and daily returns of the equity curve inside [a, b]."""
    d, e = result.journal.equity_dates, np.asarray(result.journal.equity, dtype=float)
    idx = [i for i, x in enumerate(d) if a <= x <= b]
    lo = max(idx[0] - 1, 0)
    e = e[lo: idx[-1] + 1]
    return [d[i] for i in idx], e[1:] / e[:-1] - 1.0


def profile(dates, r, f: float = 1.0) -> dict:
    usd = f * r * ACCOUNT
    months = {}
    for d, x in zip(dates, usd):
        m = d[:7] if d[:7] != "2026-03" else "2026-04"
        months.setdefault(m, []).append(x)
    roll = np.convolve(usd, np.ones(MONTH), mode="valid") / MONTH
    eq = np.cumprod(1.0 + f * r)
    dd = float(np.min(eq / np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:] - 1.0))
    weeks = np.convolve(usd, np.ones(5), mode="valid") / 5
    return {"usd_per_session": round(float(usd.mean()), 1),
            "months": {m: round(float(np.mean(v)), 1) for m, v in months.items()},
            "worst_month": round(float(min(np.mean(v) for v in months.values())), 1),
            "months_up": int(sum(np.mean(v) > 0 for v in months.values())), "months_n": len(months),
            "month_stretches_up": round(float((roll > 0).mean()), 3),
            "worst_month_stretch": round(float(roll.min()), 1),
            "week_stretches_up": round(float((weeks > 0).mean()), 3),
            "max_drawdown": round(dd, 4), "worst_day": round(float(usd.min()), 0),
            "days_up": round(float((usd > 0).mean()), 3),
            "days_in_market": round(float((r != 0).mean()), 3)}


def reliable(p: dict) -> bool:
    return (p["months_up"] == p["months_n"] and p["month_stretches_up"] >= 0.9
            and p["max_drawdown"] > -0.25)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=float, default=200.0)
    ap.add_argument("--exclude", default="TSM", help="skip strategies on these underlyings, comma separated")
    ap.add_argument("--target", type=float, default=250.0)
    args = ap.parse_args(argv)
    bad = [x for x in args.exclude.split(",") if x]
    a, b = WINDOWS["held_out"]
    rows = []
    for key, v in load_store()["strategies"].items():
        if any(x in s for s in v["symbols"] for x in bad):
            continue
        ho = v["windows"]["held_out"]["usd_per_session"]
        real = v["verdict"].get("real_held_out_usd")
        if ho < args.min or (real is not None and real < args.min):
            continue
        res = backtest(Genome.from_dict(v["genome"]), v["symbols"], SLIP)
        dates, r = daily(res, a, b)
        full = profile(dates, r)
        f = min(1.0, args.target / full["usd_per_session"]) if full["usd_per_session"] > 0 else 1.0
        sized = profile(dates, r, f)
        rows.append({"key": key, "name": v["genome"]["name"], "symbols": v["symbols"], "source": v["source"],
                     "real_held_out_usd": real, "train_usd": v["windows"]["train"]["usd_per_session"],
                     "older_usd": (v["windows"].get("older") or {}).get("usd_per_session"),
                     "older_profitable": v["verdict"].get("older_profitable"),
                     "full": full, "fraction": round(f, 3), "sized": sized,
                     "reliable": reliable(sized)})
    rows.sort(key=lambda x: (x["reliable"], x["sized"]["worst_month"], x["sized"]["max_drawdown"]), reverse=True)
    OUT.write_text(json.dumps(rows, indent=1))
    ok = [x for x in rows if x["reliable"]]
    print(f"{len(rows)} candidates at ${args.min:.0f}+, {len(ok)} reliable")
    for x in rows[:25]:
        s, fl = x["sized"], x["full"]
        print(f"{'R' if x['reliable'] else ' '} {','.join(x['symbols']):28s} {x['name'][:38]:38s} "
              f"full ${fl['usd_per_session']:5.0f} dd {fl['max_drawdown']:.0%} | at {x['fraction']:.0%}: "
              f"${s['usd_per_session']:4.0f} worst mo ${s['worst_month']:5.0f} up {s['months_up']}/{s['months_n']} "
              f"1mo-up {s['month_stretches_up']:.0%} dd {s['max_drawdown']:.0%} | real {x['real_held_out_usd']} "
              f"train {x['train_usd']:.0f} older {x['older_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
