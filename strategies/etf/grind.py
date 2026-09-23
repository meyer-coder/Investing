"""Keep four islands running until a deadline, harvesting each as it finishes.

    python strategies/etf/grind.py --until 2026-09-23T09:40:00Z [--slots 4]

Plan: every universe in PRIORITY with each fitness, in order; once a pass is
done, the next pass seeds each universe's islands with its best stored
strategies (ranked on the training window only, so the held-out months stay
unseen by breeding) and new random seeds.  Each finished run goes through the
gauntlet (strategies/etf/gauntlet.py harvest) into strategies/etf/store.json.
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "etf"))
from islands import UNIVERSES, config                                      # noqa: E402

PRIORITY = ["soxl_long", "soxl", "memory", "semis", "nvda", "amd", "tsm", "avgo", "index3x", "tecl_long",
            "tqqq_long", "usd", "gpu", "ai", "ftec3", "rom", "mu", "tecl", "tqqq", "smci", "megacap",
            "googl", "meta", "msft", "amzn", "aapl", "tsla", "orcl", "qld", "ftec2", "nvda_ls", "index3x_ls"]
FITNESSES = ["dollars", "trend", "steady"]
LOGS = ROOT / "runs" / "logs" / "etf"


def now() -> float:
    return time.time()


def seed_file_for(universe: str, n: int = 12) -> str:
    store = ROOT / "strategies" / "etf" / "store.json"
    if not store.exists():
        return ""
    items = [v for v in json.loads(store.read_text())["strategies"].values()
             if v["symbols"] == UNIVERSES[universe]]
    if len(items) < 3:
        return ""
    items.sort(key=lambda v: -(v["windows"].get("train") or {}).get("usd_per_session", 0))
    path = ROOT / "strategies" / "etf" / "seeds" / f"{universe}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"genomes": [v["genome"] for v in items[:n]]}, indent=1))
    return str(path.relative_to(ROOT))


def plan(universes, fitnesses, seed):
    for p in itertools.count():
        for universe in universes:
            for fitness in fitnesses:
                seed += 1
                yield p, universe, fitness, seed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--until", required=True)
    ap.add_argument("--slots", type=int, default=4)
    ap.add_argument("--generations", type=int, default=30)
    ap.add_argument("--prefix", default="p")
    ap.add_argument("--seed-base", type=int, default=2000)
    ap.add_argument("--universes", default=",".join(PRIORITY))
    ap.add_argument("--fitnesses", default=",".join(FITNESSES))
    args = ap.parse_args(argv)
    deadline = datetime.strptime(args.until, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    LOGS.mkdir(parents=True, exist_ok=True)
    running = {}
    todo = plan(args.universes.split(","), args.fitnesses.split(","), args.seed_base)
    done = 0
    while True:
        # reap
        for proc, (name, log, db) in list(running.items()):
            if proc.poll() is None:
                continue
            del running[proc]
            m = re.search(r"run-\d{8}-\d{6}-[0-9a-f]{4}", log.read_text(errors="ignore"))
            if m:
                h = subprocess.run([sys.executable, str(ROOT / "strategies" / "etf" / "gauntlet.py"),
                                    "harvest", m.group(0), "--top", "20", "--db", db],
                                   cwd=ROOT, capture_output=True, text=True)
                tail = (h.stdout.strip().splitlines() or ["(no output)"])[-1]
                print(f"{datetime.now(timezone.utc):%H:%M} done {name} {m.group(0)}: {tail}", flush=True)
                if h.returncode:
                    print(h.stderr[-800:], flush=True)
            else:
                print(f"{datetime.now(timezone.utc):%H:%M} done {name}: no run id (see {log})", flush=True)
            done += 1
        # launch
        while len(running) < args.slots and now() < deadline:
            p, universe, fitness, seed = next(todo)
            name = f"{args.prefix}{p}_{universe}_{fitness}_{seed}"
            cfg = config(name, universe, fitness, seed, generations=args.generations,
                         seed_file=seed_file_for(universe) if p > 0 else "")
            cfg["db_path"] = f"runs/etf/{name}.sqlite"      # one database per island: no lock waits
            path = ROOT / "configs" / "etf" / f"{name}.json"
            path.write_text(json.dumps(cfg, indent=1))
            log = LOGS / f"{name}.log"
            proc = subprocess.Popen([sys.executable, "-m", "evotrader.cli", "run", "--config", str(path)],
                                    cwd=ROOT, stdout=open(log, "w"), stderr=subprocess.STDOUT)
            running[proc] = (name, log, cfg["db_path"])
            print(f"{datetime.now(timezone.utc):%H:%M} start {name}", flush=True)
        if not running and now() >= deadline:
            break
        time.sleep(5)
    print(f"grind over: {done} islands", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
