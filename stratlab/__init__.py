"""stratlab: build intraday strategies from a fixed card, test them honestly, log every one.

A strategy is a card (spec.py) with the same fields every time: signal family
and its settings, market, timeframe, session, direction, entry, stop, target,
trailing stop, partial exit, time stop, max trades a day and filters
(confluences).  The engine (engine.py) runs a card on 13 years of one-minute
Dukascopy data; evaluate.py scores it on three periods fixed in advance;
log.py records every card before it is tested, so the number of strategies
tried -- and how many would look good by luck -- is never lost.

    python -m stratlab batch research/lab/batches/01-screenshots.json
    python -m stratlab board
    python -m stratlab show L0001
"""
