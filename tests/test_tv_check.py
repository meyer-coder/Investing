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
    assert "credentials       none" in out
    assert "symbol search     ok (NASDAQ:AAPL" in out
    assert "bars              ok (120 x 1D" in out
    assert "evotrader tv-mcp" in out


def test_never_prints_the_cookie(feed, capsys, monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_SESSION", "super-secret-cookie")
    cli.main(["tv-check"])
    out = capsys.readouterr().out
    assert "super-secret-cookie" not in out
    assert "credentials       environment (19 chars)" in out


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


def test_reports_a_signed_in_account(feed, capsys, monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_SESSION", "cookie-value")
    monkeypatch.setattr(tvdata, "auth_token", lambda **k: ("tok", "session"))
    cli.main(["tv-check"])
    out = capsys.readouterr().out
    assert "account           signed in" in out
    assert "cookie-value" not in out


def test_reports_a_rejected_cookie_without_failing_the_bar_check(feed, capsys,
                                                                monkeypatch):
    monkeypatch.setenv("TRADINGVIEW_SESSION", "stale")
    def boom(**k):
        raise TradingViewError("cookie has expired")
    monkeypatch.setattr(tvdata, "auth_token", boom)
    assert cli.main(["tv-check"]) == 0
    out = capsys.readouterr().out
    assert "NOT SIGNED IN" in out and "anonymous data" in out


def test_tv_depth_tabulates_history(capsys, monkeypatch):
    monkeypatch.delenv("TRADINGVIEW_SESSION", raising=False)
    monkeypatch.setattr(tvdata, "fetch_bars",
                        lambda symbol, tf, bars, **k: synthetic_bars("AAPL", 500))
    assert cli.main(["tv-depth", "--timeframes", "60,1D"]) == 0
    out = capsys.readouterr().out
    assert "account anonymous" in out
    assert out.count("|") > 4 and "60 " in out and "1D " in out
    assert "an upgrade will not lift" in out


def test_tv_depth_keeps_going_when_one_timeframe_fails(capsys, monkeypatch):
    monkeypatch.delenv("TRADINGVIEW_SESSION", raising=False)

    def fetch(symbol, timeframe, bars, **k):
        if timeframe == "1":
            raise TradingViewError("no bars at this resolution")
        return synthetic_bars("AAPL", 500)

    monkeypatch.setattr(tvdata, "fetch_bars", fetch)
    assert cli.main(["tv-depth", "--timeframes", "1,1D"]) == 0
    out = capsys.readouterr().out
    assert "no bars at this resolution" in out and "1D" in out


def test_tv_login_verifies_before_storing(tmp_path, monkeypatch, capsys):
    """A cookie that does not work must not be written to disk."""
    path = tmp_path / "creds.json"
    monkeypatch.setattr(cli, "input", lambda *a: "", raising=False)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "bad-cookie")

    def reject(*a, **k):
        raise TradingViewError("cookie has expired")

    monkeypatch.setattr(tvdata, "resolve_auth_token", reject)
    assert cli.main(["tv-login", "--path", str(path)]) == 1
    assert not path.exists(), "a rejected cookie was stored anyway"


def test_tv_login_stores_a_working_cookie(tmp_path, monkeypatch, capsys):
    path = tmp_path / "creds.json"
    answers = iter(["good-cookie", "the-signature"])
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(answers))
    monkeypatch.setattr(tvdata, "resolve_auth_token", lambda *a, **k: "token")
    assert cli.main(["tv-login", "--path", str(path)]) == 0
    import json
    stored = json.loads(path.read_text())
    assert stored == {"sessionid": "good-cookie", "sessionid_sign": "the-signature"}
    out = capsys.readouterr().out
    assert "good-cookie" not in out, "the cookie was echoed to the terminal"


def test_tv_login_forget(tmp_path, monkeypatch, capsys):
    path = tmp_path / "creds.json"
    tvdata.save_credentials("secret", path=str(path))
    assert cli.main(["tv-login", "--forget", "--path", str(path)]) == 0
    assert not path.exists()
    assert "removed" in capsys.readouterr().out
