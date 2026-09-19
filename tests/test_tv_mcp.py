"""The backtesting MCP server.

Bars come from the offline synthetic source so the tests are deterministic and
never touch the network; the TradingView path itself is covered in
``test_tvdata.py`` against recorded frames.
"""
import random

from evotrader import tv_mcp
from evotrader.config import EvolutionConfig
from evotrader.population import seed_population
from evotrader.store import Store
from evotrader.tv_mcp import build_server

DIP = {"entry_rules": [{"when": "rsi14 < 35 and close > sma200", "weight": 0.3}],
       "exit_rules": [{"when": "rsi14 > 60"}, {"when": "position_return < -0.08"}]}
MOMENTUM = {"name": "Momentum", "entry_rules": [{"when": "ret20 > 0.05", "weight": 0.3}],
            "exit_rules": ["ret5 < -0.03", "bars_held > 40"]}


def _server():
    return build_server(source="synthetic")


def _call(server, tool_name, **arguments):
    return server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                          "params": {"name": tool_name,
                                     "arguments": arguments}})["result"]


def _text(result):
    return "\n".join(c["text"] for c in result["content"])


# ---------------------------------------------------------------- the surface

def test_tools_are_declared_properly():
    server = _server()
    specs = server.handle({"jsonrpc": "2.0", "id": 1,
                           "method": "tools/list"})["result"]["tools"]
    names = {s["name"] for s in specs}
    assert names == {"search_symbols", "get_bars", "backtest", "compare_strategies",
                     "walk_forward", "backtest_evolved_agent", "strategy_language",
                     "quote", "technicals", "screener"}
    for spec in specs:
        assert spec["description"] and spec["inputSchema"]["type"] == "object"
        for key in spec["inputSchema"].get("required", []):
            assert key in spec["inputSchema"]["properties"], (spec["name"], key)


def test_initialize_names_the_server():
    info = _server().handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                             "params": {}})["result"]
    assert info["serverInfo"]["name"] == "tradingview-backtest"
    assert "in-sample" in info["instructions"]


# -------------------------------------------------------------------- bars

def test_get_bars_returns_ohlcv_and_a_range():
    result = _call(_server(), "get_bars", symbol="AAPL", bars=300, show=3)
    s = result["structuredContent"]
    assert result["isError"] is False
    assert s["bars"] == 300 and s["timeframe"] == "1D" and s["source"] == "synthetic"
    assert len(s["last"]) == 3 and s["last"][-1]["high"] >= s["last"][-1]["low"]
    assert s["start"] < s["end"]
    assert "O " in _text(result)


def test_non_daily_timeframes_need_the_tradingview_source():
    result = _call(_server(), "get_bars", symbol="AAPL", timeframe="4h")
    assert result["isError"] is True
    assert "daily bars only" in _text(result)


def test_unknown_timeframe_is_rejected():
    result = _call(_server(), "get_bars", symbol="AAPL", timeframe="fortnightly")
    assert result["isError"] is True and "timeframe" in _text(result)


def test_search_symbols_passes_through_to_tradingview(monkeypatch):
    monkeypatch.setattr(tv_mcp.tvdata, "search_symbols", lambda *a, **k: [
        {"symbol": "NASDAQ:AAPL", "ticker": "AAPL", "exchange": "NASDAQ",
         "description": "Apple Inc.", "type": "stock", "currency": "USD"}])
    result = _call(_server(), "search_symbols", query="apple")
    assert result["structuredContent"]["matches"][0]["symbol"] == "NASDAQ:AAPL"
    assert "NASDAQ:AAPL" in _text(result)


def test_search_symbol_failures_are_reported_not_raised(monkeypatch):
    def boom(*a, **k):
        raise tv_mcp.tvdata.TradingViewError("symbol search failed: offline")
    monkeypatch.setattr(tv_mcp.tvdata, "search_symbols", boom)
    result = _call(_server(), "search_symbols", query="apple")
    assert result["isError"] is True and "offline" in _text(result)


# ---------------------------------------------------------------- backtesting

