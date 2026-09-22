#!/usr/bin/env python3
"""Pull CME futures OHLCV from Databento and aggregate 1-minute bars to 5-minute.

Prints a cost estimate and makes you confirm before spending anything.

    pip install databento pandas
    export DATABENTO_API_KEY=db-...
    python scripts/fetch_databento.py --symbol NQ --start 2017-05-22 --end 2026-09-01

Why 1-minute and not 5-minute: aggregating yourself means you control the bar
boundaries and can verify them, rather than inheriting someone else's convention.

Why the default start is 2017-05-22: GLBX.MDP3 reaches back to 2010-06-06, but
Databento documents that OHLCV schemas return fewer bars than expected on many
days before 2017-05-21. Pass --start 2010-06-06 to go deeper, and check the
per-session bar counts this script reports before trusting that period.
"""
from __future__ import annotations

import argparse
import os
import sys

DATASET = "GLBX.MDP3"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--symbol", default="NQ",
                   help="root symbol: NQ, ES, CL, GC, ...")
    p.add_argument("--roll", default="v", choices=["v", "n", "c"],
                   help="continuous roll rule: v=volume, n=open interest, "
                        "c=calendar. Volume-based is usually right for "
                        "backtesting. Verify the suffix against Databento's "
                        "symbology docs if a request comes back empty.")
    p.add_argument("--start", default="2017-05-22")
    p.add_argument("--end", default=None, help="default: today")
    p.add_argument("--outdir", default="data/futures")
    p.add_argument("--yes", action="store_true",
                   help="skip the cost confirmation prompt")
    args = p.parse_args()

    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        print("error: set DATABENTO_API_KEY (get one at databento.com)", file=sys.stderr)
        return 1

    try:
        import databento as db
        import pandas as pd
    except ImportError as exc:
        print(f"error: {exc}. run: pip install databento pandas", file=sys.stderr)
        return 1

    contract = f"{args.symbol}.{args.roll}.0"
    end = args.end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    req = dict(dataset=DATASET, symbols=[contract], stype_in="continuous",
               schema="ohlcv-1m", start=args.start, end=end)

    client = db.Historical(key)

    # Cost estimation is free. Always look before you spend.
    cost = client.metadata.get_cost(**req)
    size = client.metadata.get_billable_size(**req)
    print(f"symbol   {contract}   ({args.start} -> {end})")
    print(f"size     {size / 1e6:.1f} MB")
    print(f"cost     ${cost:.4f}")
    print("note     new accounts get $125 of free credit, which covers this "
          "many times over — OHLCV is a tiny schema.")

    if not args.yes:
        if input("\nproceed with download? [y/N] ").strip().lower() != "y":
            print("aborted, nothing spent.")
            return 0

    print("\ndownloading...")
    df = client.timeseries.get_range(**req).to_df()
    if df.empty:
        print("error: no data returned. check the symbol and the --roll suffix.",
              file=sys.stderr)
        return 1

    df = df.sort_index()
    os.makedirs(args.outdir, exist_ok=True)
    base = f"{args.outdir}/{args.symbol}_{args.roll}"

    one_min = f"{base}_1m.parquet"
    df.to_parquet(one_min)
    print(f"wrote {one_min}  ({len(df):,} bars)")

    # 1m -> 5m. Left-closed, left-labelled: the 09:30 bar covers 09:30-09:34,
    # which is the convention that keeps a signal on a bar's close honest.
    bars = (df.resample("5min", closed="left", label="left")
              .agg(open=("open", "first"), high=("high", "max"),
                   low=("low", "min"), close=("close", "last"),
                   volume=("volume", "sum"))
              .dropna(subset=["open"]))
    five_min = f"{base}_5m.parquet"
    bars.to_parquet(five_min)
    bars.to_csv(f"{base}_5m.csv")
    print(f"wrote {five_min}  ({len(bars):,} bars)")

    # Coverage report — read this before trusting any of it.
    per_day = bars.groupby(bars.index.date).size()
    print(f"\ncoverage  {bars.index[0]} -> {bars.index[-1]}")
    print(f"sessions  {len(per_day):,}  ({len(per_day) / 252:.1f} years)")
    print(f"bars/session  median {per_day.median():.0f}, "
          f"min {per_day.min()}, max {per_day.max()}")
    thin = per_day[per_day < per_day.median() * 0.5]
    if len(thin):
        print(f"WARNING   {len(thin)} sessions have under half the median bar "
              f"count — inspect before including them:")
        print("          " + ", ".join(str(d) for d in thin.index[:8]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
