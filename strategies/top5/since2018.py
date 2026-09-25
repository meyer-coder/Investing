"""The owner's three leveraged-fund bots, D609, CB51 and CBE3, traded from January 2018 to now: at least
20,000 simulated trades each, before any of them is released.

    python strategies/top5/since2018.py                 # fetch what is missing, then the three
    python strategies/top5/since2018.py d609            # one

This is rigor.py's test, unchanged, with three differences:

* trades start on 2018-01-02 (the rules still see the years before for their
  averages) and run to the last close;
* the wide set is rigor.py's 173 funds plus synthetic 2x funds on 91 more
  large US stocks (EXTRA below), so that each rule reaches 20,000 trades in
  under nine years (on the 173 alone D609 made 16,812 since 2018);
* each bot's own-fund account ($25,000, its own funds) is also checked
  against a funded account's loss limits: how many days lost more than
  $1,000, $2,000 and $3,000 at the close.  Intraday lows are deeper, so these
  counts are a floor.

Every trade goes through evotrader's engine: the rule reads the close, the
order fills at the next open, 8 bp of slippage a side, the genome's own
stops, targets and holding limits.  The comparison that matters is random
timing: the same number of trades on the same funds, held just as long,
entered on random days, 500 times.  A rule that does not beat it is holding a
rising fund, not timing it.

Survivorship: the extra stocks are today's large caps too, which flatters
anything that buys; the random entries share that bias.

Written to profitable-strategies/top5/since-2018/<key>/ (summary.json,
trades.csv.gz) and strategies/top5/since2018.json.
"""
from __future__ import annotations

import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C                                                           # noqa: E402
import rigor as R                                                            # noqa: E402
import universe as U                                                         # noqa: E402

KEYS = ("d609", "cb51", "cbe3")
SINCE = "2018-01-02"
TO = "2026-09-25"                                                            # the last close is the 24th
MIN_TRADES = 20_000
EXTRA = (
    "META TSLA PYPL NOW PANW FTNT ANET MSI APH GLW NXPI ON MPWR EA TTWO CHTR TMUS "
    "V MA COF PGR CME ICE AON AFL PRU TROW STT "
    "ABBV ZTS EW IDXX HCA CI HUM ELV MCK A IQV DXCM ALGN RMD "
    "MDLZ PM KHC EL STZ MNST ROST DG DLTR AZO CMG MAR HLT GM F LULU "
    "ROK PH CMI PCAR GWW FAST CTAS ODFL TT ROP AME LHX "
    "PSX MPC VLO KMI WMB OKE PPG "
    "SRE XEL PEG EQIX PSA O WELL CCI").split()
LIMITS = (1_000.0, 2_000.0, 3_000.0)

_members = U.members


def members(kind: str = "all"):
    out = _members(kind)
    if kind in ("all", "stocks"):
        have = {m[0] for m in out}
        out += [(U.name(s, 2.0), s, 2.0) for s in EXTRA if U.name(s, 2.0) not in have and not C.excluded([s])]
    return out


def setup() -> None:
    """Point rigor.py at 2018 and today, with the wider set."""
    C.END = U.END = TO
    R.START = SINCE
    R.OUT = R.PS / "top5" / "since-2018"
    U.members = members


def limit_days(key: str) -> dict:
    """The bot's own-fund account from 2018: days that lost more than each limit at the close, and the worst."""
    sp = R.spec(key)
    res = C.backtest(sp["genome"], sp["native"], start=SINCE, **sp["native_kw"])
    dates, r = C.daily_returns(res, SINCE, C.END)
    usd = r * C.ACCOUNT
    out = {"sessions": len(usd), "worst_day": round(float(usd.min()), 0)}
    for lim in LIMITS:
        out[f"days_losing_over_{lim:.0f}"] = int((usd <= -lim).sum())
        hit = np.flatnonzero(usd <= -lim)
        out[f"first_day_over_{lim:.0f}"] = dates[hit[0]] if hit.size else None
    return out


def main(argv=None) -> int:
    setup()
    keys = [k.lower() for k in (argv if argv is not None else sys.argv[1:])] or list(KEYS)
    made = U.build()                                                          # synthetic funds not yet cached
    print(f"{made} synthetic funds written; the wide set has {len(U.members())} funds", flush=True)
    path = HERE / "since2018.json"
    done = json.loads(path.read_text()) if path.exists() else {}
    with Pool(max(os.cpu_count() or 2, 2)) as pool:
        for key in keys:
            out = R.study(key, pool)
            row = {k: v for k, v in out.items() if k not in ("funds",)}
            row["nudges"] = {k: v for k, v in out["nudges"].items() if k != "each"}
            row["since"], row["to"] = SINCE, TO
            row["enough_trades"] = out["wide"]["trades"] >= MIN_TRADES
            row["own_limits"] = limit_days(key)
            done[key] = row
            print(f"  {key}: {out['wide']['trades']:,} trades since {SINCE} "
                  f"({'at least' if row['enough_trades'] else 'SHORT of'} {MIN_TRADES:,}); own account days losing "
                  f"over $1,000 / $2,000 / $3,000: {row['own_limits']['days_losing_over_1000']} / "
                  f"{row['own_limits']['days_losing_over_2000']} / {row['own_limits']['days_losing_over_3000']}", flush=True)
            path.write_text(json.dumps(done, indent=1, default=R._plain))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