def test_backtest_reports_like_a_strategy_tester():
    result = _call(_server(), "backtest", symbols=["AAPL", "MSFT"], bars=1200,
                   name="RSI dip", **DIP)
    assert result["isError"] is False, _text(result)
    text = _text(result)
    s = result["structuredContent"]
    for label in ("net profit", "max drawdown", "profit factor", "trades",
                  "buy & hold", "sharpe"):
        assert label in text
    assert s["name"] == "RSI dip" and s["symbols"] == ["AAPL", "MSFT"]
    assert s["bars"] == 1200 and s["timeframe"] == "1D"
    m = s["metrics"]
    assert {"total_return", "max_drawdown", "profit_factor", "sharpe",
            "benchmark_return", "trades"} <= set(m)
    assert isinstance(s["trades"], list)
    assert "walk_forward" in text          # the window was chosen, and it says so


def test_backtest_trades_carry_the_rule_that_fired():
    s = _call(_server(), "backtest", symbols=["AAPL", "MSFT"], bars=1500,
              **DIP)["structuredContent"]
    assert s["metrics"]["trades"] == len(s["trades"])
    if s["trades"]:
        assert "rsi14" in s["trades"][0]["entry_reason"]
        assert s["rule_hits"]


def test_backtest_flags_a_thin_result():
    """A strategy that almost never fires should say so, not just show a number."""
    s = _call(_server(), "backtest", symbols=["AAPL"], bars=800,
              entry_rules=[{"when": "rsi14 < 5", "weight": 0.2}],
              exit_rules=["rsi14 > 95"])["structuredContent"]
    assert s["metrics"]["trades"] < 10
    assert any("too few" in c for c in s["caveats"])


def test_a_malformed_rule_explains_itself():
    result = _call(_server(), "backtest", symbols=["AAPL"],
                   entry_rules=["rsi14 <<< 30"], exit_rules=["rsi14 > 60"])
    assert result["isError"] is True
    assert "bad entry rule" in _text(result) and "strategy_language" in _text(result)


def test_an_unknown_feature_is_rejected():
    result = _call(_server(), "backtest", symbols=["AAPL"],
                   entry_rules=["twitter_sentiment > 0.5"], exit_rules=["rsi14 > 60"])
    assert result["isError"] is True and "twitter_sentiment" in _text(result)


def test_missing_rules_are_required_arguments():
    server = _server()
    assert _call(server, "backtest", symbols=["AAPL"],
                 exit_rules=["rsi14 > 60"])["isError"] is True
    result = _call(server, "backtest", symbols=["AAPL"], entry_rules=["rsi14 < 30"])
    assert result["isError"] is True and "exit_rules" in _text(result)


def test_symbols_are_required_and_bounded():
    server = _server()
    assert _call(server, "backtest", **DIP)["isError"] is True
    many = _call(server, "backtest", symbols=[f"S{i}" for i in range(25)], **DIP)
    assert many["isError"] is True and "at most 20" in _text(many)


def test_rules_may_be_plain_strings():
    result = _call(_server(), "backtest", symbols=["AAPL"], bars=600,
                   entry_rules=["rsi14 < 35"], exit_rules=["rsi14 > 60"])
    assert result["isError"] is False


def test_risk_limits_reach_the_engine():
    """A one-position cap must produce a strictly less exposed run."""
    server = _server()
    loose = _call(server, "backtest", symbols=["AAPL", "MSFT"], bars=1500,
                  risk={"max_positions": 5, "max_position_pct": 0.5},
                  **DIP)["structuredContent"]
    tight = _call(server, "backtest", symbols=["AAPL", "MSFT"], bars=1500,
                  risk={"max_positions": 1, "max_position_pct": 0.1},
                  **DIP)["structuredContent"]
    assert tight["strategy"]["risk"]["max_positions"] == 1
    assert tight["metrics"]["exposure"] <= loose["metrics"]["exposure"]


def test_costs_are_charged():
    """Raising commission and slippage can only lower the net result."""
    server = _server()
    free = _call(server, "backtest", symbols=["AAPL", "MSFT"], bars=1500,
                 commission_bps=0, slippage_bps=0, **DIP)["structuredContent"]
    dear = _call(server, "backtest", symbols=["AAPL", "MSFT"], bars=1500,
                 commission_bps=50, slippage_bps=50, **DIP)["structuredContent"]
    if free["metrics"]["trades"]:
        assert dear["metrics"]["total_return"] < free["metrics"]["total_return"]


# ----------------------------------------------------------------- comparison

def test_compare_strategies_ranks_on_identical_bars():
    result = _call(_server(), "compare_strategies", symbols=["AAPL", "MSFT"],
                   bars=1200, strategies=[dict(DIP, name="RSI dip"), MOMENTUM])
    s = result["structuredContent"]
    assert len(s["results"]) == 2
    returns = [r["metrics"]["total_return"] for r in s["results"]]
    assert returns == sorted(returns, reverse=True)
    assert all(r["metrics"]["benchmark_return"] == s["benchmark_return"]
               for r in s["results"])
    assert "buy & hold" in _text(result)


