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

    def start(token="", allow=(), which="tradingview"):
        routes = build_routes(which, source="synthetic")
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
    assert status == 200 and len(body["result"]["tools"]) == 7


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


def test_an_unsupported_protocol_version_is_rejected(endpoint):
    port = endpoint()
    status, _, body = call(port, body=INIT,
                           headers={"MCP-Protocol-Version": "1999-01-01"})
    assert status == 400 and "MCP-Protocol-Version" in body["error"]
    status, _, _ = call(port, body=INIT,
                        headers={"MCP-Protocol-Version": "2025-06-18"})
    assert status == 200


# ------------------------------------------------------------------ security

def test_a_token_is_required_when_one_is_set(endpoint):
    port = endpoint(token="secret-token")
    status, headers, _ = call(port, body=INIT)
    assert status == 401 and "Bearer" in headers["WWW-Authenticate"]
    status, _, body = call(port, body=INIT,
                           headers={"Authorization": "Bearer secret-token"})
    assert status == 200 and body["result"]["serverInfo"]


def test_the_wrong_token_is_refused(endpoint):
    port = endpoint(token="secret-token")
    status, _, _ = call(port, body=INIT,
                        headers={"Authorization": "Bearer wrong"})
    assert status == 401


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

    conn.request("POST", "/mcp", body=body, headers=headers)      # 401, body unread
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
