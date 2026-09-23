"""Pick the top 50 from the store and write profitable-strategies/leveraged-etfs/.

    python strategies/etf/publish_etf.py [--top 50] [--no-slim]

1. Candidates: every stored strategy marked "shown" (profitable and at least
   $80 a session over the held-out months; see gauntlet.py).
2. Ranked by the lower of its held-out dollars on the rebuilt series and on
   the real fund.  Left out: anything that lost money over 2012-2018 (the one
   window neither the breeding nor the $80 filter looked at), anything past a
   70% drawdown in any window; a
   strategy whose daily returns correlate above 0.9 with one already picked
   (a near-copy); more than six on the same funds.  So the list is fifty
   different traders, not fifty variants of one.
3. Each pick is simplified (every trade unchanged), re-run through the
   gauntlet, named from what it does, and written with a Pine script per fund.
4. Two special picks from all shown strategies: the most reliable at $150-200
   a session, and the lowest-risk at $100+ a session with a high win rate.
5. The full store, profitable strategies under $80 included, is copied to
   stored/ and not listed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategies" / "etf"))
from gauntlet import REAL, SHOW_USD, WINDOWS, backtest, gauntlet, load_store      # noqa: E402
from evotrader.genome import Genome                                          # noqa: E402
from evotrader.pine import compile_check, genome_to_pine                     # noqa: E402

OUT = ROOT / "profitable-strategies" / "leveraged-etfs"
FUND_LABEL = {"SOXL": "SOXL", "SOXS": "SOXS", "TQQQ": "TQQQ", "SQQQ": "SQQQ", "TECL": "TECL", "TECS": "TECS",
              "USD": "USD", "ROM": "ROM", "QLD": "QLD", "FTEC.2X": "FTEC 2x", "FTEC.3X": "FTEC 3x"}


def fund_name(sym: str) -> str:
    if sym in FUND_LABEL:
        return FUND_LABEL[sym]
    return REAL.get(sym, sym)


def family(g: dict) -> str:
    text = " ".join(r["when"] for r in g["entry_rules"])
    if "day_of_month" in text or "day_of_week" in text:
        return "Calendar"
    dip = re.search(r"ret1 < -|rsi7 <|rsi14 <|zscore20 < -|dist_sma20 < -|bb_pct <|close < bb_lower", text)
    trend = re.search(r"close > sma(50|200)|sma50 > sma200|pct_of_52w_high >|vol20 <", text)
    brk = re.search(r"bb_upper|ret1 > 0\.0[3-9]|ret5 > |ret20 > |macd", text)
    if dip and trend:
        return "Uptrend Dip"
    if dip:
        return "Dip Buyer"
    if brk and trend:
        return "Trend Breakout"
    if brk:
        return "Momentum"
    if trend:
        return "Trend Rider"
    return "Swing"


def daily_returns(item: dict) -> Dict[str, float]:
    r = backtest(Genome.from_dict(item["genome"]), item["symbols"], 8.0)
    d, e = r.journal.equity_dates, np.asarray(r.journal.equity, dtype=float)
    return {d[i]: e[i] / e[i - 1] - 1.0 for i in range(1, len(d)) if d[i] >= "2019-01-02"}


def corr(a: Dict[str, float], b: Dict[str, float]) -> float:
    keys = sorted(set(a) & set(b))
    x, y = np.array([a[k] for k in keys]), np.array([b[k] for k in keys])
    if x.std() == 0 or y.std() == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


MAX_DRAWDOWN = -0.70        # past this in any window a strategy is not something to trade
PER_UNIVERSE = 6            # at most this many picks on the same set of funds
MAX_CORR = 0.90


def survivable(v: dict) -> bool:
    return all((v["windows"].get(w) or {}).get("max_drawdown", 0) > MAX_DRAWDOWN
               for w in ("older", "train", "held_out"))


def pick(shown: List[dict], top: int) -> List[dict]:
    shown = sorted([v for v in shown if survivable(v) and v["verdict"]["older_profitable"]],
                   key=lambda v: -v["verdict"]["rank_usd"])
    picked, series, per = [], [], {}
    for item in shown:
        key = ",".join(item["symbols"])
        if per.get(key, 0) >= PER_UNIVERSE:
            continue
        s = daily_returns(item)
        if any(corr(s, t) > MAX_CORR for t in series):
            continue
        picked.append(item)
        series.append(s)
        per[key] = per.get(key, 0) + 1
        if len(picked) >= top:
            break
    return picked


def scaled(item: dict, f: float) -> dict:
    """The strategy at ``f`` of the account (the rest in cash): each window's
    dollars, drawdown and worst day, from its daily returns."""
    r = backtest(Genome.from_dict(item["genome"]), item["symbols"], 8.0)
    d, e = r.journal.equity_dates, np.asarray(r.journal.equity, dtype=float)
    ret = {d[i]: f * (e[i] / e[i - 1] - 1.0) for i in range(1, len(d))}
    out = {"fraction": round(f, 3)}
    for w, (a, b) in WINDOWS.items():
        x = np.array([v for k, v in ret.items() if a <= k <= b])
        if x.size < 5:
            continue
        eq = np.cumprod(1 + x)
        out[w] = {"usd_per_session": round(float(x.mean()) * 25_000, 1),
                  "max_drawdown": round(float(np.min(eq / np.maximum.accumulate(eq) - 1)), 4),
                  "usd_worst_day": round(float(x.min()) * 25_000, 0)}
    return out


def consistency(item: dict, f: float = 1.0, span: int = 63) -> dict:
    """Every rolling three-month stretch since 2019 at ``f`` of the account: the
    share that made money and the worst one's dollars a session."""
    r = backtest(Genome.from_dict(item["genome"]), item["symbols"], 8.0)
    d, e = r.journal.equity_dates, np.asarray(r.journal.equity, dtype=float)
    x = np.array([f * (e[i] / e[i - 1] - 1.0) for i in range(1, len(d)) if d[i] >= "2019-01-02"])
    if x.size <= span:
        return {}
    roll = np.convolve(x, np.ones(span), mode="valid") / span * 25_000
    return {"stretches": int(roll.size), "share_profitable": round(float((roll > 0).mean()), 3),
            "worst_usd_per_session": round(float(roll.min()), 1),
            "median_usd_per_session": round(float(np.median(roll)), 1)}