def test_compare_needs_at_least_two():
    result = _call(_server(), "compare_strategies", symbols=["AAPL"],
                   strategies=[dict(DIP, name="only one")])
    assert result["isError"] is True and "at least two" in _text(result)


def test_compare_fetches_the_bars_once(monkeypatch):
    """Ten strategies, one download — the comparison must be like-for-like."""
    server = _server()
    calls = []
    original = tv_mcp.marketdata.load_universe

    def counted(*args, **kwargs):
        calls.append(args[0])
        return original(*args, **kwargs)

    monkeypatch.setattr(tv_mcp.marketdata, "load_universe", counted)
    _call(server, "compare_strategies", symbols=["AAPL", "MSFT"], bars=900,
          strategies=[dict(DIP, name="a"), MOMENTUM, dict(DIP, name="c")])
    assert len(calls) == 1


# --------------------------------------------------------------- walk forward

def test_walk_forward_splits_in_and_out_of_sample():
    result = _call(_server(), "walk_forward", symbols=["AAPL", "MSFT"], bars=1500,
                   folds=3, name="RSI dip", **DIP)
    s = result["structuredContent"]
    assert result["isError"] is False, _text(result)
    assert 1 <= len(s["folds"]) <= 3
    assert s["folds_total"] == len(s["folds"])
    for fold in s["folds"]:
        assert fold["in_sample"]["end"] <= fold["out_of_sample"]["start"]
        assert fold["in_sample"]["start"] < fold["in_sample"]["end"]
    assert "out-of-sample" in _text(result)


def test_walk_forward_verdict_matches_the_folds():
    s = _call(_server(), "walk_forward", symbols=["AAPL", "MSFT"], bars=1500,
              folds=3, **DIP)["structuredContent"]
    assert 0 <= s["folds_positive"] <= s["folds_total"]


# ------------------------------------------------------- evolved agent bridge

def _training_db(tmp_path):
    path = str(tmp_path / "runs.sqlite")
    store = Store(path)
    store.create_run("r1", EvolutionConfig(offline=True).to_dict(), "")
    pop = seed_population(2, random.Random(0))
    store.save_genomes("r1", pop)
    store.close()
    return path, pop


def test_backtest_evolved_agent_on_new_symbols(tmp_path):
    path, pop = _training_db(tmp_path)
    server = build_server(source="synthetic", db_path=path)
    result = _call(server, "backtest_evolved_agent", genome_id=pop[0].id,
                   symbols=["AAPL", "MSFT"], bars=1200)
    assert result["isError"] is False, _text(result)
    s = result["structuredContent"]
    assert s["genome_id"] == pop[0].id and s["name"] == pop[0].name
    assert "metrics" in s and s["strategy"]["entry_rules"]
    assert "BUY" in _text(result)          # the agent's own rules are shown


def test_unknown_evolved_agent(tmp_path):
    path, _ = _training_db(tmp_path)
    server = build_server(source="synthetic", db_path=path)
    result = _call(server, "backtest_evolved_agent", genome_id="nope",
                   symbols=["AAPL"])
    assert result["isError"] is True and "unknown genome" in _text(result)


def test_missing_training_database_is_explained(tmp_path):
    server = build_server(source="synthetic", db_path=str(tmp_path / "absent.sqlite"))
    result = _call(server, "backtest_evolved_agent", genome_id="x", symbols=["AAPL"])
    assert result["isError"] is True and "no evotrader database" in _text(result)


# ------------------------------------------------------------------ reference

def test_strategy_language_is_available():
    result = _call(_server(), "strategy_language")
    s = result["structuredContent"]
    assert "rsi14" in s["market_features"] and "position_return" in s["portfolio_features"]
    assert "RULE LANGUAGE" in _text(result)


def test_resources_list_and_read():
    server = _server()
    listed = server.handle({"jsonrpc": "2.0", "id": 1,
                            "method": "resources/list"})["result"]["resources"]
    uris = {r["uri"] for r in listed}
    assert uris == {"evotrader://strategy-language", "tradingview://timeframes"}
    read = server.handle({"jsonrpc": "2.0", "id": 2, "method": "resources/read",
                          "params": {"uri": "tradingview://timeframes"}})["result"]
    assert "1D" in read["contents"][0]["text"]


