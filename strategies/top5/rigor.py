"""The top five, tested hard: each rule trades on its own funds and on 170-odd others until it has well
over 10,000 trades, every one of them simulated bar by bar.

    python strategies/top5/rigor.py              # the five, the two paper split bots and the extra leg
    python strategies/top5/rigor.py cb51 d609    # some

For each strategy (rank.py's top five by dollars a day, 2012-2026, and "ml",
NQ at 2x Managed Long, the leg book.py adds):

1. Its own funds, as far back as they go: dollars a day on $25,000, the worst
   day, the worst losing stretch, the years, and holding the same funds.
2. The same rule, unchanged, on each fund of a wide set, one fund at a time:
   for the five, 143 synthetic 2x stock funds and 30 synthetic 3x ETF funds
   (universe.py) from 2005, 8 bp slippage a side; for Managed Long, the same
   30 ETFs and 143 stocks themselves at 2x account leverage from 2000 (so the
   2000-2002 and 2008 crashes are in), 2 bp slippage and 0.2 bp commission.
   Every trade goes through evotrader's engine (signal on the close, fill at
   the next open, the genome's own stops, targets and holding limits).  The
   pooled trades are the 10,000+ sample.
3. Random timing: on every fund, as many trades as the rule made there, with
   its own holding times, entered on random days (the same next-open fills and
   costs), 500 times.  A rule whose trades beat random entries on the same
   funds times the market; one that does not is only holding a rising fund.
4. Costs: the same trades at three and five times the slippage.
5. Nudges: every number in the rules and the risk settings moved 20% either
   way, one at a time, on the strategy's own funds and 25 of the others.
6. Luck in the order of trades: the own-fund trades resampled 2,000 times into
   new sequences, for the spread of the worst losing stretch.

Written to profitable-strategies/top5/<key>/ (summary.json, trades.csv.gz)
and strategies/top5/rigor.json.
"""
from __future__ import annotations

import csv
import gzip
import json
import os
import re
import sys
from multiprocessing import Pool
from pathlib import Path
from typing import Dict, List

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C                                                           # noqa: E402
import universe as U                                                         # noqa: E402

PS = C.ROOT / "profitable-strategies"
OUT = PS / "top5"
START = "2005-01-03"
SLIP = 8.0
PERMUTATIONS, RESAMPLES = 500, 2000
TOP5 = {"cb51": "25_muu_soxl_uptrend_dip_bred_cb51.json", "d609": "02_muu_trend_breakout_bred_d609.json",
        "cbe3": "18_muu_soxl_uptrend_dip_bred_cbe3.json", "852d": "12_amdl_uptrend_dip_bred_852d.json",
        "01d4": "35_soxl_tqqq_tecl_uptrend_dip_bred_01d4.json"}
#: beyond the five: two more of the leveraged-fund list that run on paper as split bots 1 and 2
PAPER = {"q05": "05_muu_quick_dip_2_dip_above_the_200_day_2_target_10_stop_4_days_max.json",
         "r24": "24_nvdl_amdl_short_trend_rider_above_a_rising_10_day.json"}
#: and the leg book.py adds: NQ at 2x, Managed Long, run on the ETFs and stocks themselves at 2x
EXTRA = {"ml": "Managed Long"}
NUM = re.compile(r"(?<![A-Za-z_\d.])(\d+\.?\d*)(?![A-Za-z_\d(])")
RISK_KEYS = ("stop_loss_pct", "take_profit_pct", "trailing_stop_pct", "max_hold_bars", "min_hold_bars", "cooldown_bars")


def _plain(o):
    return o.item() if hasattr(o, "item") else str(o)


def spec(key: str) -> dict:
    """What to run: the genome, its own funds and costs, and the wide set with its costs."""
    if key in TOP5 or key in PAPER:
        f = TOP5.get(key) or PAPER[key]
        d = json.loads((PS / "leveraged-etfs" / f).read_text())
        return {"key": key, "name": d["genome"]["name"], "source": f"leveraged-etfs/{f}", "genome": d["genome"],
                "native": d["symbols"], "start": START, "native_kw": {"slippage": SLIP}, "wide_kw": {"slippage": SLIP},
                "members": [(syn, "stock 2x" if k == 2.0 else "ETF 3x") for syn, _, k in U.members()], "hold_lev": 1.0,
                "alike": {"SOXL": ("SMH", "SOXX"), "TQQQ": ("QQQ",), "TECL": ("XLK",)}}
    name = EXTRA[key]
    g = next(x for x in json.loads((PS / "nq-2x" / "all.json").read_text())["genomes"] if x["name"] == name)
    return {"key": key, "name": f"NQ E-mini at 2x: {name}", "source": "nq-2x/all.json", "genome": g, "native": ["NQ1!"],
            "start": "2000-01-03", "native_kw": {"slippage": 1.0, "commission": 0.2, "leverage": 2.0},
            "wide_kw": {"slippage": 2.0, "commission": 0.2, "leverage": 2.0},
            "members": [(x, "ETF 1x") for x in U.ETFS] + [(x, "stock 1x") for x in U.STOCKS], "hold_lev": 2.0,
            "alike": {"NQ1!": ("QQQ",)}}


