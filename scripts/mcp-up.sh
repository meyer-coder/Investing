#!/usr/bin/env bash
# Start the MCP server and its tunnel, and print the URL to paste into Claude.
#
#   scripts/mcp-up.sh                  # quick tunnel: a new URL every run
#   TUNNEL_HOSTNAME=mcp.example.com scripts/mcp-up.sh
#                                      # named tunnel: the same URL, always
#
# Stop everything with Ctrl-C, or `scripts/mcp-down.sh` if it was started
# in the background.
set -euo pipefail

cd "$(dirname "$0")/.."

PORT="${PORT:-8787}"
SERVER="${SERVER:-tradingview}"
LOG_DIR="${LOG_DIR:-$HOME/.evotrader}"
mkdir -p "$LOG_DIR"

python3 -m evotrader.cli serve-http --server "$SERVER" --port "$PORT" \
    >"$LOG_DIR/server.log" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$LOG_DIR/server.pid"

cleanup() {
    kill "$SERVER_PID" 2>/dev/null || true
    [ -n "${TUNNEL_PID:-}" ] && kill "$TUNNEL_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Wait for the server rather than racing it.
for _ in $(seq 1 40); do
    if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then break; fi
    sleep 0.25
done
if ! curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    echo "the MCP server did not come up; see $LOG_DIR/server.log" >&2
    tail -5 "$LOG_DIR/server.log" >&2 || true
    exit 1
fi
echo "MCP server up on port $PORT"

if [ -n "${TUNNEL_HOSTNAME:-}" ]; then
    # A named tunnel keeps one hostname forever, so the connector URL never
    # has to change again.  TUNNEL_CREDENTIALS lets a machine run a tunnel that
    # was created on someone else's Cloudflare account: they send the JSON, and
    # this machine never needs their login.
    CRED_ARGS=()
    if [ -n "${TUNNEL_CREDENTIALS:-}" ]; then
        CRED_ARGS=(--credentials-file "$TUNNEL_CREDENTIALS")
    fi
    cloudflared tunnel --url "http://localhost:$PORT" \
        "${CRED_ARGS[@]}" run "${TUNNEL_NAME:-evotrader}" \
        >"$LOG_DIR/tunnel.log" 2>&1 &
    TUNNEL_PID=$!
    echo "$TUNNEL_PID" > "$LOG_DIR/tunnel.pid"
    echo
    echo "  MCP server URL:  https://$TUNNEL_HOSTNAME/mcp"
    echo
else
    cloudflared tunnel --url "http://localhost:$PORT" \
        >"$LOG_DIR/tunnel.log" 2>&1 &
    TUNNEL_PID=$!
    echo "$TUNNEL_PID" > "$LOG_DIR/tunnel.pid"
    printf 'waiting for the tunnel URL'
    URL=""
    for _ in $(seq 1 60); do
        URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG_DIR/tunnel.log" \
              2>/dev/null | head -1 || true)
        [ -n "$URL" ] && break
        printf '.'
        sleep 1
    done
    echo
    if [ -z "$URL" ]; then
        echo "the tunnel did not report a URL; see $LOG_DIR/tunnel.log" >&2
        exit 1
    fi
    echo
    echo "  MCP server URL:  $URL/mcp"
    echo
    echo "  (a quick tunnel gets a new URL every run — set TUNNEL_HOSTNAME for"
    echo "   a permanent one, see README)"
    echo
fi

echo "logs: $LOG_DIR  ·  Ctrl-C to stop both"
wait
