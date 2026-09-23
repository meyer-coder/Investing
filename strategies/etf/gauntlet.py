"""The bar every leveraged-ETF strategy has to clear, and the store it goes into.

    python strategies/etf/gauntlet.py harvest RUN_ID [RUN_ID ...] [--top 20]
    python strategies/etf/gauntlet.py file CANDIDATES.json --symbols A,B

Account: $25,000 cash, one position with the whole account, fills at the next
open, no commission, 8 bp slippage a side.  One backtest from 2012 to today;
every window is read from it:

  older     2012-01-03 .. 2018-12-31
  train     2019-01-02 .. 2026-03-20   the only window the breeding saw
  held_out  2026-03-23 .. 2026-09-21   never used for breeding
  last_12m  2025-09-22 .. 2026-09-21
  stress    the whole run again at 24 bp slippage a side (3x)

Single-stock funds trade on their synthetic daily-reset series back to 2012
(strategies/etf/synth.py); "real" re-runs the strategy on the real fund
(NVDA.2X -> NVDL ...) over its own life, so the held-out result on the fund
you would actually buy is reported beside the synthetic one.

Verdict:
  profitable   held-out: gain, profit factor > 1, 3+ trades;
               train: gain, profit factor > 1.1, 30+ trades;
               both still a gain at 3x slippage
  shown        profitable and at least $80 a session over the held-out months
Everything profitable is kept in strategies/etf/store.json; the report shows
only what is shown.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from evotrader.data import load_universe                                   # noqa: E402
from evotrader.features import build_features                              # noqa: E402
from evotrader.genome import Genome, compile_genome                        # noqa: E402
from evotrader.runner import run_backtest                                  # noqa: E402

ACCOUNT = 25_000.0
SLIP, STRESS_SLIP = 8.0, 24.0
START, END = "2011-01-01", "2026-09-22"
WINDOWS = {"older": ("2012-01-03", "2018-12-31"), "train": ("2019-01-02", "2026-03-20"),
           "held_out": ("2026-03-23", "2026-09-21"), "last_12m": ("2025-09-22", "2026-09-21")}
SHOW_USD = 80.0
STORE = ROOT / "strategies" / "etf" / "store.json"

#: synthetic series -> the real fund it stands for
REAL = {"NVDA.2X": "NVDL", "NVDA.-2X": "NVDQ", "AMD.2X": "AMDL", "AVGO.2X": "AVGX", "TSM.2X": "TSMX",
        "MU.2X": "MUU", "SMCI.2X": "SMCX", "PLTR.2X": "PTIR", "MSFT.2X": "MSFU", "AAPL.2X": "AAPU",
        "GOOGL.2X": "GGLL", "META.2X": "METU", "AMZN.2X": "AMZU", "TSLA.2X": "TSLL", "ORCL.2X": "ORCX",
        # FTEC has no leveraged fund of its own; its tech-sector cousins stand in
        "FTEC.2X": "ROM", "FTEC.3X": "TECL"}

_markets: Dict[Tuple[str, ...], tuple] = {}


def market(symbols: Sequence[str]):
    key = tuple(symbols)
    if key not in _markets:
        u = load_universe(list(symbols), START, END, min_bars=100)
        _markets[key] = (u, build_features(u))
    return _markets[key]


def _first_on_or_after(dates: List[str], d: str) -> int:
    for i, x in enumerate(dates):
        if x >= d:
            return i
    return len(dates)


def window_stats(result, a: str, b: str) -> dict:
    j = result.journal
    dates, eq = j.equity_dates, np.asarray(j.equity, dtype=float)
    idx = [i for i, d in enumerate(dates) if a <= d <= b]
    if len(idx) < 5:
        return {}
    lo = max(idx[0] - 1, 0)
    e = eq[lo: idx[-1] + 1]
    r = e[1:] / e[:-1] - 1.0
    trades = [t for t in j.trades if a <= t.exit_date <= b]
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gw = sum(t.pnl for t in wins)
    gl = -sum(t.pnl for t in losses)
    peak = np.maximum.accumulate(e)
    sd = float(np.std(r, ddof=1)) if r.size > 1 else 0.0
    return {
        "start": dates[idx[0]], "end": dates[idx[-1]], "sessions": int(r.size),
        "usd_per_session": round(float(r.mean()) * ACCOUNT, 2),
        "return": round(float(e[-1] / e[0] - 1.0), 4),
        "sharpe": round(float(r.mean() / sd * math.sqrt(252)), 2) if sd > 0 else 0.0,
        "max_drawdown": round(float(np.min(e / peak - 1.0)), 4),
        "usd_worst_day": round(float(r.min()) * ACCOUNT, 0), "usd_best_day": round(float(r.max()) * ACCOUNT, 0),
        "days_in_market": int(np.sum(np.abs(r) > 1e-12)),
        "trades": len(trades), "win_rate": round(len(wins) / len(trades), 3) if trades else 0.0,
        "profit_factor": round(gw / gl, 2) if gl > 1e-9 else (99.0 if gw > 0 else 0.0),
        "avg_win": round(float(np.mean([t.ret for t in wins])), 4) if wins else 0.0,
        "avg_loss": round(float(np.mean([t.ret for t in losses])), 4) if losses else 0.0,
        "avg_hold": round(float(np.mean([t.bars_held for t in trades])), 1) if trades else 0.0,
    }


def by_year(result) -> List[dict]:
    j = result.journal
    out = []
    years = sorted({d[:4] for d in j.equity_dates})
    for y in years:
        s = window_stats(result, f"{y}-01-01", f"{y}-12-31")
        if s:
            out.append({"year": y, "return": s["return"], "usd_per_session": s["usd_per_session"],
                        "trades": s["trades"], "win_rate": s["win_rate"]})
    return out


def backtest(genome: Genome, symbols: Sequence[str], slippage: float, start: str = "2012-01-03"):
    u, f = market(symbols)
    compiled = compile_genome(genome)
    s = max(_first_on_or_after(u.calendar, start), f.warmup_for(compiled.feature_names()))
    return run_backtest(compiled, u, f, starting_cash=ACCOUNT, commission_bps=0.0,
                        slippage_bps=slippage, record_thoughts=False, start_bar=s)


def buy_and_hold(symbols: Sequence[str], a: str, b: str) -> Dict[str, float]:
    u, _ = market(symbols)
    out = {}
    for s in symbols:
        bars = u.bars[s]
        idx = [i for i, d in enumerate(bars.dates) if a <= d <= b]
        if len(idx) > 5:
            c = np.asarray(bars.close, dtype=float)[max(idx[0] - 1, 0): idx[-1] + 1]
            out[s] = round(float(np.mean(c[1:] / c[:-1] - 1.0)) * ACCOUNT, 1)
    return out


def gauntlet(genome: Genome, symbols: Sequence[str]) -> dict:
    r = backtest(genome, symbols, SLIP)
    rs = backtest(genome, symbols, STRESS_SLIP)
    w = {k: window_stats(r, a, b) for k, (a, b) in WINDOWS.items()}
    stress = {k: window_stats(rs, *WINDOWS[k]) for k in ("train", "held_out")}
    real_syms = [REAL.get(s, s) for s in symbols]
    real = None
    if real_syms != list(symbols):
        try:
            rr = backtest(genome, real_syms, SLIP, start="2000-01-01")
            real = {"symbols": real_syms, "held_out": window_stats(rr, *WINDOWS["held_out"]),
                    "last_12m": window_stats(rr, *WINDOWS["last_12m"]),
                    "since": rr.start_date,
                    "life": window_stats(rr, rr.start_date, WINDOWS["held_out"][1])}
        except Exception as exc:  # noqa: BLE001 - a fund too young to trade the rules
            real = {"symbols": real_syms, "error": str(exc)[:120]}
    h, t = w.get("held_out") or {}, w.get("train") or {}
    sh, st = stress.get("held_out") or {}, stress.get("train") or {}
    profitable = bool(h and t and h["return"] > 0 and h["profit_factor"] > 1 and h["trades"] >= 3
                      and t["return"] > 0 and t["profit_factor"] > 1.1 and t["trades"] >= 30
                      and sh.get("return", -1) > 0 and st.get("return", -1) > 0)
    o = w.get("older") or {}
    real_h = (real or {}).get("held_out") or {}
    shown_usd = real_h.get("usd_per_session", h.get("usd_per_session", 0.0)) if real_h else h.get("usd_per_session", 0.0)
    verdict = {"profitable": profitable, "older_profitable": bool(o and o["return"] > 0),
               "held_out_usd": h.get("usd_per_session", 0.0), "real_held_out_usd": real_h.get("usd_per_session"),
               "shown": bool(profitable and h.get("usd_per_session", 0) >= SHOW_USD
                             and (not real_h or real_h.get("usd_per_session", 0) >= SHOW_USD)),
               "rank_usd": min(h.get("usd_per_session", 0.0), shown_usd)}
    return {"symbols": list(symbols), "windows": w, "stress": stress, "real": real, "verdict": verdict,
            "by_year": by_year(r),
            "buy_and_hold": {k: buy_and_hold(symbols, a, b) for k, (a, b) in WINDOWS.items()}}


def signature(genome: Genome, symbols: Sequence[str]) -> str:
    r = backtest(genome, symbols, SLIP)
    sig = "|".join(f"{t.symbol}:{t.entry_date}:{t.exit_date}" for t in r.journal.trades)
    return hashlib.sha1(sig.encode()).hexdigest()[:16]


def load_store() -> dict:
    return json.loads(STORE.read_text()) if STORE.exists() else {"strategies": {}}


def save_store(store: dict) -> None:
    """Merge ``store`` into the file under a lock: several harvests may run at once."""
    import fcntl
    lock = open(STORE.with_suffix(".lock"), "w")
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        disk = load_store()
        for sig, rec in store["strategies"].items():
            old = disk["strategies"].get(sig)
            if old is None or rule_len(rec["genome"]) <= rule_len(old["genome"]):
                disk["strategies"][sig] = rec
        tmp = STORE.with_suffix(f".{id(store)}.tmp")
        tmp.write_text(json.dumps(disk, indent=1))
        tmp.replace(STORE)
        store["strategies"] = disk["strategies"]
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def rule_len(g: dict) -> int:
    return sum(len(r["when"]) for r in g["entry_rules"] + g["exit_rules"])


def consider(store: dict, genome: Genome, symbols: Sequence[str], source: str) -> Optional[dict]:
    """Gauntlet one genome; keep it if profitable (the simpler of two identical traders)."""
    sig = signature(genome, symbols)
    old = store["strategies"].get(sig)
    if old and rule_len(old["genome"]) <= rule_len(genome.to_dict()):
        return None
    res = gauntlet(genome, symbols)
    if not res["verdict"]["profitable"]:
        return res
    store["strategies"][sig] = {"signature": sig, "source": source, "genome": genome.to_dict(), **res}
    return res


def harvest(runs: Sequence[str], top: int, db: str) -> int:
    from evotrader.store import Store
    s = Store(db)
    store = load_store()
    kept = shown = seen = 0
    for run_id in runs:
        cfg = s.run_config(run_id) or {}
        symbols = cfg.get("symbols", [])
        board = s.leaderboard(run_id, limit=top)
        for e in board:
            g = s.get_genome(e["genome_id"])
            if g is None:
                continue
            seen += 1
            try:
                res = consider(store, g, symbols, f"{run_id} gen {e.get('gen')}")
            except Exception as exc:  # noqa: BLE001 - one broken genome must not stop the harvest
                print(f"  skip {g.name}: {exc}", flush=True)
                continue
            if res and res["verdict"]["profitable"]:
                kept += 1
                shown += res["verdict"]["shown"]
                v = res["verdict"]
                print(f"  kept {g.name[:40]:40} {','.join(symbols)[:30]:30} held-out ${v['held_out_usd']:7.1f}"
                      f" real {v['real_held_out_usd']} {'SHOWN' if v['shown'] else ''}", flush=True)
        save_store(store)
    total = len(store["strategies"])
    n_shown = sum(1 for x in store["strategies"].values() if x["verdict"]["shown"])
    print(f"harvest: {seen} candidates, {kept} kept, {shown} at ${SHOW_USD:.0f}+; store {total}, "
          f"{n_shown} at ${SHOW_USD:.0f}+", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("harvest")
    h.add_argument("runs", nargs="+")
    h.add_argument("--top", type=int, default=20)
    h.add_argument("--db", default=str(ROOT / "runs" / "etf.sqlite"))
    f = sub.add_parser("file")
    f.add_argument("path")
    f.add_argument("--symbols", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "harvest":
        return harvest(args.runs, args.top, args.db)
    store = load_store()
    raw = json.loads(Path(args.path).read_text())
    for item in raw["genomes"] if isinstance(raw, dict) else raw:
        g = Genome.from_dict(item)
        res = consider(store, g, args.symbols.split(","), f"file {args.path}")
        if res:
            v = res["verdict"]
            print(f"{g.name[:40]:40} profitable {v['profitable']} held-out ${v['held_out_usd']} "
                  f"real {v['real_held_out_usd']} shown {v['shown']}", flush=True)
    save_store(store)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
