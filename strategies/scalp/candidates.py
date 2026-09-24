"""Every sharp one-minute move in four years of stock minutes, with what came next.

    python strategies/scalp/candidates.py          # builds data/cache/duka/panel/candidates.npz

The family searches rerun the whole panel for each rule.  This pulls out, once,
every (session, name, minute) where a name moved hard on its own (a one-minute
return beyond half its typical range and more than 1.5 standard deviations
from the other names, up or down, 09:31 to 15:50), with what a trader could
see at that minute's close and the returns that followed from the next
minute's open (1 to 5 minutes, and the same a minute late).  The price is
the one actually paid (splits.py), so costs quoted per share are right.
Rules and models are then tried on this table in seconds, and the book
(slots, one position per name) is replayed from it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "strategies" / "scalp"))
import panel                                                                 # noqa: E402
import splits                                                                # noqa: E402

OUT = panel.CACHE / "candidates.npz"
FEATURES = ["minute", "r1_atr", "resid_z", "r1", "atr", "resid", "gap", "mkt_r1", "mkt_r5", "ret5", "ret15", "ret30",
            "day_ret", "range_pos", "clv", "bar_range", "breadth_down", "breadth_up", "prev_z", "prev_r1_atr",
            "vol20", "atr_ratio", "px", "prev_day_ret", "sector_z"]
HORIZONS = (1, 2, 3, 4, 5)
_P: dict = {}


def _day(i: int):
    cube, names, vol, fac = _P["cube"], _P["names"], _P["vol"], _P["fac"]
    prev = cube[i - 1]
    f = panel.features(cube[i], prev[:, -1, 3].astype(float), prev)
    o, h, l, c, r1, atr, rz = f["o"], f["h"], f["l"], f["c"], f["r1"], f["atr"], f["resid_z"]
    n, T = c.shape
    with np.errstate(invalid="ignore", divide="ignore"):
        r1_atr = r1 / atr
        m = (np.abs(r1_atr) > 0.5) & (np.abs(rz) > 1.5)
    m[:, :1] = False
    m[:, 381:] = False
    m &= ~np.isnan(rz)
    ks, ts = np.nonzero(m)
    if not len(ks):
        return None
    mk = f["mkt_r1"]
    mk5 = np.full(T, np.nan)
    mk5[5:] = np.nancumsum(np.nan_to_num(mk))[5:] - np.nancumsum(np.nan_to_num(mk))[:-5]

    def back(x, k):
        out = np.full((n, T), np.nan)
        out[:, k:] = c[:, k:] / c[:, :-k] - 1.0
        return out

    ret5, ret15, ret30 = back(c, 5), back(c, 15), back(c, 30)
    hi = np.maximum.accumulate(h, axis=1)
    lo = np.minimum.accumulate(l, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        range_pos = (c - lo) / (hi - lo)
        clv = (c - l) / (h - l)
        bar_range = (h - l) / c / atr
        down = ((r1_atr < -0.5) & (rz < -2)).sum(axis=0)
        up = ((r1_atr > 0.5) & (rz > 2)).sum(axis=0)
    prev_z = np.full((n, T), np.nan)
    prev_z[:, 1:] = rz[:, :-1]
    prev_r = np.full((n, T), np.nan)
    prev_r[:, 1:] = r1_atr[:, :-1]
    v20 = np.nanmean(vol[max(i - 20, 0):i], axis=0) if i >= 5 else np.full(n, np.nan)
    day_atr = np.nanmean(atr[:, 15:], axis=1)
    prev_day = prev[:, -1, 3].astype(float) / prev[:, 0, 0].astype(float) - 1.0
    sz = _P["sector"](f) if _P.get("sector") else np.full((n, T), np.nan)
    feats = np.column_stack([
        ts, r1_atr[ks, ts], rz[ks, ts], r1[ks, ts], atr[ks, ts], f["resid"][ks, ts], f["gap"][ks], mk[ts], mk5[ts],
        ret5[ks, ts], ret15[ks, ts], ret30[ks, ts], c[ks, ts] / o[ks, 0] - 1.0, range_pos[ks, ts], clv[ks, ts],
        bar_range[ks, ts], down[ts], up[ts], prev_z[ks, ts], prev_r[ks, ts], v20[ks], atr[ks, ts] / _P["atr20"][i, ks],
        o[ks, np.minimum(ts + 1, T - 1)] * fac[i, ks], prev_day[ks], sz[ks, ts]]).astype(np.float32)
    fwd = np.full((len(ks), 2, len(HORIZONS)), np.nan, dtype=np.float32)
    for j, hz in enumerate(HORIZONS):
        for dl in (0, 1):
            t_in, t_out = ts + 1 + dl, ts + 1 + dl + hz
            ok = t_out < 386
            fwd[ok, dl, j] = o[ks[ok], t_out[ok]] / o[ks[ok], t_in[ok]] - 1.0
    return np.full(len(ks), i, dtype=np.int16), ks.astype(np.int16), feats, fwd


def build() -> Path:
    import multiprocessing as mp
    import families2
    cube, dates, names = panel.load_panel()
    vol = np.nanstd(cube[:, :, 1:, 3] / cube[:, :, :-1, 3] - 1.0, axis=2)
    atr_day = np.nanmean((cube[:, :, 15:, 1] - cube[:, :, 15:, 2]) / cube[:, :, 15:, 3], axis=2)
    atr20 = np.full_like(atr_day, np.nan)
    for i in range(len(dates)):
        if i >= 5:
            atr20[i] = np.nanmean(atr_day[max(i - 20, 0):i], axis=0)
    _P.update(cube=cube, names=names, vol=vol, fac=splits.matrix(dates, names), atr20=atr20,
              sector=lambda f: families2.sector_resid(f, names))
    with mp.get_context("fork").Pool(4) as pool:
        parts = [p for p in pool.map(_day, range(1, len(dates)), chunksize=8) if p is not None]
    day = np.concatenate([p[0] for p in parts])
    name = np.concatenate([p[1] for p in parts])
    x = np.concatenate([p[2] for p in parts])
    y = np.concatenate([p[3] for p in parts])
    np.savez_compressed(OUT, day=day, name=name, x=x, y=y, dates=np.array(dates), names=np.array(names),
                        features=np.array(FEATURES), horizons=np.array(HORIZONS))
    return OUT


def load():
    z = np.load(OUT, allow_pickle=True)
    return {k: z[k] for k in z.files}


if __name__ == "__main__":
    import time
    t0 = time.time()
    p = build()
    d = load()
    print(f"{len(d['day'])} candidate minutes, {d['x'].shape[1]} features, {time.time() - t0:.0f} s -> {p}")