# ------------------------------------------------------------------ one fund, one rule

def run_fund(args):
    """(genome, symbol, start, costs) -> the trades and the fund's own-account days."""
    genome, sym, start, kw = args
    try:
        res = C.backtest(genome, [sym], start=start, **kw)
    except Exception as e:                                                   # a fund too short for the warm-up
        return sym, [], {}, str(e)[:80]
    trades = [(t.symbol, t.entry_date, t.exit_date, round(t.ret, 6), t.bars_held) for t in res.journal.trades]
    dates, r = C.daily_returns(res, start, C.END)
    st = C.day_stats(r)
    if dates:
        st["first"], st["last"] = dates[0], dates[-1]
    return sym, trades, st, ""


def hold_stats(sym: str, a: str, b: str, lev: float = 1.0) -> Dict[str, float]:
    """Holding the fund over the same days, at the account leverage the rule uses."""
    u, _ = C.market([sym])
    bars = u.bars[sym]
    c = np.asarray(bars.close, dtype=float)
    idx = [i for i, d in enumerate(bars.dates) if a <= d <= b and i > 0]
    r = np.array([c[i] / c[i - 1] - 1 for i in idx]) * lev
    return C.day_stats(r)


# ------------------------------------------------------------------ random timing

def random_means(trades: List[tuple], rng: np.random.Generator, n: int, cost_bp: float, start: str) -> np.ndarray:
    """Pooled mean trade return of `n` random-timing books: on each fund, as many trades as the rule made
    there with its own holding times, entered at the open of random days and sold at the open `bars_held`
    days later, both sides paying the costs (bp a side)."""
    by: Dict[str, List[tuple]] = {}
    for t in trades:
        by.setdefault(t[0], []).append(t)
    sums = np.zeros(n)
    count = 0
    for sym, ts in by.items():
        u, _ = C.market([sym])
        bars = u.bars[sym]
        o = np.asarray(bars.open, dtype=float)
        lo = max(C.first_on_or_after(list(bars.dates), start), 252)      # where the rule could first trade
        holds = np.array([max(int(t[4]), 1) for t in ts])
        hi = len(o) - 1
        k = len(ts)
        starts = rng.integers(lo, np.maximum(hi - holds, lo + 1), size=(n, k))
        ends = np.minimum(starts + holds[None, :], hi)
        r = o[ends] / o[starts] - 1.0 - 2 * cost_bp * 1e-4
        sums += r.sum(axis=1)
        count += k
    return sums / max(count, 1)


# ------------------------------------------------------------------ nudges

def nudged(genome: dict, scale: float) -> List[tuple]:
    """Every number in the rules and the risk settings moved by `scale`, one at a time: (label, genome)."""
    out = []
    for part in ("entry_rules", "exit_rules"):
        for i, rule in enumerate(genome[part]):
            for m in NUM.finditer(rule["when"]):
                v = float(m.group(1))
                if v == 0 or m.group(1) in ("0.0001",):
                    continue
                nv = v * scale
                txt = f"{nv:.4g}" if "." in m.group(1) else str(max(int(round(nv)), 1))
                if txt == m.group(1):
                    continue
                g = json.loads(json.dumps(genome))
                g[part][i]["when"] = rule["when"][:m.start(1)] + txt + rule["when"][m.end(1):]
                out.append((f"{part[:-6]} {i + 1}: {m.group(1)} -> {txt}", g))
    for key in RISK_KEYS:
        v = genome["risk"].get(key) or 0
        if not v:
            continue
        nv = v * scale if isinstance(v, float) and v < 1 else max(int(round(v * scale)), 1)
        if nv == v:
            continue
        g = json.loads(json.dumps(genome))
        g["risk"][key] = nv
        out.append((f"risk {key}: {v} -> {nv}", g))
    return out


