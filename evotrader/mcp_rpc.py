"""The MCP wire protocol, shared by this package's servers.

Newline-delimited JSON-RPC 2.0 on stdin and stdout — the subset of the Model
Context Protocol a read-only server needs: initialize, tools, resources, ping.
Speaking it directly costs about two hundred lines and keeps the package's
dependency list at numpy.

A server is a :class:`Registry` of tools, a context object handed to every
handler, and optionally some resources::

    TOOLS = Registry()

    @TOOLS.tool("echo", "Echo", "Say it back", {"text": {"type": "string"}},
                required=["text"])
    def _echo(ctx, args):
        return args["text"], {"text": args["text"]}

    serve(MCPServer(ctx, TOOLS, name="demo", instructions="..."))

Handlers return ``(text, structured)``: the text a client shows, and the JSON a
client can compute on.  Raising :class:`ToolError` reports a problem the caller
can fix without killing the session.
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, TextIO, Tuple

PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

ToolResult = Tuple[str, Dict[str, Any]]
Handler = Callable[[Any, Dict[str, Any]], ToolResult]


class ToolError(RuntimeError):
    """A problem the caller can fix: unknown id, missing data, bad argument."""


@dataclass
class Tool:
    name: str
    title: str
    description: str
    schema: Dict[str, Any]
    handler: Handler
    read_only: bool = True

    def spec(self) -> Dict[str, Any]:
        return {"name": self.name, "title": self.title,
                "description": self.description, "inputSchema": self.schema,
                "annotations": {"readOnlyHint": self.read_only,
                                "openWorldHint": False}}


@dataclass
class Registry:
    """The tools one server exposes."""

    tools: Dict[str, Tool] = field(default_factory=dict)
    common_properties: Dict[str, Any] = field(default_factory=dict)

    def tool(self, name: str, title: str, description: str,
             properties: Optional[Dict[str, Any]] = None,
             required: Sequence[str] = (),
             read_only: bool = True) -> Callable[[Handler], Handler]:
        def decorate(fn: Handler) -> Handler:
            props = dict(properties or {})
            for key, spec in self.common_properties.items():
                props.setdefault(key, spec)
            self.tools[name] = Tool(name, title, description,
                                    {"type": "object", "properties": props,
                                     "required": list(required)}, fn, read_only)
            return fn

        return decorate

    def specs(self) -> List[Dict[str, Any]]:
        return [t.spec() for t in self.tools.values()]

    def __contains__(self, name: object) -> bool:
        return name in self.tools

    def __len__(self) -> int:
        return len(self.tools)


# ------------------------------------------------------------ argument helpers

def str_arg(args: Dict[str, Any], key: str, default: str = "") -> str:
    value = args.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ToolError(f"{key} must be a string")
    return value.strip()


def required_str(args: Dict[str, Any], key: str) -> str:
    value = str_arg(args, key)
    if not value:
        raise ToolError(f"{key} is required")
    return value


def int_arg(args: Dict[str, Any], key: str, default: int, *,
            lo: int = 1, hi: int = 500) -> int:
    value = args.get(key, default)
    if value is None:
        return default
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ToolError(f"{key} must be a whole number") from None
    return max(lo, min(hi, n))


def float_arg(args: Dict[str, Any], key: str, default: float, *,
              lo: float = 0.0, hi: float = 1e9) -> float:
    value = args.get(key, default)
    if value is None:
        return default
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise ToolError(f"{key} must be a number") from None
    if math.isnan(x):
        raise ToolError(f"{key} must be a number")
    return max(lo, min(hi, x))


def choice_arg(args: Dict[str, Any], key: str, allowed: Sequence[str]) -> str:
    value = str_arg(args, key, allowed[0]) or allowed[0]
    if value not in allowed:
        raise ToolError(f"{key} must be one of {', '.join(allowed)}")
    return value


def list_arg(args: Dict[str, Any], key: str) -> List[Any]:
    """Accept a JSON list, or a comma-separated string for convenience."""
    value = args.get(key)
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return list(value)
    raise ToolError(f"{key} must be a list")


# ----------------------------------------------------------------- formatting

def score_text(value: Optional[float]) -> str:
    return f"{value:+.3f}" if value is not None and math.isfinite(value) else "  -   "


def clip(text: str, limit: int = 1200) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit].rstrip() + " ..."


# --------------------------------------------------------------- the protocol

class MCPServer:
    """Routes one client's messages to a registry's tools."""

    def __init__(self, context: Any, registry: Registry, *, name: str,
                 title: str = "", version: str = "", instructions: str = "",
                 resources: Optional[Callable[[Any], List[Dict[str, Any]]]] = None,
                 read_resource: Optional[Callable[[Any, str], Dict[str, Any]]] = None,
                 resource_templates: Sequence[Dict[str, Any]] = ()):
        self.context = context
        self.registry = registry
        self.name = name
        self.title = title or name
        self.version = version or _package_version()
        self.instructions = instructions
        self._resources = resources
        self._read_resource = read_resource
        self._templates = list(resource_templates)
        self.initialized = False

    # --------------------------------------------------------------- routing
    def handle(self, message: Any) -> Optional[Dict[str, Any]]:
        """Return the response to one message, or None for a notification."""
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return error(None, INVALID_REQUEST, "expected a JSON-RPC 2.0 object")
        method = message.get("method")
        msg_id = message.get("id")
        if not isinstance(method, str):
            return error(msg_id, INVALID_REQUEST, "missing method")
        params = message.get("params") or {}
        if not isinstance(params, dict):
            return error(msg_id, INVALID_PARAMS, "params must be an object")

        if method.startswith("notifications/"):
            if method == "notifications/initialized":
                self.initialized = True
            return None
        if msg_id is None:
            return None          # an unknown notification: nothing to answer

        try:
            if method == "initialize":
                return result(msg_id, self._initialize(params))
            if method == "ping":
                return result(msg_id, {})
            if method == "tools/list":
                return result(msg_id, {"tools": self.registry.specs()})
            if method == "tools/call":
                return result(msg_id, self._call_tool(params))
            if method == "resources/list":
                listed = self._resources(self.context) if self._resources else []
                return result(msg_id, {"resources": listed})
            if method == "resources/templates/list":
                return result(msg_id, {"resourceTemplates": self._templates})
            if method == "resources/read":
                uri = params.get("uri")
                if not isinstance(uri, str) or not uri:
                    return error(msg_id, INVALID_PARAMS, "uri is required")
                if self._read_resource is None:
                    return error(msg_id, METHOD_NOT_FOUND,
                                 "this server exposes no resources")
                return result(msg_id, {"contents": [
                    self._read_resource(self.context, uri)]})
        except ToolError as exc:
            return error(msg_id, INVALID_PARAMS, str(exc))
        except Exception as exc:  # noqa: BLE001 - a bad call must not kill the server
            return error(msg_id, INTERNAL_ERROR, f"{type(exc).__name__}: {exc}")
        return error(msg_id, METHOD_NOT_FOUND, f"unknown method {method!r}")

    def _initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        asked = params.get("protocolVersion")
        version = asked if asked in SUPPORTED_PROTOCOLS else PROTOCOL_VERSION
        capabilities: Dict[str, Any] = {"tools": {"listChanged": False}}
        if self._resources is not None:
            capabilities["resources"] = {"listChanged": False, "subscribe": False}
        return {
            "protocolVersion": version,
            "capabilities": capabilities,
            "serverInfo": {"name": self.name, "title": self.title,
                           "version": self.version},
            "instructions": self.instructions,
        }

    def _call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params.get("name")
        impl = self.registry.tools.get(name) if isinstance(name, str) else None
        if impl is None:
            return tool_error(f"unknown tool {name!r}; available: "
                              f"{', '.join(sorted(self.registry.tools))}")
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            return tool_error("arguments must be an object")
        for key in impl.schema.get("required", []):
            if args.get(key) in (None, "", [], {}):
                return tool_error(f"{impl.name} needs {key!r}")
        try:
            text, structured = impl.handler(self.context, args)
        except ToolError as exc:
            return tool_error(str(exc))
        except Exception as exc:  # noqa: BLE001 - report, don't crash the session
            return tool_error(f"{type(exc).__name__}: {exc}")
        return {"content": [{"type": "text", "text": text}],
                "structuredContent": structured, "isError": False}


def _package_version() -> str:
    from . import __version__
    return __version__


def result(msg_id: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": payload}


def error(msg_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def tool_error(message: str) -> Dict[str, Any]:
    return {"content": [{"type": "text", "text": message}], "isError": True}


def serve(server: MCPServer, stdin: Optional[TextIO] = None,
          stdout: Optional[TextIO] = None) -> int:
    """Read messages until stdin closes.  Only JSON goes to stdout."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError as exc:
            response = error(None, PARSE_ERROR, f"invalid JSON: {exc}")
        else:
            response = server.handle(message)
        if response is not None:
            stdout.write(json.dumps(response) + "\n")
            stdout.flush()
    closer = getattr(server.context, "close", None)
    if callable(closer):
        closer()
    return 0