def reliable_150(shown: List[dict]):
    """$150-200: among strategies at $150+ over both the held-out months and
    the last 12 months, profitable on 2012-2018 and never past a 70% drawdown,
    the one whose weaker window is strongest."""
    ok = [v for v in shown if survivable(v) and v["verdict"]["older_profitable"]
          and v["windows"]["held_out"]["usd_per_session"] >= 150
          and (v["windows"].get("last_12m") or {}).get("usd_per_session", 0) >= 150]
    return max(ok, key=lambda v: (min(v["windows"]["held_out"]["usd_per_session"],
                                      v["windows"]["last_12m"]["usd_per_session"])
                                  + 2 * v["windows"]["train"]["usd_per_session"]), default=None)


def low_risk_100(shown: List[dict]):
    """$100 a session at the lowest risk: every shown strategy, sized so its
    held-out dollars are $100 (never above full size), win rate 60%+ in
    training and held-out; the smallest drawdown at that size wins."""
    best, best_dd = None, None
    for v in shown:
        w = v["windows"]
        if not survivable(v) or w["held_out"]["win_rate"] < 0.6 or w["train"]["win_rate"] < 0.6:
            continue
        f = min(1.0, 100.0 / w["held_out"]["usd_per_session"])
        dd = f * (abs(w["held_out"]["max_drawdown"]) + abs(w["train"]["max_drawdown"]))
        if best_dd is None or dd < best_dd:
            best, best_dd = v, dd
    return best


GLOSSARY = {
    "ret1": "the day's return", "ret5": "5-day return", "ret20": "20-day return", "ret60": "60-day return",
    "sma10": "10-day average", "sma20": "20-day average", "sma50": "50-day average",
    "sma200": "200-day average", "ema12": "12-day exponential average", "ema26": "26-day exponential average",
    "dist_sma20": "distance above the 20-day average (0.05 = 5%)",
    "dist_sma50": "distance above the 50-day average", "dist_sma200": "distance above the 200-day average",
    "sma20_slope": "5-day change of the 20-day average", "rsi7": "RSI, 7 days", "rsi14": "RSI, 14 days",
    "macd": "MACD line", "macd_signal": "MACD signal line", "macd_hist": "MACD histogram",
    "atr14": "14-day average true range", "atr_pct": "14-day average range as a share of price",
    "vol20": "20-day volatility, annualised (0.6 = 60%)", "vol60": "60-day volatility, annualised",
    "vol_ratio_20_60": "20-day over 60-day volatility", "bb_upper": "upper Bollinger band (20, 2)",
    "bb_lower": "lower Bollinger band", "bb_pct": "position inside the bands (0 = lower, 1 = upper)",
    "zscore20": "standard deviations from the 20-day mean", "pct_of_52w_high": "close / 52-week high",
    "pct_off_52w_low": "gain off the 52-week low", "volume_ratio": "volume / 20-day average volume",
    "mkt_ret20": "the first fund's 20-day return", "mkt_vol20": "the first fund's 20-day volatility",
    "mkt_above_sma200": "1 when the first fund is above its 200-day average",
    "day_of_month": "calendar day of the month", "day_of_week": "weekday (0 = Monday)",
    "bars_held": "sessions the trade has been held", "position_return": "the trade's return so far",
    "in_position": "1 when holding", "prev": "prev(x): x one session earlier",
    "cross_above": "cross_above(a, b): a closed above b today after closing at or below it yesterday",
}


