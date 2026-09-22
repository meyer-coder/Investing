"""One-line renderings of a backtest's metrics, shared by the MCP servers."""
from __future__ import annotations

import dataclasses
import json
from typing import Any, Dict, Optional

from .fitness import Metrics

_FIELDS = {f.name for f in dataclasses.fields(Metrics)}


def metrics_dict(raw: Any) -> Optional[Dict[str, Any]]:
    """Parse stored metrics JSON, tolerating nulls and anything malformed."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, Metrics):
        return raw.to_dict()
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def to_metrics(raw: Any) -> Optional[Metrics]:
    d = metrics_dict(raw)
    if d is None:
        return None
    return Metrics(**{k: v for k, v in d.items() if k in _FIELDS})


def metrics_line(raw: Any) -> str:
    m = to_metrics(raw)
    return m.summary() if m else "-"
