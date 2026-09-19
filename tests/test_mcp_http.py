"""The Streamable HTTP transport — what a Claude custom connector talks to."""
import json
import threading
from http.client import HTTPConnection

import pytest

from evotrader.mcp_http import build_routes, serve_http


@pytest.fixture
def endpoint():
    """A running server on a loopback port, torn down after the test."""
    servers = {}

    def start(token="", allow=(), which="tradingview", db_path=""):
        routes = build_routes(which, source="synthetic", db_path=db_path)
        httpd = serve_http(routes, host="127.0.0.1", port=0, token=token,
                           allowed_origins=allow)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        servers["httpd"] = httpd
        return httpd.server_address[1]

    yield start
    if "httpd" in servers:
        servers["httpd"].shutdown()
        servers["httpd"].server_close()


def call(port, method="POST", path="/mcp", body=None, headers=None):
    conn = HTTPConnection("127.0.0.1", port, timeout=30)
    payload = json.dumps(body) if isinstance(body, (dict, list)) else body
    all_headers = {"Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
    all_headers.update(headers or {})
    conn.request(method, path, body=payload, headers=all_headers)
    response = conn.getresponse()
    raw = response.read()
    conn.close()
    parsed = json.loads(raw) if raw else None
    return response.status, dict(response.getheaders()), parsed


INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18"}}


# ------------------------------------------------------------------ protocol

def test_initialize_returns_json_and_a_session_id(endpoint):
    port = endpoint()
    status, headers, body = call(port, body=INIT)
    assert status == 200
    assert headers["Content-Type"] == "application/json"
    assert body["result"]["serverInfo"]["name"] == "tradingview-backtest"
    assert len(headers["Mcp-Session-Id"]) >= 16


def test_a_notification_is_accepted_with_no_body(endpoint):
    port = endpoint()
    status, _, body = call(port, body={"jsonrpc": "2.0",
                                       "method": "notifications/initialized"})
    assert status == 202 and body is None


def test_a_tool_call_round_trips(endpoint):
    port = endpoint()
    call(port, body=INIT)
    status, _, body = call(port, body={
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "backtest", "arguments": {
            "symbols": ["AAPL"], "bars": 600, "source": "synthetic",
            "entry_rules": ["rsi14 < 35"], "exit_rules": ["rsi14 > 60"]}}})
    assert status == 200
    assert body["result"]["isError"] is False
    assert "net profit" in body["result"]["content"][0]["text"]


def test_tools_are_listed(endpoint):
    port = endpoint()
    status, _, body = call(port, body={"jsonrpc": "2.0", "id": 3,
                                       "method": "tools/list"})
    assert status == 200 and len(body["result"]["tools"]) == 10


def test_malformed_json_is_a_parse_error(endpoint):
    port = endpoint()
    status, _, body = call(port, body="{not json")
    assert status == 400 and body["error"]["code"] == -32700


def test_a_batch_is_refused(endpoint):
    """Batching was removed from the protocol in 2025-06-18."""
    port = endpoint()
    status, _, body = call(port, body=[INIT, INIT])
    assert status == 400 and body["error"]["code"] == -32600


def test_get_reports_no_stream(endpoint):
    port = endpoint()
    status, headers, _ = call(port, method="GET")
    assert status == 405 and "POST" in headers["Allow"]


def test_delete_ends_a_session(endpoint):
    port = endpoint()
    status, _, _ = call(port, method="DELETE")
    assert status == 204


def test_an_unknown_path_is_404(endpoint):
    port = endpoint()
    status, _, body = call(port, path="/nope", body=INIT)
    assert status == 404 and "no MCP endpoint" in body["error"]


def test_health_needs_no_credentials(endpoint):
    port = endpoint(token="secret")
    status, _, body = call(port, method="GET", path="/health")
    assert status == 200 and body["status"] == "ok"


def test_a_newer_protocol_version_is_still_served(endpoint):
    """A client one revision ahead must not have every request 400'd."""
    port = endpoint()
    for version in ("2025-06-18", "2025-11-25", "2026-06-18"):
        status, _, body = call(port, body=INIT,
                               headers={"MCP-Protocol-Version": version})
        assert status == 200, version
        # initialize negotiates down to what this server actually speaks
        assert body["result"]["protocolVersion"] in (version, "2025-06-18")


# ------------------------------------------------------------------ security

def test_a_token_is_required_when_one_is_set(endpoint):
    """403, never 401: a 401 sends the client hunting for an OAuth server."""
    port = endpoint(token="secret-token")
    status, headers, body = call(port, body=INIT)
    assert status == 403, "401 makes Claude start an OAuth flow that does not exist"
    assert "WWW-Authenticate" not in headers
    assert "Bearer" in body["error"]
    status, _, body = call(port, body=INIT,
                           headers={"Authorization": "Bearer secret-token"})
    assert status == 200 and body["result"]["serverInfo"]


def test_the_wrong_token_is_refused(endpoint):
    port = endpoint(token="secret-token")
    status, _, _ = call(port, body=INIT,
                        headers={"Authorization": "Bearer wrong"})
    assert status == 403


def test_a_browser_origin_is_refused_by_default(endpoint):
    """DNS rebinding: a local server is otherwise reachable from any web page."""
    port = endpoint()
    status, _, body = call(port, body=INIT,
                           headers={"Origin": "https://evil.example"})
    assert status == 403 and "origin" in body["error"]


