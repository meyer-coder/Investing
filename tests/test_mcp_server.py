import io
import json
import random

from evotrader.config import EvolutionConfig
from evotrader.fitness import Evaluation, Metrics
from evotrader.journal import Trade
from evotrader.mcp_server import MCPServer, TOOLS, TrainingView, serve
from evotrader.population import seed_population
from evotrader.store import Store


def _seeded_db(tmp_path, *, run_id="r1"):
    """A small but complete run: genomes, scores on both windows, trades, analysis."""
    path = str(tmp_path / "evotrader.sqlite")
    store = Store(path)
    cfg = EvolutionConfig(population=6, generations=4, offline=True,
                          symbols=["SPY", "QQQ"], budget_usd=5.0)
    store.create_run(run_id, cfg.to_dict(), "a test run")
    pop = seed_population(4, random.Random(0))
    store.save_genomes(run_id, pop)
    for gen in range(2):
        evals = []
        for i, g in enumerate(pop):
            evals.append(Evaluation(
                g.id, g.name, gen, 1.5 - i * 0.4 + gen * 0.1,
                Metrics(sharpe=1.2 - i * 0.2, trades=30, total_return=0.4,
                        benchmark_return=0.2),
                test_metrics=Metrics(sharpe=0.7, trades=12, total_return=0.1),
                test_score=0.9 - i * 0.3))
        store.save_evaluations(run_id, gen, evals)
        store.save_generation(run_id, gen, best_score=1.5 + gen * 0.1,
                              mean_score=0.5 + gen * 0.1, median_score=0.4,
                              best_genome_id=pop[0].id,
                              analysis="the dip buyers carried the generation",
                              lessons=["trend filters matter"], cost_usd=0.12,
                              elapsed_s=6.5)
    store.save_trades(run_id, 0, pop[0].id, [
        Trade("SPY", "2020-01-02", "2020-02-01", 100.0, 110.0, 5.0, 50.0, 0.10, 21,
              "rsi14 < 30", "rsi14 > 60"),
        Trade("QQQ", "2020-03-02", "2020-03-20", 200.0, 180.0, 3.0, -60.0, -0.10, 13,
              "rsi14 < 30", "position_return < -0.07"),
    ])
    store.close()
    return path, pop


def _server(tmp_path):
    path, pop = _seeded_db(tmp_path)
    return MCPServer(TrainingView(path)), pop


def _call(server, name, **arguments):
    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                              "params": {"name": name, "arguments": arguments}})
    return response["result"]


def _text(result):
    return "\n".join(c["text"] for c in result["content"])


# ------------------------------------------------------------------ protocol

def test_initialize_advertises_tools_and_resources(tmp_path):
    server, _ = _server(tmp_path)
    result = server.handle({"jsonrpc": "2.0", "id": 0, "method": "initialize",
                            "params": {"protocolVersion": "2025-06-18"}})["result"]
    assert result["protocolVersion"] == "2025-06-18"
    assert result["capabilities"]["tools"] == {"listChanged": False}
    assert "resources" in result["capabilities"]
    assert result["serverInfo"]["name"] == "evotrader-training-view"
    assert "held-out" in result["instructions"]


def test_initialize_falls_back_for_unknown_protocol(tmp_path):
    server, _ = _server(tmp_path)
    result = server.handle({"jsonrpc": "2.0", "id": 0, "method": "initialize",
                            "params": {"protocolVersion": "1999-01-01"}})["result"]
    assert result["protocolVersion"] == "2025-06-18"


def test_notifications_get_no_response(tmp_path):
    server, _ = _server(tmp_path)
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert server.initialized is True


def test_unknown_method_is_a_jsonrpc_error(tmp_path):
    server, _ = _server(tmp_path)
    response = server.handle({"jsonrpc": "2.0", "id": 3, "method": "nope"})
    assert response["error"]["code"] == -32601


def test_malformed_message_is_rejected(tmp_path):
    server, _ = _server(tmp_path)
    assert server.handle({"id": 4, "method": "ping"})["error"]["code"] == -32600
    assert server.handle({"jsonrpc": "2.0", "id": 5})["error"]["code"] == -32600


def test_ping_answers(tmp_path):
    server, _ = _server(tmp_path)
    assert server.handle({"jsonrpc": "2.0", "id": 6, "method": "ping"})["result"] == {}