def report_md(item: dict) -> str:
    g, w = item["genome"], item["windows"]
    words = sorted({k for k in GLOSSARY if any(re.search(rf"\b{k}\b", r["when"])
                                                for r in g["entry_rules"] + g["exit_rules"])})
    rk = g["risk"]
    lines = [f"# {item['rank']:02d}. {item['name']}", "",
             f"Funds: {', '.join(item['funds'])}. $25,000 cash account, the whole account in one position, "
             "fills at the next open, 8 bp slippage a side. Backtests, not advice.", "", "## Rules", ""]
    lines += [f"- **Buy** when `{r['when']}`" for r in g["entry_rules"]]
    lines += [f"- **Sell** when `{r['when']}`" for r in g["exit_rules"]]
    risk = [f"stop {rk['stop_loss_pct']:.1%} under entry (on a close)" if rk.get("stop_loss_pct") else "",
            f"target {rk['take_profit_pct']:.1%} (on a close)" if rk.get("take_profit_pct") else "",
            f"trailing stop {rk['trailing_stop_pct']:.1%} off the best close" if rk.get("trailing_stop_pct") else "",
            f"out after {rk['max_hold_bars']} sessions" if rk.get("max_hold_bars") else "",
            f"waits {rk['cooldown_bars']} sessions after an exit" if rk.get("cooldown_bars") else ""]
    lines += [f"- **Risk:** {', '.join(x for x in risk if x) or 'none beyond the sell rules'}", ""]
    if words:
        lines += ["Terms: " + "; ".join(f"`{k}` {GLOSSARY[k]}" for k in words) + ".", ""]
    lines += ["## Results", "", "| Window | $ a session | Return | Trades | Win rate | Avg win | Avg loss | "
              "Profit factor | Max drawdown | Worst day |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    names = {"held_out": "Last 6 months (never bred on)", "last_12m": "Last 12 months",
             "train": "2019 to Mar 2026 (bred on)", "older": "2012 to 2018"}
    for k in ("held_out", "last_12m", "train", "older"):
        x = w.get(k) or {}
        if x:
            lines.append(f"| {names[k]} | ${x['usd_per_session']:,.0f} | {x['return']:+.0%} | {x['trades']} | "
                         f"{x['win_rate']:.0%} | {x['avg_win']:+.1%} | {x['avg_loss']:+.1%} | {x['profit_factor']} | "
                         f"{x['max_drawdown']:.0%} | ${x['usd_worst_day']:,.0f} |")
    c = item.get("three_month_stretches") or {}
    if c:
        lines += ["", f"Every rolling three-month stretch since 2019 ({c['stretches']}): {c['share_profitable']:.0%} "
                  f"made money; the typical one made ${c['median_usd_per_session']:,.0f} a session and the worst "
                  f"${c['worst_usd_per_session']:,.0f}."]
    st = item.get("stress") or {}
    if st.get("held_out") and st.get("train"):
        lines += ["", f"At 3x slippage: ${st['held_out']['usd_per_session']:,.0f} a session over the last six "
                  f"months, ${st['train']['usd_per_session']:,.0f} over 2019 to March 2026."]
    real = item.get("real") or {}
    if real.get("held_out"):
        lines += ["", f"On the real fund{'s' if len(real['symbols']) > 1 else ''} ({', '.join(real['symbols'])}, "
                  f"traded since {real.get('since')}): ${real['held_out']['usd_per_session']:,.0f} a session over "
                  f"the last six months" + (f", ${real['life']['usd_per_session']:,.0f} over its whole life"
                                            if real.get("life") else "") + "."]
    bh = (item.get("buy_and_hold") or {}).get("held_out") or {}
    if bh:
        lines += ["", "Buying and holding over the last six months: " + ", ".join(
            f"{fund_name(k)} ${v:,.0f} a session" for k, v in bh.items()) + "."]
    by = item.get("by_year") or []
    if by:
        lines += ["", "## By year", "", "| Year | Return | $ a session | Trades | Win rate |",
                  "| --- | --- | --- | --- | --- |"]
        lines += [f"| {y['year']} | {y['return']:+.0%} | ${y['usd_per_session']:,.0f} | {y['trades']} | "
                  f"{y['win_rate']:.0%} |" for y in by]
    return "\n".join(lines) + "\n"