def test_an_allowed_origin_passes(endpoint):
    port = endpoint(allow=("https://claude.ai",))
    status, _, _ = call(port, body=INIT,
                        headers={"Origin": "https://claude.ai"})
    assert status == 200


def test_an_oversized_body_is_refused(endpoint):
    port = endpoint()
    conn = HTTPConnection("127.0.0.1", port, timeout=30)
    conn.request("POST", "/mcp", body=b"", headers={
        "Content-Type": "application/json",
        "Content-Length": str(50 * 1024 * 1024)})
    assert conn.getresponse().status == 413
    conn.close()


# -------------------------------------------------------------------- routing

def test_both_servers_can_share_one_process(endpoint):
    port = endpoint(which="both")
    status, _, body = call(port, path="/mcp/tradingview", body=INIT)
    assert status == 200 and body["result"]["serverInfo"]["name"] == "tradingview-backtest"
    status, _, body = call(port, path="/mcp/training", body=INIT)
    assert status == 200
    assert body["result"]["serverInfo"]["name"] == "evotrader-training-view"


def test_routes_reject_an_unknown_server_name():
    with pytest.raises(ValueError):
        build_routes("nonsense")


def test_a_reused_connection_survives_a_refused_request(endpoint):
    """Clients reuse connections; an undrained body desyncs every later request."""
    port = endpoint(token="secret-token")
    conn = HTTPConnection("127.0.0.1", port, timeout=30)
    body = json.dumps(INIT)
    headers = {"Content-Type": "application/json"}

    conn.request("POST", "/mcp", body=body, headers=headers)      # 403, body unread
    assert conn.getresponse().read() is not None

    conn.request("POST", "/mcp", body=body,                        # same connection
                 headers={**headers, "Authorization": "Bearer secret-token"})
    second = conn.getresponse()
    assert second.status == 200
    assert json.loads(second.read())["result"]["serverInfo"]
    conn.close()


def test_a_reused_connection_survives_a_404(endpoint):
    port = endpoint()
    conn = HTTPConnection("127.0.0.1", port, timeout=30)
    body = json.dumps(INIT)
    headers = {"Content-Type": "application/json"}
    conn.request("POST", "/nope", body=body, headers=headers)
    assert conn.getresponse().read() is not None
    conn.request("POST", "/mcp", body=body, headers=headers)
    assert conn.getresponse().status == 200
    conn.close()


# ------------------------------------------- what a connector's checker sends

def test_options_is_answered_not_501(endpoint):
    """http.server's default 501 makes a reachable server look broken."""
    port = endpoint()
    status, headers, _ = call(port, method="OPTIONS")
    assert status == 204
    assert "POST" in headers["Access-Control-Allow-Methods"]


def test_head_is_answered(endpoint):
    port = endpoint()
    status, _, _ = call(port, method="HEAD")
    assert status == 200


def test_an_empty_post_is_a_reachability_probe(endpoint):
    port = endpoint()
    status, _, body = call(port, body="")
    assert status == 200 and body["status"] == "ok"


def test_oauth_discovery_is_a_plain_404(endpoint):
    port = endpoint()
    status, _, body = call(port, method="GET",
                           path="/.well-known/oauth-authorization-server")
    assert status == 404 and body is None


def test_a_chunked_body_is_read(endpoint):
    """Without chunked support the message is lost and the reply says 'ok'."""
    import socket as _socket

    port = endpoint()
    body = json.dumps(INIT).encode()
    request = (b"POST /mcp HTTP/1.1\r\nHost: 127.0.0.1\r\n"
               b"Content-Type: application/json\r\n"
               b"Transfer-Encoding: chunked\r\n\r\n"
               + f"{len(body):x}".encode() + b"\r\n" + body + b"\r\n0\r\n\r\n")
    sock = _socket.create_connection(("127.0.0.1", port), timeout=30)
    sock.sendall(request)
    raw = b""
    while b"\r\n\r\n" not in raw or len(raw.split(b"\r\n\r\n", 1)[1]) < 10:
        part = sock.recv(65536)
        if not part:
            break
        raw += part
    sock.close()
    head, _, payload = raw.partition(b"\r\n\r\n")
    assert b"200" in head.split(b"\r\n")[0]
    parsed = json.loads(payload.decode())
    assert parsed["result"]["serverInfo"]["name"] == "tradingview-backtest", \
        "the chunked body was dropped and answered as a probe"


def test_concurrent_calls_all_succeed(endpoint, tmp_path):
    """http.server gives each request its own thread; SQLite and the caches
    behind these tools were written for one."""
    from evotrader.config import EvolutionConfig
    from evotrader.store import Store

    db = str(tmp_path / "runs.sqlite")
    store = Store(db)
    store.create_run("r1", EvolutionConfig(population=4).to_dict(), "concurrent")
    store.close()

    port = endpoint(which="training", db_path=db)
    results = []

    def hit():
        try:
            results.append(call(port, body={
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "list_runs", "arguments": {}}}))
        except Exception as exc:  # noqa: BLE001 - recorded, asserted below
            results.append(("raised", exc))

    threads = [threading.Thread(target=hit) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert len(results) == 6
    for result in results:
        assert result[0] != "raised", f"request failed: {result[1]}"
        status, _, body = result
        assert status == 200
        assert body["result"]["isError"] is False, body["result"]["content"][0]["text"]
        # The real run comes back, so the SQLite connection was genuinely used
        # from each of these threads.
        assert "r1" in body["result"]["content"][0]["text"]