def run_book(args):
    """(label, genome, symbols, start, costs) -> the rule on those funds, one at a time, pooled."""
    label, genome, symbols, start, kw = args
    rets, usd = [], []
    for sym in symbols:
        try:
            res = C.backtest(genome, [sym], start=start, **kw)
        except Exception:
            continue
        rets += [t.ret for t in res.journal.trades]
        _, r = C.daily_returns(res, start, C.END)
        if r.size:
            usd.append(float(r.mean() * C.ACCOUNT))
    a = np.asarray(rets)
    return label, {"trades": int(a.size), "mean_bp": round(float(a.mean() * 1e4), 1) if a.size else 0.0,
                   "usd_per_day": round(float(np.mean(usd)), 1) if usd else 0.0}


def own_book(args):
    label, genome, symbols, start, kw = args
    try:
        res = C.backtest(genome, symbols, start=start, **kw)
    except Exception:
        return label, {}
    _, r = C.daily_returns(res, start, C.END)
    return label, {"usd_per_day": C.day_stats(r).get("usd_per_day", 0.0), "trades": len(res.journal.trades)}


# ------------------------------------------------------------------ one strategy

def study(key: str, pool: Pool) -> dict:
    sp = spec(key)
    genome, native, name, start = sp["genome"], sp["native"], sp["name"], sp["start"]
    kinds = dict(sp["members"])
    cost_bp = sp["wide_kw"]["slippage"] + sp["wide_kw"].get("commission", 0.0)
    folder = OUT / key
    folder.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {name} ({key}) on {', '.join(native)}", flush=True)
    rng = np.random.default_rng(int(key, 16) if all(ch in "0123456789abcdef" for ch in key) else 7)

    # 1. own funds
    res = C.backtest(genome, native, start=start, **sp["native_kw"])
    dates, r = C.daily_returns(res, start, C.END)
    own_trades = np.array([t.ret for t in res.journal.trades])
    own = {"funds": native, "from": dates[0], "to": dates[-1], **C.day_stats(r), **C.trade_stats(own_trades)}
    years = {}
    for dd, x in zip(dates, r):
        years.setdefault(dd[:4], []).append(x)
    own["years_usd_per_day"] = {y: round(float(np.mean(v) * C.ACCOUNT), 1) for y, v in sorted(years.items())}
    own["years_up"] = sum(np.mean(v) > 0 for v in years.values())
    own["years"] = len(years)
    hs = [hold_stats(s, dates[0], dates[-1], sp["hold_lev"]) for s in native]
    own["hold_usd_per_day"] = round(float(np.mean([h["usd_per_day"] for h in hs])), 1)
    own["hold_worst_stretch"] = round(float(np.mean([h["worst_stretch"] for h in hs])), 0)
    print(f"  own funds {own['from']}..{own['to']}: ${own['usd_per_day']:+.1f} a day, Sharpe {own['sharpe']:+.2f}, "
          f"{own['trades']} trades, worst stretch ${own['worst_stretch']:+,.0f}; holding them ${own['hold_usd_per_day']:+.1f} "
          f"(worst stretch ${own['hold_worst_stretch']:+,.0f})", flush=True)

    # 6. the order of the own-fund trades
    eqs = np.cumsum(rng.choice(own_trades, size=(RESAMPLES, own_trades.size)) * C.ACCOUNT, axis=1)
    dds = (eqs - np.maximum.accumulate(np.concatenate([np.zeros((RESAMPLES, 1)), eqs], axis=1), axis=1)[:, 1:]).min(axis=1)
    own["resampled_worst_stretch"] = {"median": round(float(np.median(dds)), 0), "p05": round(float(np.percentile(dds, 5)), 0),
                                      "p95": round(float(np.percentile(dds, 95)), 0)}
    own["resampled_loses_money"] = round(float((eqs[:, -1] < 0).mean()), 3)

    # 2. the wide set, one fund at a time
    jobs = [(genome, sym, start, sp["wide_kw"]) for sym, _ in sp["members"]]
    rows, all_trades, skipped = [], [], []
    for sym, trades, st, err in pool.imap_unordered(run_fund, jobs, chunksize=4):
        if err or not trades:
            skipped.append(sym)
            continue
        a = np.array([t[3] for t in trades])
        rows.append({"fund": sym, "kind": kinds[sym], "trades": len(trades),
                     "mean_bp": round(float(a.mean() * 1e4), 1), "usd_per_day": st.get("usd_per_day", 0.0),
                     "sharpe": st.get("sharpe", 0.0), "worst_stretch": st.get("worst_stretch", 0.0),
                     "days_in_market": st.get("days_in_market", 0.0), "first": st.get("first"), "last": st.get("last")})
        all_trades += trades
    for row in rows:
        h = hold_stats(row["fund"], row["first"], row["last"], sp["hold_lev"])
        row["hold_usd_per_day"] = h.get("usd_per_day", 0.0)
        row["hold_sharpe"] = h.get("sharpe", 0.0)
        row["hold_worst_stretch"] = h.get("worst_stretch", 0.0)
    rets = np.array([t[3] for t in all_trades])
    wide = {"funds": len(rows), "skipped": skipped, **C.trade_stats(rets)}
    boot = np.array([rng.choice(rets, size=rets.size).mean() for _ in range(1000)])
    wide["mean_bp_95ci"] = [round(float(np.percentile(boot, 2.5) * 1e4), 1), round(float(np.percentile(boot, 97.5) * 1e4), 1)]
    wide["funds_profitable"] = round(float(np.mean([x["usd_per_day"] > 0 for x in rows])), 3)
    wide["funds_beat_holding"] = round(float(np.mean([x["usd_per_day"] > x["hold_usd_per_day"] for x in rows])), 3)
    wide["funds_better_sharpe_than_holding"] = round(float(np.mean([x["sharpe"] > x["hold_sharpe"] for x in rows])), 3)
    wide["usd_per_day_median_fund"] = round(float(np.median([x["usd_per_day"] for x in rows])), 1)
    wide["hold_usd_per_day_median_fund"] = round(float(np.median([x["hold_usd_per_day"] for x in rows])), 1)
    for kind in sorted(set(kinds.values())):
        sub = [x for x in rows if x["kind"] == kind]
        ks = {x["fund"] for x in sub}
        a = np.array([t[3] for t in all_trades if t[0] in ks])
        wide[kind] = {"funds": len(sub), **C.trade_stats(a),
                      "funds_profitable": round(float(np.mean([x["usd_per_day"] > 0 for x in sub])), 3) if sub else 0.0,
                      "usd_per_day_median_fund": round(float(np.median([x["usd_per_day"] for x in sub])), 1) if sub else 0.0,
                      "hold_usd_per_day_median_fund": round(float(np.median([x["hold_usd_per_day"] for x in sub])), 1) if sub else 0.0}
    # by the year each trade closed
    yr: Dict[str, List[float]] = {}
    for t in all_trades:
        yr.setdefault(t[2][:4], []).append(t[3])
    wide["years"] = {y: {"trades": len(v), "mean_bp": round(float(np.mean(v) * 1e4), 1)} for y, v in sorted(yr.items())}
    wide["years_up"] = sum(v["mean_bp"] > 0 for v in wide["years"].values())
    # never seen in breeding: the funds other than its own, and on its own funds the years before 2019
    alike = sp["alike"]
    own_under = {s.split(".")[0] for s in native} | {x for s in native for x in alike.get(s, ())}
    unseen = np.array([t[3] for t in all_trades if t[0].split(".")[0] not in own_under])
    wide["other_funds_only"] = C.trade_stats(unseen)
    print(f"  wide set: {wide['trades']:,} trades on {wide['funds']} funds, mean {wide['mean_bp']:+.1f} bp "
          f"(95% {wide['mean_bp_95ci'][0]:+.1f} to {wide['mean_bp_95ci'][1]:+.1f}), win {wide['win_rate']:.0%}, PF {wide['profit_factor']:.2f}, "
          f"t {wide['t_stat']:+.1f}; funds profitable {wide['funds_profitable']:.0%}, beat holding {wide['funds_beat_holding']:.0%}", flush=True)

    # 3. random timing on the same funds
    rnd = random_means(all_trades, rng, PERMUTATIONS, cost_bp, start)
    wide["random_mean_bp"] = round(float(rnd.mean() * 1e4), 1)
    wide["random_mean_bp_p95"] = round(float(np.percentile(rnd, 95) * 1e4), 1)
    wide["timing_edge_bp"] = round(float((rets.mean() - rnd.mean()) * 1e4), 1)
    wide["p_value_vs_random"] = round(float((rnd >= rets.mean()).mean()), 4)
    print(f"  random timing, same funds, holds and costs: mean {wide['random_mean_bp']:+.1f} bp (95th pct "
          f"{wide['random_mean_bp_p95']:+.1f}); edge {wide['timing_edge_bp']:+.1f} bp a trade, p = {wide['p_value_vs_random']}", flush=True)

    # 4. costs
    slip = sp["wide_kw"]["slippage"]
    wide["mean_bp_3x_slippage"] = round(float((rets.mean() - 2 * 2 * slip * 1e-4) * 1e4), 1)
    wide["mean_bp_5x_slippage"] = round(float((rets.mean() - 2 * 4 * slip * 1e-4) * 1e4), 1)

    # 5. nudges
    sample = [m[0] for m in sp["members"]]
    sample = sorted(np.random.default_rng(11).choice(sample, size=25, replace=False).tolist())
    jobs, own_jobs = [], []
    for scale in (0.8, 1.2):
        for label, g in nudged(genome, scale):
            jobs.append((f"x{scale}: {label}", g, sample, start, sp["wide_kw"]))
            own_jobs.append((f"x{scale}: {label}", g, native, start, sp["native_kw"]))
    base_wide = run_book(("base", genome, sample, start, sp["wide_kw"]))[1]
    nudges = {label: {"wide25": v} for label, v in pool.imap_unordered(run_book, jobs)}
    for label, v in pool.imap_unordered(own_book, own_jobs):
        nudges.setdefault(label, {})["own"] = v
    ok_wide = [v["wide25"]["mean_bp"] > 0 for v in nudges.values() if "wide25" in v]
    ok_own = [v["own"].get("usd_per_day", 0) > 0 for v in nudges.values() if v.get("own")]
    nudge = {"count": len(nudges), "base_wide25": base_wide, "base_own_usd_per_day": own["usd_per_day"],
             "share_profitable_wide25": round(float(np.mean(ok_wide)), 3) if ok_wide else 0.0,
             "share_profitable_own": round(float(np.mean(ok_own)), 3) if ok_own else 0.0,
             "own_usd_per_day_range": [round(min(v["own"]["usd_per_day"] for v in nudges.values() if v.get("own")), 1),
                                       round(max(v["own"]["usd_per_day"] for v in nudges.values() if v.get("own")), 1)] if ok_own else None,
             "wide25_mean_bp_range": [min(v["wide25"]["mean_bp"] for v in nudges.values() if "wide25" in v),
                                      max(v["wide25"]["mean_bp"] for v in nudges.values() if "wide25" in v)] if ok_wide else None,
             "each": nudges}
    print(f"  nudges: {nudge['count']}; own funds profitable in {nudge['share_profitable_own']:.0%} "
          f"(${nudge['own_usd_per_day_range']} a day), 25 other funds in {nudge['share_profitable_wide25']:.0%} "
          f"({nudge['wide25_mean_bp_range']} bp)", flush=True)

    out = {"key": key, "name": name, "file": sp["source"], "costs": {"own": sp["native_kw"], "wide": sp["wide_kw"]}, "rules": {"entry": [x["when"] for x in genome["entry_rules"]],
           "exit": [x["when"] for x in genome["exit_rules"]], "risk": {k: v for k, v in genome["risk"].items() if v}},
           "own": own, "wide": wide, "nudges": nudge, "funds": sorted(rows, key=lambda x: -x["usd_per_day"])}
    (folder / "summary.json").write_text(json.dumps(out, indent=1, default=_plain))
    with gzip.open(folder / "trades.csv.gz", "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["fund", "entry_date", "exit_date", "return", "bars_held"])
        w.writerows(sorted(all_trades, key=lambda t: (t[1], t[0])))
    return out


def main(argv=None) -> int:
    keys = (argv if argv is not None else sys.argv[1:]) or list(TOP5) + list(PAPER) + list(EXTRA)
    OUT.mkdir(parents=True, exist_ok=True)
    path = C.ROOT / "strategies" / "top5" / "rigor.json"
    done = json.loads(path.read_text()) if path.exists() else {}
    with Pool(max(os.cpu_count() or 2, 2)) as pool:
        for key in keys:
            out = study(key, pool)
            done[key] = {k: v for k, v in out.items() if k not in ("funds",)}
            done[key]["nudges"] = {k: v for k, v in out["nudges"].items() if k != "each"}
            path.write_text(json.dumps(done, indent=1, default=_plain))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