def write(item: dict, rank: int, folder: Path, tag: str = "") -> dict:
    g = item["genome"]
    funds = [fund_name(s) for s in item["symbols"]]
    name = f"{' / '.join(funds)} {family(g)}"
    item = {**item, "rank": rank, "name": name, "funds": funds, "tag": tag,
            "three_month_stretches": consistency(item)}
    item["genome"] = {**g, "name": name}
    stem = f"{rank:02d}_{re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')}"
    (folder / f"{stem}.json").write_text(json.dumps(item, indent=1))
    (folder / f"{stem}.md").write_text(report_md(item))
    for sym, fund in zip(item["symbols"], funds):
        chart = REAL.get(sym, sym if "." not in sym else "")
        if not chart:
            continue
        notes = []
        if len(funds) > 1:
            notes.append(f"Part of a {len(funds)}-fund strategy ({', '.join(funds)}): run the script on "
                         f"each fund's chart and hold one position at a time, the first signal wins.")
        src = genome_to_pine(Genome.from_dict(item["genome"]), fund=chart, extra_notes=notes,
                             source_note=f"Leveraged tech strategy {rank} of the grind (strategies/etf).")
        errs = compile_check(src)
        if errs:
            print(f"  pine for {stem} {chart} does not compile: {errs[:2]}", flush=True)
            continue
        suffix = "" if len(funds) == 1 else f"_{chart.lower()}"
        (folder / f"{stem}{suffix}.pine").write_text(src)
    return item


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=50)
    ap.add_argument("--no-slim", action="store_true")
    args = ap.parse_args(argv)
    store = load_store()["strategies"]
    shown = [v for v in store.values() if v["verdict"]["shown"]]
    print(f"store {len(store)} profitable, {len(shown)} at ${SHOW_USD:.0f}+", flush=True)
    picks = pick(shown, args.top)
    specials = {"reliable_150": reliable_150(shown), "low_risk_100": low_risk_100(shown)}
    if not args.no_slim:
        from simplify_etf import slim
        done = {}
        for item in picks + [v for v in specials.values() if v]:
            key = item["signature"]
            if key in done:
                continue
            thin = slim(item["genome"], item["symbols"])
            res = gauntlet(Genome.from_dict(thin), item["symbols"])
            if res["verdict"]["shown"]:
                item.update(res)
                item["genome"] = thin
            done[key] = True
            print(f"  slim {item['symbols']} {item['verdict']['rank_usd']:.1f}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stored").mkdir(exist_ok=True)
    for old in OUT.glob("[0-9][0-9]_*"):
        old.unlink()
    picks = sorted(picks, key=lambda v: -v["verdict"]["rank_usd"])
    written = [write(item, i, OUT) for i, item in enumerate(picks, 1)]
    special_out = {}
    for key, item in specials.items():
        if item is None:
            continue
        match = next((w for w in written if w["signature"] == item["signature"]), None)
        rank = match["rank"] if match else write(item, 90 + len(special_out), OUT, tag=key)["rank"]
        target = 175.0 if key == "reliable_150" else 100.0
        f = min(1.0, target / item["windows"]["held_out"]["usd_per_session"])
        special_out[key] = {"rank": rank, "sized": scaled(item, f), "three_month_stretches": consistency(item, f)}
    (OUT / "all.json").write_text(json.dumps({"windows": WINDOWS, "show_usd": SHOW_USD,
                                              "specials": special_out, "strategies": written}, indent=1))
    (OUT / "stored" / "all_profitable.json").write_text(json.dumps(
        {"note": "every strategy that passed the gauntlet, shown or not", "strategies": store}, indent=1))
    print(f"wrote {len(written)} strategies; specials {special_out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