def test_unknown_resource_is_an_error():
    response = _server().handle({"jsonrpc": "2.0", "id": 1, "method": "resources/read",
                                 "params": {"uri": "tradingview://nope"}})
    assert response["error"]["code"] == -32602


def test_each_walk_forward_window_gets_its_own_features():
    """Folds must not share a feature set; one window's indicators are not another's."""
    server = _server()
    view = server.context
    universe = view.universe(["AAPL", "MSFT"], "1D", 1200, "synthetic")
    early, late = universe.slice(0, 600), universe.slice(600, 1200)
    first, second = view.features(early), view.features(late)
    assert first is not second
    assert first.dates[0] != second.dates[0]
    assert view.features(early) is first          # and caching still works


# ------------------------------------------------------------ market scanning

def test_quote_reports_the_day(monkeypatch):
    monkeypatch.setattr(tv_mcp.tvdata, "quotes", lambda *a, **k: [
        {"symbol": "NASDAQ:AAPL", "name": "AAPL", "description": "Apple Inc.",
         "close": 336.13, "change": -0.2581, "volume": 86588048,
         "market_cap": 4905541689620}])
    result = _call(_server(), "quote", symbols=["NASDAQ:AAPL"])
    assert result["isError"] is False
    assert result["structuredContent"]["quotes"][0]["close"] == 336.13
    text = _text(result)
    assert "NASDAQ:AAPL" in text and "-0.26%" in text and "Apple" in text


def test_quote_needs_symbols():
    assert _call(_server(), "quote")["isError"] is True


def test_quote_failures_are_reported(monkeypatch):
    def boom(*a, **k):
        raise tv_mcp.tvdata.TradingViewError("the scanner refused the request")
    monkeypatch.setattr(tv_mcp.tvdata, "quotes", boom)
    result = _call(_server(), "quote", symbols=["NASDAQ:AAPL"])
    assert result["isError"] is True and "scanner refused" in _text(result)


def test_technicals_says_which_side_of_the_200(monkeypatch):
    monkeypatch.setattr(tv_mcp.tvdata, "technicals", lambda *a, **k: {
        "symbol": "NASDAQ:AAPL", "close": 336.13, "rsi": 64.25,
        "sma50": 320.14, "sma200": 286.34, "perf_ytd": 23.46})
    result = _call(_server(), "technicals", symbol="NASDAQ:AAPL")
    text = _text(result)
    assert "RSI(14)" in text and "64.25" in text
    assert "above" in text and "+17.4%" in text      # 336.13 / 286.34 - 1


def test_technicals_needs_a_symbol():
    assert _call(_server(), "technicals")["isError"] is True


def test_screener_passes_filters_through(monkeypatch):
    seen = {}

    def fake_screen(filters, **kwargs):
        seen["filters"] = filters
        seen["kwargs"] = kwargs
        return [{"symbol": "NYSE:BAC", "description": "Bank of America",
                 "close": 57.73, "change": -0.77, "rsi": 29.16}]

    monkeypatch.setattr(tv_mcp.tvdata, "screen", fake_screen)
    result = _call(_server(), "screener",
                   filters=[{"field": "rsi", "op": "less", "value": 35}],
                   limit=5, sort_by="close", ascending=True)
    assert seen["filters"] == [{"field": "rsi", "op": "less", "value": 35}]
    assert seen["kwargs"]["limit"] == 5
    assert seen["kwargs"]["sort_by"] == "close"
    assert seen["kwargs"]["descending"] is False
    assert seen["kwargs"]["common_stock_only"] is True
    text = _text(result)
    assert "NYSE:BAC" in text and "rsi" in text
    assert "candidates, not signals" in text


def test_screener_can_include_every_share_class(monkeypatch):
    seen = {}
    monkeypatch.setattr(tv_mcp.tvdata, "screen",
                        lambda filters, **k: (seen.update(k), [])[1])
    _call(_server(), "screener", filters=[{"field": "rsi", "op": "less", "value": 35}],
          include_all_share_classes=True)
    assert seen["common_stock_only"] is False


def test_screener_needs_filters():
    result = _call(_server(), "screener")
    assert result["isError"] is True


def test_screener_rejects_junk_filters():
    result = _call(_server(), "screener", filters=["rsi < 35"])
    assert result["isError"] is True and "object" in _text(result)
