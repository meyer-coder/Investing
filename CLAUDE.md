# Notes for Claude

## Presenting data

Any page, report or dashboard that shows results follows
`docs/presentation-standard.md`. Start from the reference implementation,
`confluence/templates/explorer.html` (rendered by `confluence/explorer_html.py`):
one-screen layout, frozen header and ID columns, virtualised table, docked
inspector, keyboard navigation, column sets, the dark navy tokens, the number
formats, and the chart rules. Always show a baseline (random controls) next to
results.

## Projects

* `confluence/` — strategy factory, 8-year intraday backtester, macro-regime
  analysis and the explorer. `python -m confluence.cli run` rebuilds everything;
  `python -m confluence.cli explorer` rebuilds only the page from the last run.
* `evotrader/` — evolutionary daily-bar agents bred by Claude.

## Data gotchas already found

* histdata.com timestamps are New York time **with** DST (not fixed EST).
* histdata has no WTI for 2024 – May 2026, thin 2023 files, and its GRXEUR
  "DAX" is the Euro Stoxx 50 from 2020-06 to 2023-12. `data.build_feed`
  checks every month against Dukascopy and refills what fails.
* Dukascopy through the egress proxy is only fast with keep-alive sessions
  (~15 s per new TLS connection, ~0.2 s per reused one).
* FRED and the BLS API are not reachable here; CPI comes from the OECD series
  on DBnomics, macro prices from Yahoo, FOMC dates from federalreserve.gov.

## Tests

`python -m pytest tests -q`
