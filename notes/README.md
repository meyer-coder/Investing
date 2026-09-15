# notes

Findings from runs and experiments, one file per investigation:
`YYYY-MM-DD-<topic>.md`.

Every backtest, generation and run instance leaves notes on what it found.
Results from the CLI live in the sqlite store (`runs.note`, and each
generation's `analysis` / `lessons`); this directory is for ad-hoc experiments
and for the write-up that pulls a run's results together.

Each file covers:

- **Who and what** — who asked for it, and the question it was meant to answer.
- **Setup** — config, symbols, date range, commit the code was at.
- **Numbers** — the metrics that came out, in-sample and held-out.
- **Reading** — what the numbers mean, including what did *not* work.
- **Next** — what to try after this.

## Template

```markdown
# <topic>

- Date: YYYY-MM-DD
- Requested by: Charlie | Meyer
- Config: configs/<name>.json (population, generations, breeder)
- Data: <symbols>, <start>..<end>, held-out <frac>
- Code: <commit sha>

## Numbers

| | in-sample | held-out |
|---|---|---|
| return | | |
| buy & hold | | |
| sharpe | | |
| max drawdown | | |
| trades / win rate | | |

## Reading

What the run showed, and what it ruled out.

## Next

What this suggests trying.
```
