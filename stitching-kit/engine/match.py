"""The matcher: banded DTW between z-scored, length-200 curves.

normalise(x)            -> resample to N=200, z-score (None if flat)
dtw_banded(a, b)        -> squared-difference DTW in a Sakoe-Chiba band of +-10, cost / path length
dtw_batch(a, B)         -> same, for one query against many rows at once (vectorised over rows)
match_forward(curve)    -> top-k library tracks for a data curve
match_reverse(song)     -> top-k data curves for a song energy curve
alignment(curve, tid)   -> data step -> song second map, moment timestamps snapped to beats/onsets
"""
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import curves as C

ROOT = Path(__file__).resolve().parents[1]
N = 200
BAND = 10
LIB = ROOT / "library" / "curves.npz"
CURVE_INDEX = ROOT / "curves" / "index.npz"
CALIB = ROOT / "logs" / "match_calibration.json"
POP = ROOT / "logs" / "popularity_penalty.json"


# ---------------------------------------------------------------- normalise + DTW
def normalise(x, n=N):
    v = C.resample(x, n)
    if not np.isfinite(v).all():
        return None
    sd = v.std()
    if sd < 1e-6:
        return None
    return (v - v.mean()) / sd


def dtw_batch(a, B, band=BAND):
    """a: (n,) query, or (m, n) one query per row; B: (m, n).
    Returns (m,) DTW cost / path length (squared difference, Sakoe-Chiba band). Vectorised over the m pairs;
    ties prefer diagonal, then up, then left (same order as dtw_path)."""
    B = np.atleast_2d(np.asarray(B, dtype=np.float64))
    m, n = B.shape
    A = np.asarray(a, dtype=np.float64)
    At = A.T if A.ndim == 2 else A[:, None]  # (n, m) or (n, 1)
    Bt = np.ascontiguousarray(B.T)          # (n, m)
    INF = np.inf
    # D[j] holds cumulative cost of cell (i, j) for the current row; band width is 2*band+1
    Dp = np.full((n, m), INF); Lp = np.zeros((n, m))
    Dc = np.full((n, m), INF); Lc = np.zeros((n, m))
    for i in range(n):
        lo, hi = max(0, i - band), min(n - 1, i + band)
        Dc[max(0, lo - 1): hi + 2] = INF
        for j in range(lo, hi + 1):
            c = (At[i] - Bt[j]) ** 2
            if i == 0 and j == 0:
                Dc[0] = c
                Lc[0] = 1
                continue
            if i > 0 and j > 0:
                best = Dp[j - 1].copy(); bl = Lp[j - 1].copy()
            else:
                best = np.full(m, INF); bl = np.zeros(m)
            if i > 0:
                up = Dp[j]
                msk = up < best
                if msk.any():
                    best[msk] = up[msk]; bl[msk] = Lp[j][msk]
            if j > 0:
                left = Dc[j - 1]
                msk = left < best
                if msk.any():
                    best[msk] = left[msk]; bl[msk] = Lc[j - 1][msk]
            Dc[j] = c + best
            Lc[j] = bl + 1
        Dp, Dc = Dc, Dp
        Lp, Lc = Lc, Lp
    return Dp[n - 1] / Lp[n - 1]


def dtw_banded(a, b, band=BAND):
    return float(dtw_batch(np.asarray(a, float), np.asarray(b, float)[None, :], band)[0])


def dtw_path(a, b, band=BAND):
    """Full DTW (single pair) with backtracking. Returns (cost/len, path as list of (i, j))."""
    n, m = len(a), len(b)
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0
    for i in range(1, n + 1):
        jc = int(round(i * m / n))
        lo, hi = max(1, jc - band), min(m, jc + band)
        for j in range(lo, hi + 1):
            c = (a[i - 1] - b[j - 1]) ** 2
            D[i, j] = c + min(D[i - 1, j - 1], D[i - 1, j], D[i, j - 1])
    i, j, path = n, m, []
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        k = np.argmin([D[i - 1, j - 1], D[i - 1, j], D[i, j - 1]])
        if k == 0:
            i, j = i - 1, j - 1
        elif k == 1:
            i -= 1
        else:
            j -= 1
    path.reverse()
    return D[n, m] / len(path), path


# ---------------------------------------------------------------- library + curve indexes
@lru_cache(maxsize=1)
def library():
    z = np.load(LIB)
    ids = [str(x) for x in z["ids"]]
    off = z["curve_off"]
    raw = [z["curve"][off[i]: off[i + 1]] for i in range(len(ids))]
    norm, keep = [], []
    for i, r in enumerate(raw):
        v = normalise(r)
        if v is not None:
            norm.append(v)
            keep.append(i)
    bo, oo = z["beats_off"], z["onsets_off"]
    return {
        "ids": [ids[i] for i in keep],
        "raw": [raw[i] for i in keep],
        "M": np.array(norm),
        "t0": z["t0"][keep], "duration": z["duration"][keep], "tempo": z["tempo"][keep],
        "beats": [z["beats"][bo[i]: bo[i + 1]] for i in keep],
        "onsets": [z["onsets"][oo[i]: oo[i + 1]] for i in keep],
    }


