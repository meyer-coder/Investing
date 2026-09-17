"""Streamable HTTP transport, so the servers can be a Claude custom connector.

The stdio servers only work where a client can launch a subprocess — a terminal,
or Claude Code in this repo.  A Claude *custom connector* is a remote MCP server
instead: Claude's cloud reaches it over the public internet, which means HTTPS
and the Streamable HTTP transport rather than stdin and stdout.

    evotrader serve-http --server both --token "$(openssl rand -hex 24)"

That listens on 127.0.0.1 by default, which Claude cannot reach — put it behind
a tunnel or a host with a real certificate, then add the resulting
``https://…/mcp/tradingview`` URL as a custom connector.

What the transport owes the spec, and does:

* one endpoint path serving POST (messages), GET (405 — nothing is pushed from
  here) and DELETE (ends a session),
* ``202 Accepted`` with no body for a notification, a single JSON object for a
  request,
* an ``Mcp-Session-Id`` on the initialize response,
* ``400`` for an ``MCP-Protocol-Version`` this server does not speak,
* ``Origin`` validation, because a server on localhost is otherwise reachable
  from any web page the machine's browser happens to open.

Exposing this to the internet exposes market data and, if the training view is
served, a run's record.  ``--token`` requires a bearer credential; an
unguessable ``--path`` is the fallback for clients that cannot send headers.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Sequence, Tuple

from .mcp_rpc import INVALID_REQUEST, MCPServer, PARSE_ERROR, error

MAX_BODY_BYTES = 4 * 1024 * 1024


class _Handler(BaseHTTPRequestHandler):
    """One MCP endpoint, spoken over HTTP."""

    protocol_version = "HTTP/1.1"
    server_version = "evotrader-mcp"
    sys_version = ""

    # Set on the ThreadingHTTPServer instance by :func:`serve_http`.
    routes: Dict[str, MCPServer]
    token: str
    allowed_origins: Tuple[str, ...]

    # ------------------------------------------------------------- plumbing
    def _routes(self) -> Dict[str, MCPServer]:
        return getattr(self.server, "routes", {})

    def _send(self, status: int, payload: Optional[Dict[str, Any]] = None, *,
              headers: Optional[Dict[str, str]] = None) -> None:
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(status)
        if body:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if body and self.command != "HEAD":
            self.wfile.write(body)

    def _lock_for(self, endpoint: MCPServer) -> threading.Lock:
        locks = getattr(self.server, "locks", None)
        if locks is None:
            locks = {}
            self.server.locks = locks            # type: ignore[attr-defined]
        return locks.setdefault(id(endpoint), threading.Lock())

    def _endpoint(self) -> Optional[MCPServer]:
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        routes = self._routes()
        return routes.get(path) or routes.get(path + "/")

    def _authorised(self) -> bool:
        token = getattr(self.server, "token", "")
        if not token:
            return True
        header = self.headers.get("Authorization", "")
        scheme, _, value = header.partition(" ")
        return scheme.lower() == "bearer" and secrets.compare_digest(value, token)

    def _origin_allowed(self) -> bool:
        """Guard against DNS rebinding: a browser sends Origin, Claude does not."""
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        allowed = getattr(self.server, "allowed_origins", ())
        return "*" in allowed or origin in allowed

    def _protocol_ok(self) -> bool:
        """Accept any protocol version the client names.

        The spec says to answer 400 to a version the server does not know, but
        a client one revision ahead then has every request rejected before
        initialize can negotiate a version both sides speak — which is exactly
        what a newer client hitting this server did. Negotiation belongs in
        initialize, which answers with a version this server actually speaks.
        """
        return True

    def _guard(self) -> Optional[Tuple[int, Dict[str, Any], Dict[str, str]]]:
        if not self._origin_allowed():
            return 403, {"error": "origin not allowed"}, {}
        if not self._authorised():
            return 401, {"error": "a bearer token is required"}, {
                "WWW-Authenticate": 'Bearer realm="evotrader"'}
        return None

    # -------------------------------------------------------------- methods
    def _too_large(self) -> None:
        self._send(413, {"error": "message too large"},
                   headers={"Connection": "close"})
        self.close_connection = True

    def _read_chunked(self) -> Optional[bytes]:
        """Read a chunked body.  Without this the message is silently lost."""
        chunks: list = []
        total = 0
        while True:
            line = self.rfile.readline(1024)
            if not line:
                return None                      # the client went away
            try:
                size = int(line.split(b";", 1)[0].strip() or b"0", 16)
            except ValueError:
                self._send(400, {"error": "malformed chunked body"},
                           headers={"Connection": "close"})
                self.close_connection = True
                return None
            if size == 0:
                while True:                      # trailing headers, if any
                    trailer = self.rfile.readline(1024)
                    if not trailer or trailer in (b"\r\n", b"\n"):
                        break
                break
            total += size
            if total > MAX_BODY_BYTES:
                self._too_large()
                return None
            chunks.append(self.rfile.read(size))
            self.rfile.read(2)                   # the CRLF after each chunk
        return b"".join(chunks)

    def _read_body(self) -> Optional[bytes]:
        """Drain the request body before answering, whatever the answer is.

        A reply sent while unread bytes remain leaves them at the head of the
        next request on a keep-alive connection, and every later request on it
        fails to parse.  Clients reuse connections, so this has to happen on
        the error paths too.

        Returns None when the request has already been answered.
        """
        if "chunked" in (self.headers.get("Transfer-Encoding") or "").lower():
            return self._read_chunked()
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY_BYTES:
            self._too_large()
            return None
        return self.rfile.read(length) if length else b"" 

    def do_POST(self) -> None:  # noqa: N802 - the name http.server requires
        raw = self._read_body()
        if raw is None:
            return
        if self.path.split("?", 1)[0].rstrip("/") == "/health":
            return self._send(200, {"status": "ok"})
        endpoint = self._endpoint()
        if endpoint is None:
            return self._send(404, {"error": f"no MCP endpoint at {self.path!r}"})
        refusal = self._guard()
        if refusal is not None:
            status, payload, headers = refusal
            return self._send(status, payload, headers=headers)

        if not raw.strip():
            # A connector's reachability probe, not a message. Answering 400
            # here reads as "no server", which is how this looked from the
            # other end.
            return self._send(200, {"status": "ok",
                                    "transport": "streamable-http"})
        try:
            message = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            return self._send(400, error(None, PARSE_ERROR, f"invalid JSON: {exc}"))
        if not isinstance(message, dict):
            # Batching was removed in 2025-06-18; one message per request.
            return self._send(400, error(None, INVALID_REQUEST,
                                         "expected a single JSON-RPC object"))

        # One message at a time per endpoint: these servers hold a SQLite
        # connection and in-memory caches built for a single-threaded stdio
        # client, and http.server hands every request to a new thread.
        with self._lock_for(endpoint):
            response = endpoint.handle(message)
        if response is None:
            # A notification or a response: accepted, nothing to say back.
            return self._send(202)
        headers = {}
        if message.get("method") == "initialize":
            headers["Mcp-Session-Id"] = secrets.token_hex(16)
        return self._send(200, response, headers=headers)

    def do_GET(self) -> None:  # noqa: N802
        if self._read_body() is None:
            return
        if self.path.startswith("/.well-known/"):
            # No OAuth here. A bare 404 is how a client learns that.
            return self._send(404)
        if self.path.split("?", 1)[0].rstrip("/") == "/health":
            return self._send(200, {"status": "ok",
                                    "endpoints": sorted(self._routes())})
        if self._endpoint() is None:
            return self._send(404, {"error": f"no MCP endpoint at {self.path!r}"})
        refusal = self._guard()
        if refusal is not None:
            status, payload, headers = refusal
            return self._send(status, payload, headers=headers)
        # Nothing is ever pushed from this server, so there is no stream to open.
        return self._send(405, {"error": "this endpoint does not open an SSE stream"},
                          headers={"Allow": "POST, DELETE"})

    def do_OPTIONS(self) -> None:  # noqa: N802
        """Preflight.  http.server answers 501 otherwise, which looks broken."""
        self._read_body()
        origin = self.headers.get("Origin")
        headers = {"Allow": "GET, POST, DELETE, OPTIONS, HEAD",
                   "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
                   "Access-Control-Allow-Headers": "Content-Type, Authorization, "
                                                   "Mcp-Session-Id, MCP-Protocol-Version",
                   "Access-Control-Expose-Headers": "Mcp-Session-Id",
                   "Access-Control-Max-Age": "600"}
        if origin and self._origin_allowed():
            headers["Access-Control-Allow-Origin"] = origin
        return self._send(204, headers=headers)

    def do_HEAD(self) -> None:  # noqa: N802
        self._read_body()
        if self._endpoint() is None and \
                self.path.split("?", 1)[0].rstrip("/") != "/health":
            return self._send(404)
        return self._send(200)

    def do_DELETE(self) -> None:  # noqa: N802
        if self._read_body() is None:
            return
        if self._endpoint() is None:
            return self._send(404, {"error": f"no MCP endpoint at {self.path!r}"})
        refusal = self._guard()
        if refusal is not None:
            status, payload, headers = refusal
            return self._send(status, payload, headers=headers)
        return self._send(204)          # sessions hold nothing to tear down

    def log_message(self, fmt: str, *args: Any) -> None:
        # Never log query strings or bodies: a path can carry a shared secret.
        sys.stderr.write(f"{self.command} {self.path.split('?')[0]} "
                         f"{fmt % args if args else ''}\n".replace("\n\n", "\n"))


def build_routes(which: str, *, db_path: str = "", source: str = "tradingview",
                 path: str = "/mcp") -> Dict[str, MCPServer]:
    """Map endpoint paths to servers."""
    from .mcp_server import build_server as build_training
    from .tv_mcp import build_server as build_tradingview

    base = "/" + path.strip("/")
    if which == "training":
        return {base: build_training(db_path)}
    if which == "tradingview":
        return {base: build_tradingview(source=source, db_path=db_path)}
    if which == "both":
        return {f"{base}/training": build_training(db_path),
                f"{base}/tradingview": build_tradingview(source=source,
                                                         db_path=db_path)}
    raise ValueError("server must be training, tradingview or both")


def serve_http(routes: Dict[str, MCPServer], *, host: str = "127.0.0.1",
               port: int = 8787, token: str = "",
               allowed_origins: Sequence[str] = ()) -> ThreadingHTTPServer:
    """Start the HTTP transport.  Returns the server; caller runs it."""
    httpd = ThreadingHTTPServer((host, port), _Handler)
    httpd.routes = routes                        # type: ignore[attr-defined]
    httpd.token = token                          # type: ignore[attr-defined]
    httpd.allowed_origins = tuple(allowed_origins)   # type: ignore[attr-defined]
    httpd.daemon_threads = True
    return httpd


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="evotrader-mcp-http",
        description="Serve the MCP servers over Streamable HTTP, for use as a "
                    "Claude custom connector.")
    parser.add_argument("--server", choices=["tradingview", "training", "both"],
                        default="tradingview")
    parser.add_argument("--host", default="127.0.0.1",
                        help="0.0.0.0 to accept remote connections (use a token)")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--path", default="/mcp", help="endpoint path")
    parser.add_argument("--token", default=os.environ.get("EVOTRADER_MCP_TOKEN", ""),
                        help="require this bearer token (or $EVOTRADER_MCP_TOKEN)")
    parser.add_argument("--allow-origin", action="append", default=[],
                        help="permit this Origin header; repeatable")
    parser.add_argument("--source", choices=["tradingview", "yahoo", "synthetic"],
                        default="tradingview")
    parser.add_argument("--db", dest="db_path", default="")
    args = parser.parse_args(argv)

    routes = build_routes(args.server, db_path=args.db_path, source=args.source,
                          path=args.path)
    httpd = serve_http(routes, host=args.host, port=args.port, token=args.token,
                       allowed_origins=args.allow_origin)
    for endpoint in sorted(routes):
        print(f"listening on http://{args.host}:{args.port}{endpoint}",
              file=sys.stderr)
    if not args.token:
        print("no --token: anyone who can reach this port can use these tools",
              file=sys.stderr)
    if args.host not in ("127.0.0.1", "localhost", "::1") and not args.token:
        print("refusing to serve a public interface without a token",
              file=sys.stderr)
        return 2
    print("a custom connector needs this reachable over public HTTPS — put a "
          "tunnel or a reverse proxy in front", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - interactive
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