def test_tools_list_is_well_formed(tmp_path):
    server, _ = _server(tmp_path)
    tools = server.handle({"jsonrpc": "2.0", "id": 7, "method": "tools/list"})["result"]["tools"]
    names = {t["name"] for t in tools}
    assert {"training_status", "leaderboard", "inspect_genome", "genome_trades",
            "overfitting_report", "generation_history"} <= names
    for spec in tools:
        assert spec["description"] and spec["inputSchema"]["type"] == "object"
        assert "db" in spec["inputSchema"]["properties"]
        for key in spec["inputSchema"].get("required", []):
            assert key in spec["inputSchema"]["properties"]


def test_unknown_tool_is_a_tool_error_not_a_protocol_error(tmp_path):
    server, _ = _server(tmp_path)
    result = _call(server, "does_not_exist")
    assert result["isError"] is True and "unknown tool" in _text(result)


def test_missing_required_argument_is_reported(tmp_path):
    server, _ = _server(tmp_path)
    result = _call(server, "inspect_genome")
    assert result["isError"] is True and "genome_id" in _text(result)


def test_serve_round_trips_over_a_stream(tmp_path):
    path, _ = _seeded_db(tmp_path)
    lines = [
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        "not json at all",
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": "training_status", "arguments": {}}}),
    ]
    out = io.StringIO()
    serve(MCPServer(TrainingView(path)), io.StringIO("\n".join(lines) + "\n"), out)
    responses = [json.loads(l) for l in out.getvalue().splitlines()]
    assert len(responses) == 3                       # the notification gets no reply
    assert responses[0]["result"]["serverInfo"]["name"] == "evotrader-training-view"
    assert responses[1]["error"]["code"] == -32700   # the bad line, and the server lived
    assert "run r1" in responses[2]["result"]["content"][0]["text"]


# --------------------------------------------------------------------- tools

def test_list_runs(tmp_path):
    server, _ = _server(tmp_path)
    result = _call(server, "list_runs")
    assert "r1" in _text(result)
    run = result["structuredContent"]["runs"][0]
    assert run["generations_done"] == 2 and run["population"] == 6
    assert abs(run["cost_usd"] - 0.24) < 1e-6


def test_training_status_reports_progress_and_champion(tmp_path):
    server, pop = _server(tmp_path)
    result = _call(server, "training_status")
    text = _text(result)
    s = result["structuredContent"]
    assert "run r1" in text and "champion" in text
    assert s["generations_done"] == 2 and s["generations_planned"] == 4
    assert s["budget_usd"] == 5.0 and abs(s["cost_usd"] - 0.24) < 1e-6
    assert s["champion"]["genome_id"] == pop[0].id
    assert s["champion"]["test_metrics"]["sharpe"] == 0.7
    assert s["latest_analysis"]["generation"] == 1
    assert s["stalled"] is False


def test_training_status_defaults_to_the_latest_run(tmp_path):
    server, _ = _server(tmp_path)
    assert _call(server, "training_status")["structuredContent"]["run_id"] == "r1"


def test_unknown_run_is_reported_with_the_known_ones(tmp_path):
    server, _ = _server(tmp_path)
    result = _call(server, "training_status", run_id="nope")
    assert result["isError"] is True
    assert "unknown run" in _text(result) and "r1" in _text(result)


def test_generation_history_pairs_train_and_holdout(tmp_path):
    server, _ = _server(tmp_path)
    rows = _call(server, "generation_history")["structuredContent"]["generations"]
    assert [r["generation"] for r in rows] == [0, 1]
    assert rows[0]["best_test_score"] == 0.9          # the champion's held-out score
    assert rows[1]["best_score"] > rows[0]["best_score"]


def test_generation_history_honours_limit(tmp_path):
    server, _ = _server(tmp_path)
    rows = _call(server, "generation_history", limit=1)["structuredContent"]["generations"]
    assert [r["generation"] for r in rows] == [1]


def test_leaderboard_ranks_on_the_requested_window(tmp_path):
    server, pop = _server(tmp_path)
    train = _call(server, "leaderboard")["structuredContent"]["rows"]
    assert train[0]["genome_id"] == pop[0].id
    assert train[0]["score"] >= train[-1]["score"]
    assert "in-sample" in _text(_call(server, "leaderboard"))
    holdout = _call(server, "leaderboard", rank_by="holdout")["structuredContent"]
    assert holdout["rank_by"] == "holdout"
    assert holdout["rows"][0]["test_score"] >= holdout["rows"][-1]["test_score"]


def test_leaderboard_rejects_an_unknown_window(tmp_path):
    server, _ = _server(tmp_path)
    result = _call(server, "leaderboard", rank_by="sideways")
    assert result["isError"] is True and "rank_by" in _text(result)