def build_curve_index(sources=None):
    allc = C.load_all(sources)
    ids, src, titles, M = [], [], [], []
    for c in allc:
        v = normalise(C.values(c))
        if v is None:
            continue
        ids.append(c["id"]); src.append(c["source"]); titles.append(c["title"]); M.append(v)
    np.savez_compressed(CURVE_INDEX, ids=np.array(ids), source=np.array(src), title=np.array(titles), M=np.array(M))
    curve_index.cache_clear()
    return len(ids)


@lru_cache(maxsize=1)
def curve_index():
    z = np.load(CURVE_INDEX)
    return {"ids": [str(x) for x in z["ids"]], "source": np.array([str(x) for x in z["source"]]),
            "title": [str(x) for x in z["title"]], "M": z["M"]}


# ---------------------------------------------------------------- calibration
@lru_cache(maxsize=1)
def _calib():
    if CALIB.exists():
        return np.array(json.loads(CALIB.read_text())["sorted_distances"])
    return None


def match_pct(d):
    """100 * (1 - percentile of d among random (curve, track) pairs)."""
    cal = _calib()
    if cal is None:
        return None
    p = np.searchsorted(cal, d, side="right") / len(cal)
    return round(100 * (1 - p), 1)


@lru_cache(maxsize=1)
def _penalty():
    if POP.exists():
        return json.loads(POP.read_text())
    return {}


# ---------------------------------------------------------------- search
def match_forward(curve, k=5, exclude=(), use_penalty=True):
    """curve: Curve dict or array of values. -> [(track_id, distance, match_pct), ...]"""
    vals = C.values(curve) if isinstance(curve, dict) else np.asarray(curve, float)
    q = normalise(vals)
    if q is None:
        return []
    lib = library()
    d = dtw_batch(q, lib["M"])
    if use_penalty:
        pen = _penalty()
        if pen:
            d = d + np.array([pen.get(t, 0.0) for t in lib["ids"]])
    order = np.argsort(d)
    out = []
    for i in order:
        if lib["ids"][i] in exclude:
            continue
        out.append((lib["ids"][i], float(d[i]), match_pct(float(d[i]))))
        if len(out) == k:
            break
    return out


def match_reverse(song_curve, sources=None, k=5):
    q = normalise(np.asarray(song_curve, float))
    if q is None:
        return []
    ix = curve_index()
    mask = np.ones(len(ix["ids"]), bool) if not sources else np.isin(ix["source"], list(sources))
    rows = np.where(mask)[0]
    d = dtw_batch(q, ix["M"][rows])
    order = np.argsort(d)[:k]
    return [(ix["ids"][rows[i]], float(d[i]), match_pct(float(d[i]))) for i in order]


# ---------------------------------------------------------------- alignment
def _snap(t, beats, onsets, tol=0.5):
    cands = np.concatenate([beats, onsets]) if len(beats) or len(onsets) else np.zeros(0)
    if len(cands) == 0:
        return t, False
    j = np.argmin(np.abs(cands - t))
    return (float(cands[j]), True) if abs(cands[j] - t) <= tol else (t, False)


def alignment(curve, track_id, window=None):
    """Map each data step to a song second (monotonic), plus a song timestamp for each moment.

    window: optional (start_s, end_s) in song seconds to align against only part of the track.
    """
    lib = library()
    ti = lib["ids"].index(track_id)
    raw, t0 = lib["raw"][ti], float(lib["t0"][ti])
    secs = t0 + np.arange(len(raw), dtype=float)
    if window:
        sel = (secs >= window[0]) & (secs <= window[1])
        raw, secs = raw[sel], secs[sel]
    vals = C.values(curve)
    a, b = normalise(vals), normalise(raw)
    cost, path = dtw_path(a, b)
    pi = np.array([p[0] for p in path], float)
    pj = np.array([p[1] for p in path], float)
    # average song index for each data index, then force monotonic
    song_idx = np.array([pj[pi == i].mean() for i in range(N)])
    song_idx = np.maximum.accumulate(song_idx)
    song_sec_200 = np.interp(song_idx * (len(secs) - 1) / (N - 1), np.arange(len(secs)), secs)
    nsteps = len(vals)
    step_pos = np.arange(nsteps) * (N - 1) / max(1, nsteps - 1)
    step_to_sec = np.interp(step_pos, np.arange(N), song_sec_200)
    step_to_sec = np.maximum.accumulate(step_to_sec)
    moments = []
    for m in curve.get("moments", []):
        t = float(step_to_sec[min(m["t"], nsteps - 1)])
        ts, snapped = _snap(t, lib["beats"][ti], lib["onsets"][ti])
        moments.append({**m, "song_s": round(ts, 2), "snapped": snapped})
    return {"track": track_id, "cost": cost, "step_to_sec": [round(float(x), 2) for x in step_to_sec],
            "moments": moments, "song_curve": [round(float(x), 4) for x in raw], "song_t0": float(secs[0])}
