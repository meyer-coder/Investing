"""The FX Replay scripts must take the same trades as the Python engine."""
from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess

import numpy as np
import pytest

from confluence import components2  # noqa: F401  (registers the legs)
from confluence.bars import PROP_SESSIONS, minute_clock, resample
from confluence.components import Ctx
from confluence.data import Minutes
from confluence.families2 import generate2
from confluence.futures import backtest_markets
from confluence.fxr import CONFIGS, render
from confluence.runner import backtest_frame

NODE = shutil.which("node")


def _market(days=260, seed=5):
    """A trending, mean-reverting random walk on weekday minutes, NQ-like prices."""
    rng = np.random.default_rng(seed)
    t0 = int(dt.datetime(2024, 1, 2, 23, 0, tzinfo=dt.timezone.utc).timestamp()) // 60
    t = np.arange(t0, t0 + days * 1440, dtype=np.int64)
    wd = ((t * 60 // 86400) + 3) % 7                       # 1970-01-01 was a Thursday
    t = t[wd < 5]
    n = t.size
    drift = np.repeat(rng.normal(0, 0.9, n // 180 + 1), 180)[:n]
    c = 17000 + np.cumsum(drift + rng.normal(0, 4.0, n))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + np.abs(rng.normal(0, 2.0, n))
    l = np.minimum(o, c) - np.abs(rng.normal(0, 2.0, n))
    return Minutes("TEST", t, o, h, l, c, {}, rng.integers(1, 50, n).astype(float))


@pytest.mark.parametrize("sid", sorted(CONFIGS))
def test_rendered_script_is_complete(sid):
    js = render(sid, {"trades": 10, "win": 0.5, "net_r": 0.1})
    assert "__" not in js.replace("__trades", "")
    assert "init = () =>" in js and "onTick = (" in js


@pytest.mark.skipif(NODE is None, reason="node is not installed")
@pytest.mark.parametrize("sid", sorted(CONFIGS))
def test_fxr_script_takes_the_engines_trades(sid, tmp_path):
    s = next(x for x in generate2() if x.sid == sid)
    tf = int(CONFIGS[sid]["TF"])
    frame = resample(minute_clock(_market()), tf)
    tr = backtest_frame(Ctx(frame), s, 0, backtest_markets(), PROP_SESSIONS, 4.0)
    py, session = {}, set()
    for k in range(tr["gross"].size):
        fill_bar = int(frame.m1_bar[np.searchsorted(frame.clock.m.t, tr["entry"][k])])
        key = (int(frame.t[fill_bar]) * 60000, int(tr["dir"][k]))
        py[key] = float(tr["gross"][k] - tr["cost"][k])
        if tr["reason"][k] == 3:
            session.add(key)
    assert len(py) >= 5, "the synthetic market should produce a few trades"

    bars = {"t": (frame.t.astype(np.int64) * 60000).tolist(), "o": frame.o.tolist(), "h": frame.h.tolist(),
            "l": frame.l.tolist(), "c": frame.c.tolist()}
    (tmp_path / "bars.json").write_text(json.dumps(bars))
    (tmp_path / "s.js").write_text(render(sid))
    subprocess.run([NODE, "tests/fxr_harness.js", str(tmp_path / "s.js"), str(tmp_path / "bars.json"),
                    str(tmp_path / "out.json")], check=True, capture_output=True, timeout=120)
    js = {(int(x["t0"]), int(x["dir"])): x["r"] for x in json.loads((tmp_path / "out.json").read_text())}

    assert set(js) == set(py)                                   # same setups, same fill bars, same side
    # Stop and trailing exits agree; session exits can differ a little on 60m bars, where the script
    # leaves at the 16:00 bar's open and the engine at 16:05.
    other = [k for k in py if k not in session]
    assert np.mean([abs(js[k] - py[k]) < 0.05 for k in other]) >= 0.95
    total_py, total_js = sum(py.values()), sum(js.values())
    assert abs(total_js - total_py) <= 0.05 * abs(total_py) + 1.0


BAD_EDITS = {
    "new": ("  const now = time(0);", "  const now = time(0);\n  const junk = new Array(3);"),
    "empty array": ("const S_BT = [0];", "const S_BT = [];"),
    "negative literal": ("let S_FRESH = true;", "let S_FRESH = -1;"),
    "const helper": ("  var resetState = function", "  const resetState = function"),
    "top-level helper": ("onTick = (", "var helper = function () { return 1; };\n\nonTick = ("),
    "clock": ("  const now = time(0);", "  const now = time(0);\n  const wall = Date.now();"),
}


@pytest.mark.skipif(NODE is None, reason="node is not installed")
@pytest.mark.parametrize("what", sorted(BAD_EDITS))
def test_harness_rejects_what_fx_replay_rejects(what, tmp_path):
    """FX Replay refuses `new`, keeps only literal/object/non-empty-array top-level state, re-runs the
    rest of the top level on every bar and moves const helpers out of onTick. The harness must catch
    each of these, or the tests above would pass scripts that fail in FX Replay."""
    old, new = BAD_EDITS[what]
    js = render("21-155")
    assert old in js
    (tmp_path / "s.js").write_text(js.replace(old, new, 1))
    bars = {"t": [1_700_000_000_000 + 3_600_000 * i for i in range(50)], "o": [1.0] * 50, "h": [1.5] * 50,
            "l": [0.5] * 50, "c": [1.0] * 50}
    (tmp_path / "bars.json").write_text(json.dumps(bars))
    out = subprocess.run([NODE, "tests/fxr_harness.js", str(tmp_path / "s.js"), str(tmp_path / "bars.json"),
                          str(tmp_path / "out.json")], capture_output=True, text=True, timeout=60)
    assert out.returncode == 3, out.stdout + out.stderr
    assert "FX Replay would reject" in out.stderr


TSC = shutil.which("tsc")


@pytest.mark.skipif(TSC is None, reason="TypeScript (tsc) is not installed")
@pytest.mark.parametrize("sid", sorted(CONFIGS))
@pytest.mark.parametrize("ext", [".js", ".ts"])
def test_fxr_script_type_checks_like_the_fx_replay_editor(sid, ext, tmp_path):
    """FX Replay's editor flags type errors (not implicit any). tests/fxr_api.d.ts declares the
    documented API; `text` is left out because the editor does not know it."""
    src = tmp_path / f"s{ext}"
    src.write_text(render(sid))
    cmd = [TSC, "--noEmit", "--strict", "--noImplicitAny", "false", "--target", "es2020", "--lib", "es2020,dom",
           "tests/fxr_api.d.ts", str(src)] + (["--allowJs", "--checkJs"] if ext == ".js" else [])
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stdout + out.stderr