def test_inspect_genome_shows_rules_scores_and_ancestry(tmp_path):
    server, pop = _server(tmp_path)
    child = pop[0].copy(generation=2, parents=[pop[0].id], origin="llm")
    store = Store(str(tmp_path / "evotrader.sqlite"))
    store.save_genomes("r1", [child])
    store.close()
    result = _call(server, "inspect_genome", genome_id=child.id)
    s = result["structuredContent"]
    assert s["genome"]["id"] == child.id
    assert "BUY" in _text(result)
    assert [g["id"] for g in s["ancestry"]] == [child.id, pop[0].id]


def test_inspect_unknown_genome(tmp_path):
    server, _ = _server(tmp_path)
    result = _call(server, "inspect_genome", genome_id="deadbeef")
    assert result["isError"] is True and "unknown genome" in _text(result)


def test_genome_trades_orders_by_return(tmp_path):
    server, pop = _server(tmp_path)
    worst = _call(server, "genome_trades", genome_id=pop[0].id, order="worst")
    trades = worst["structuredContent"]["trades"]
    assert trades[0]["symbol"] == "QQQ" and trades[0]["ret"] < 0
    best = _call(server, "genome_trades", genome_id=pop[0].id, order="best")
    assert best["structuredContent"]["trades"][0]["symbol"] == "SPY"
    assert "rsi14 < 30" in _text(best)


def test_genome_trades_when_no_journal_was_kept(tmp_path):
    server, pop = _server(tmp_path)
    result = _call(server, "genome_trades", genome_id=pop[1].id)
    assert result["isError"] is False
    assert result["structuredContent"]["trades"] == []


def test_reflections_returns_analysis_and_lessons(tmp_path):
    server, _ = _server(tmp_path)
    result = _call(server, "reflections", limit=2)
    refs = result["structuredContent"]["reflections"]
    assert len(refs) == 2 and refs[0]["generation"] == 1
    assert refs[0]["lessons"] == ["trend filters matter"]
    assert "dip buyers" in _text(result)


def test_overfitting_report_compares_the_two_windows(tmp_path):
    server, _ = _server(tmp_path)
    s = _call(server, "overfitting_report")["structuredContent"]
    assert len(s["agents"]) == 4
    assert s["rank_correlation"] > 0.9        # this fixture ranks the same both ways
    assert abs(s["mean_gap"] - (s["agents"][0]["score"] - s["agents"][0]["test_score"])) < 0.5
    assert s["verdict"]


def test_overfitting_report_needs_holdout_scores(tmp_path):
    path = str(tmp_path / "bare.sqlite")
    store = Store(path)
    store.create_run("r2", EvolutionConfig().to_dict())
    pop = seed_population(2, random.Random(1))
    store.save_genomes("r2", pop)
    store.save_evaluations("r2", 0, [Evaluation(pop[0].id, pop[0].name, 0, 1.0, Metrics())])
    store.close()
    server = MCPServer(TrainingView(path))
    result = _call(server, "overfitting_report")
    assert result["isError"] is False
    assert result["structuredContent"]["rank_correlation"] is None


def test_search_genomes_finds_a_feature_in_the_rules(tmp_path):
    server, pop = _server(tmp_path)
    rule = pop[0].entry_rules[0].when
    term = rule.split()[0]
    s = _call(server, "search_genomes", query=term)["structuredContent"]
    assert any(m["genome_id"] == pop[0].id for m in s["matches"])
    assert any(term in r for m in s["matches"] for r in m["matching_rules"])


def test_search_genomes_reports_no_matches(tmp_path):
    server, _ = _server(tmp_path)
    s = _call(server, "search_genomes", query="zzz_not_a_feature")["structuredContent"]
    assert s["matches"] == []


def test_search_treats_wildcards_literally(tmp_path):
    server, _ = _server(tmp_path)
    s = _call(server, "search_genomes", query="%")["structuredContent"]
    assert s["matches"] == []


def test_strategy_language_lists_features_and_functions(tmp_path):
    server, _ = _server(tmp_path)
    result = _call(server, "strategy_language")
    s = result["structuredContent"]
    assert "rsi14" in s["market_features"] and "bars_held" in s["portfolio_features"]
    assert any(f.startswith("cross_above") for f in s["functions"])
    assert "RULE LANGUAGE" in _text(result)


def test_backtest_genome_replays_a_stored_agent(tmp_path):
    server, pop = _server(tmp_path)          # the fixture run is offline/synthetic
    result = _call(server, "backtest_genome", genome_id=pop[0].id,
                   start="2018-01-01", end="2021-12-31", trades=3)
    assert result["isError"] is False, _text(result)
    s = result["structuredContent"]
    assert s["genome_id"] == pop[0].id and "2018-01-01..2021-12-31" in s["window"]
    assert "total_return" in s["metrics"] and len(s["trades"]) <= 3
    assert "not a forecast" in _text(result)


