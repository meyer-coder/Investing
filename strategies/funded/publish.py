"""Write profitable-strategies/funded/: the FundedNext day-trade set.

    python strategies/funded/publish.py

top10/  the ten most profitable NQ strategies as same-day trades: the
        strategy, its daily-stop settings for MNQ and MES, its numbers before
        and after (reports/day_trades.json), its FundedNext odds by account
        size and contract count (reports/account_sizes.json), and a Pine v6
        strategy that is flat at every close (evotrader/pine.py).
bred/   the day-trade islands' agents that held up on history they never
        saw (strategies/funded/bred/picked.json), with the same files.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from evotrader.genome import Genome                                         # noqa: E402
from evotrader.pine import compile_check, genome_to_pine_day                # noqa: E402

OUT = ROOT / "profitable-strategies" / "funded"
REPORTS = OUT / "reports"
CHART = {"NQ1!": "MNQ1!", "ES1!": "MES1!", "YM1!": "MYM1!"}
SOURCE = ("Same-day version for FundedNext Futures, which allows no overnight holds. Tested on "
          "ratio back-adjusted daily bars with 0.2 bp commission and 1 bp slippage a side, then "
          "priced per contract ($0.75 a side plus a tick, two on stops). Past results; not advice.")


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def pick(rows, **want):
    for r in rows:
        if all(abs(r[k] - v) < 1e-9 if isinstance(v, float) else r[k] == v for k, v in want.items()):
            return r
    raise KeyError(want)


def write_pine(path: Path, genome: Genome, *, day_stop: float, chart: str, notes=()) -> None:
    src = genome_to_pine_day(genome, day_stop=day_stop, chart=chart, source_note=SOURCE,
                             extra_notes=notes)
    errors = compile_check(src)
    if errors:
        raise SystemExit(f"{path.name}: Pine does not compile: {errors}")
    path.write_text(src)


def top10() -> list:
    top = sorted(json.loads((ROOT / "profitable-strategies" / "nq-2x" / "all.json").read_text())["genomes"],
                 key=lambda g: g["rank"])[:10]
    dt = json.loads((REPORTS / "day_trades.json").read_text())["rows"]
    acct = json.loads((REPORTS / "account_sizes.json").read_text())["rows"]
    folder = OUT / "top10"
    folder.mkdir(parents=True, exist_ok=True)
    index = []
    for i, g in enumerate(top, 1):
        name = g["name"]
        pub = pick(dt, name=name, mode="published", micro="MNQ")
        mnq = pick(dt, name=name, mode="day", session="globex", micro="MNQ", day_stop=0.008, stop_style="caps")
        mes = pick(dt, name=name, mode="day", session="globex", micro="MES", day_stop=0.01, stop_style="caps")
        odds = {f"{r['contracts']} {r['micro']}": r["windows"] for r in acct if r["name"] == name}
        item = {
            "rank": i, "name": name, "original": f"profitable-strategies/nq-2x ({g['rank']:02d})",
            "how_it_trades": ("Same-day, Globex session: the position is bought at the 17:00 Chicago open "
                              "and sold at the close (tested at the 15:00 settlement; be flat by 15:10). "
                              "While the strategy's own rules still hold it, it is bought back at the next "
                              "open. A resting stop under each day's fill caps that day only."),
            "settings": {"signal": "NQ1! daily bars",
                         "MNQ": {"day_stop": 0.008, "day_stop_usd": mnq["day_stop_usd"]},
                         "MES": {"day_stop": 0.01, "day_stop_usd": mes["day_stop_usd"],
                                 "note": "same NQ signal, filled on MES"}},
            "results": {"published_multi_day_1_mnq": pub["windows"], "same_day_1_mnq": mnq["windows"],
                        "same_day_1_mes": mes["windows"]},
            "fundednext_odds": odds,
            "genome": {k: v for k, v in g.items() if k not in ("rank", "family")},
        }
        base = folder / f"{i:02d}_{slug(name)}"
        base.with_suffix(".json").write_text(json.dumps(item, indent=1))
        write_pine(base.with_suffix(".pine"), Genome.from_dict(g), day_stop=0.008, chart="MNQ1!",
                   notes=["For MES instead: take the same signals from this NQ chart and buy one MES "
                          "with a 1% daily stop under its fill."])
        index.append(item)
        print(f"top10 {i:02d} {name}", flush=True)
    return index


def bred() -> list:
    src = HERE / "bred" / "picked.json"
    if not src.exists():
        return []
    folder = OUT / "bred"
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for i, item in enumerate(json.loads(src.read_text())["strategies"], 1):
        g = Genome.from_dict(item["genome"])
        base = folder / f"{i:02d}_{slug(item['name'])}"
        base.with_suffix(".json").write_text(json.dumps(item, indent=1))
        write_pine(base.with_suffix(".pine"), g, day_stop=item["settings"]["day_stop"],
                   chart=CHART[item["settings"]["symbol"]])
        out.append(item)
        print(f"bred {i:02d} {item['name']}", flush=True)
    return out


def main() -> int:
    t = top10()
    b = bred()
    (OUT / "all.json").write_text(json.dumps({"top10": t, "bred": b}, indent=1))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
