"""The explorer page: one self-contained HTML file.

Open ``results/explorer.html`` straight from disk.  All data is embedded,
gzip-compressed and base64-encoded, and unpacked in the browser with
``DecompressionStream``; sorting, filtering, the roll-ups and each strategy's
profile are computed client-side.

The page itself lives in ``templates/explorer.html``; it is the reference
implementation of ``docs/presentation-standard.md``.

Layout: a one-screen app.  The strategy table fills the window with a frozen
header and frozen ID / name columns, scrolls smoothly through every row
(virtualised, no pages), and a docked inspector on the right shows the
selected strategy.  Arrow keys move the selection; "/" focuses search.
"""
from __future__ import annotations

import base64
import gzip
import json
import math
import os

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "templates", "explorer.html")


def _clean(x):
    if isinstance(x, float):
        return None if (math.isnan(x) or math.isinf(x)) else x
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if hasattr(x, "item"):          # numpy scalar
        return _clean(x.item())
    return x


def render(payload: dict, *, standalone: bool = True) -> str:
    """HTML for the explorer.  ``standalone=False`` omits the document
    skeleton (doctype/html/head/body) for hosts that add their own."""
    raw = json.dumps(_clean(payload), separators=(",", ":"), allow_nan=False).encode()
    blob = base64.b64encode(gzip.compress(raw, 9)).decode()
    with open(TEMPLATE_PATH, encoding="utf-8") as fh:
        template = fh.read()
    body = template.replace("__DATA__", blob)
    if payload.get("run") == "run2":
        body = body.replace("<title>Confluence Trade Explorer</title>", "<title>Futures Confluence Explorer</title>", 1)
    if not standalone:
        return body
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            "</head>\n<body>\n" + body + "\n</body>\n</html>\n")