# ----------------------------------------------------------------- resources

def test_resources_list_and_read(tmp_path):
    server, _ = _server(tmp_path)
    listed = server.handle({"jsonrpc": "2.0", "id": 8,
                            "method": "resources/list"})["result"]["resources"]
    uris = {r["uri"] for r in listed}
    assert "evotrader://strategy-language" in uris and "evotrader://run/r1" in uris
    report = server.handle({"jsonrpc": "2.0", "id": 9, "method": "resources/read",
                            "params": {"uri": "evotrader://run/r1"}})["result"]
    assert "# evotrader run `r1`" in report["contents"][0]["text"]
    lang = server.handle({"jsonrpc": "2.0", "id": 10, "method": "resources/read",
                          "params": {"uri": "evotrader://strategy-language"}})["result"]
    assert "RULE LANGUAGE" in lang["contents"][0]["text"]


def test_unknown_resource_is_an_error(tmp_path):
    server, _ = _server(tmp_path)
    response = server.handle({"jsonrpc": "2.0", "id": 11, "method": "resources/read",
                              "params": {"uri": "evotrader://nope"}})
    assert response["error"]["code"] == -32602


def test_resource_templates_are_listed(tmp_path):
    server, _ = _server(tmp_path)
    result = server.handle({"jsonrpc": "2.0", "id": 12,
                            "method": "resources/templates/list"})["result"]
    assert result["resourceTemplates"][0]["uriTemplate"] == "evotrader://run/{run_id}"


# ------------------------------------------------------------------- plumbing

def test_missing_database_is_explained(tmp_path):
    server = MCPServer(TrainingView(str(tmp_path / "absent.sqlite")))
    result = _call(server, "list_runs")
    assert result["isError"] is True and "no evotrader database" in _text(result)


def test_empty_database_is_not_an_error(tmp_path):
    path = str(tmp_path / "empty.sqlite")
    Store(path).close()
    server = MCPServer(TrainingView(path))
    assert "no runs" in _text(_call(server, "list_runs"))
    assert _call(server, "training_status")["isError"] is True


def test_db_argument_overrides_the_default(tmp_path):
    path, _ = _seeded_db(tmp_path)
    server = MCPServer(TrainingView(str(tmp_path / "absent.sqlite")))
    assert _call(server, "list_runs", db=path)["structuredContent"]["runs"][0]["run_id"] == "r1"


def test_every_tool_declares_its_required_arguments(tmp_path):
    for name, impl in TOOLS.items():
        assert impl.title and impl.description, name
        assert impl.spec()["annotations"]["readOnlyHint"] is True, name


def test_overfitting_verdict_separates_rank_from_level(tmp_path):
    """A ranking that holds up while every held-out score is negative is not evidence."""
    path = str(tmp_path / "neg.sqlite")
    store = Store(path)
    store.create_run("r3", EvolutionConfig().to_dict())
    pop = seed_population(4, random.Random(2))
    store.save_genomes("r3", pop)
    store.save_evaluations("r3", 0, [
        Evaluation(g.id, g.name, 0, 1.5 - i * 0.3, Metrics(sharpe=1.0, trades=20),
                   test_metrics=Metrics(sharpe=-0.5, trades=8),
                   test_score=-0.5 - i * 0.3)
        for i, g in enumerate(pop)])
    store.close()
    s = _call(MCPServer(TrainingView(path)), "overfitting_report")["structuredContent"]
    assert s["rank_correlation"] > 0.9 and s["median_test_score"] < 0
    assert "do not work" in s["verdict"]


def test_status_on_a_run_that_has_not_finished_a_generation(tmp_path):
    """A run is queryable the moment it is created, before any generation lands."""
    path = str(tmp_path / "fresh.sqlite")
    store = Store(path)
    store.create_run("r4", EvolutionConfig(population=20, generations=50).to_dict())
    store.close()
    server = MCPServer(TrainingView(path))
    status = _call(server, "training_status")
    assert status["isError"] is False
    s = status["structuredContent"]
    assert s["generations_done"] == 0 and s["champion"] is None
    assert s["best_score_latest"] is None
    assert _call(server, "generation_history")["structuredContent"]["generations"] == []
    assert _call(server, "leaderboard")["structuredContent"]["rows"] == []
    assert _call(server, "reflections")["structuredContent"]["reflections"] == []
