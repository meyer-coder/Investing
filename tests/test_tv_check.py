"""`evotrader tv-check`: does the TradingView feed work from this machine?"""
import pytest

from evotrader import cli, tvdata
from evotrader.data import synthetic_bars
from evotrader.tvdata import TradingViewError


@pytest.fixture
def feed(monkeypatch):
    monkeypatch.setattr(tvdata, "search_symbols", lambda *a, **k: [
        {"symbol": "NASDAQ:AAPL"}, {"symbol": "NASDAQ:AAPL.P"}])
    bars = synthetic_bars("AAPL", 120)
    bars.symbol = "NASDAQ:AAPL"
    monkeypatch.setattr(tvdata, "fetch_bars", lambda *a, **k: bars)
    return bars


def test_reports_a_working_feed(feed, capsys, monkeypatch):
    monkeypatch.delenv("TRADINGVIEW_SESSION", raising=False)
    assert cli.main(["tv-check"]) == 0
    out = capsys.readouterr().out
    assert "session cookie    not set" in out
    assert "symbol search     ok (NASDAQ:AAPL" in out
    assert "bars              ok (120 x 1D" in out
    assert "evotrader tv-mcp" in out


def test_never_prints_the_cookie(feed, capsys, monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_SESSION", "super-secret-cookie")
    cli.main(["tv-check"])
    out = capsys.readouterr().out
    assert "super-secret-cookie" not in out
    assert "set (19 chars)" in out


def test_stale_data_is_called_out(feed, capsys, monkeypatch):
    monkeypatch.delenv("TRADINGVIEW_SESSION", raising=False)
    cli.main(["tv-check"])                 # synthetic bars end years in the past
    assert "days old" in capsys.readouterr().out


def test_a_failed_fetch_exits_nonzero_with_hints(capsys, monkeypatch):
    monkeypatch.setattr(tvdata, "search_symbols", lambda *a, **k: [])
    def boom(*a, **k):
        raise TradingViewError("returned no bars for 'NASDAQ:NOPE'")
    monkeypatch.setattr(tvdata, "fetch_bars", boom)
    assert cli.main(["tv-check", "--symbol", "NASDAQ:NOPE"]) == 1
    out = capsys.readouterr().out
    assert "bars              FAILED" in out and "exchange prefix" in out


def test_search_failure_does_not_stop_the_bar_check(feed, capsys, monkeypatch):
    def boom(*a, **k):
        raise TradingViewError("symbol search failed: 403")
    monkeypatch.setattr(tvdata, "search_symbols", boom)
    assert cli.main(["tv-check"]) == 0
    out = capsys.readouterr().out
    assert "symbol search     FAILED" in out and "bars              ok" in out
