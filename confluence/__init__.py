"""confluence: a strategy factory and 8-year intraday backtester for
confluence-based trading on index futures, CFDs, metals, oil and FX.

    python -m confluence.cli fetch      # pull 1-minute history (histdata, Dukascopy, Yahoo, massive.com)
    python -m confluence.cli run        # generate every strategy, backtest, log, build the explorer
    python -m confluence.cli explorer   # rebuild results/explorer.html from the last run

Everything is measured in R (multiples of the risk taken on the trade), so a
strategy on MNQ and one on EURUSD are directly comparable.
"""

__version__ = "0.1.0"
