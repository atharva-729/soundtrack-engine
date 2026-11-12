"""Stitched soundtracks: split a long data curve into 1-3 acts and give each act its own track window.

1. acts: DP split of the smoothed curve minimising within-act variance; every act >= 25% of the curve
2. per act: correlation pre-filter over every >= 40 s window of every track -> top 30 -> banded DTW
3. DP over acts x candidates with transition costs (energy mismatch at the cut, loud cuts, tempo jump > 25%,
   reusing a track, and keeping the acts' relative intensity)
4. render: cut on beats near the boundaries (quietest nearby beat), 3.5 s acrossfade, loudnorm I=-16
"""
import subprocess
from pathlib import Path

import numpy as np

from . import curves as C
from . import match as M

ROOT = Path(__file__).resolve().parents[1]
XFADE = 3.5
MIN_WIN = 40
TOPW = 30
PRE_N = 64


# ---------------------------------------------------------------- acts
def split_acts(v, k, min_frac=0.25):
    """Best split of v into k contiguous acts (min within-act SSE), each >= min_frac of len(v). Returns boundaries."""
    n = len(v)
    mn = int(np.ceil(min_frac * n))
    cs, cs2 = np.concatenate([[0], np.cumsum(v)]), np.concatenate([[0], np.cumsum(v * v)])

    def sse(a, b):
        m = b - a
        s = cs[b] - cs[a]
        return (cs2[b] - cs2[a]) - s * s / m

    if k == 1:
        return [0, n], sse(0, n)
    best = (np.inf, None)
    if k == 2:
        for b in range(mn, n - mn + 1):
            c = sse(0, b) + sse(b, n)
            if c < best[0]:
                best = (c, [0, b, n])
    else:
        for b1 in range(mn, n - 2 * mn + 1):
            for b2 in range(b1 + mn, n - mn + 1):
                c = sse(0, b1) + sse(b1, b2) + sse(b2, n)
                if c < best[0]:
                    best = (c, [0, b1, b2, n])
    return best[1], best[0]


# ---------------------------------------------------------------- candidates
def _resample_rows(W, n):
    p = np.linspace(0, W.shape[1] - 1, n)
    i0 = np.floor(p).astype(int)
    i1 = np.minimum(i0 + 1, W.shape[1] - 1)
    f = p - i0
    return W[:, i0] * (1 - f) + W[:, i1] * f


def _z(X):
    X = X - X.mean(axis=-1, keepdims=True)
    sd = X.std(axis=-1, keepdims=True)
    return X / np.where(sd < 1e-6, np.inf, sd)


def candidates(act_vals, win_s, step=4, per_track=2, topw=TOPW):
    """Top windows for one act: [(track_idx, start_s, end_s, dtw_cost, mean_energy)]"""
    lib = M.library()
    q64 = _z(C.resample(act_vals, PRE_N)[None, :])[0]
    scored = []
    for ti, raw in enumerate(lib["raw"]):
        if len(raw) < win_s:
            continue
        Wv = np.lib.stride_tricks.sliding_window_view(raw, win_s)[::step]
        Z = _z(_resample_rows(Wv, PRE_N))
        corr = Z @ q64 / PRE_N
        best = np.argsort(-corr)[:per_track]
        for b in best:
            scored.append((corr[b], ti, int(b * step)))
    scored.sort(key=lambda x: -x[0])
    top = scored[:topw]
    q = M.normalise(act_vals)
    out = []
    if q is None:
        return out
    B = np.array([M.normalise(lib["raw"][ti][s: s + win_s]) for _, ti, s in top])
    d = M.dtw_batch(q, B)
    for (corr, ti, s), dd in zip(top, d):
        t0 = float(lib["t0"][ti])
        raw = lib["raw"][ti]
        out.append({"ti": ti, "track": lib["ids"][ti], "start": t0 + s, "end": t0 + s + win_s, "cost": float(dd),
                    "corr": float(corr), "mean_e": float(raw[s: s + win_s].mean()),
                    "e_start": float(raw[s: s + 3].mean()), "e_end": float(raw[s + win_s - 3: s + win_s].mean())})
    return out


# ---------------------------------------------------------------- plan
def _trans_cost(a, b, act_a, act_b):
    lib = M.library()
    cost = 0.0
    lo, hi = 0.35, 0.85  # typical energy range
    ea, eb = a["e_end"], b["e_start"]
    cost += 1.0 * abs(ea - eb) / (hi - lo)            # energy mismatch at the cut
    cost += 0.5 * max(0.0, max(ea, eb) - 0.7) / 0.15  # avoid crossfading inside loud passages
    ta, tb = lib["tempo"][a["ti"]], lib["tempo"][b["ti"]]
    if ta > 0 and tb > 0 and abs(ta - tb) / min(ta, tb) > 0.25:
        cost += 0.3
    if a["track"] == b["track"]:
        cost += 5.0
    # keep relative intensity: if the data gets more intense in act b, the music should too
    dv = act_b.mean() - act_a.mean()
    de = b["mean_e"] - a["mean_e"]
    if abs(dv) > 0.05 and np.sign(dv) != np.sign(de):
        cost += 0.3 * min(1.0, abs(dv) / 0.2)
    return cost


def plan(curve, target_s=195, k_options=(2, 3), trans_weight=0.15):
    vals = C.values(curve)
    sm = C.ewm(vals, 0.1)
    best = None
    for k in k_options:
        bounds, _ = split_acts(sm, k)
        if bounds is None:
            continue
        acts = [vals[bounds[i]: bounds[i + 1]] for i in range(k)]
        fracs = [len(a) / len(vals) for a in acts]
        # every act gets its share of the target, plus the crossfade overlap; at least MIN_WIN s
        wins = [max(MIN_WIN, int(round(target_s * f + (XFADE if 0 < i < k - 1 else XFADE / 2)))) for i, f in enumerate(fracs)]
        cands = [candidates(a, w) for a, w in zip(acts, wins)]
        if any(len(c) == 0 for c in cands):
            continue
        # DP over acts
        prev = [(c["cost"] * fracs[0], [j]) for j, c in enumerate(cands[0])]
        for i in range(1, k):
            cur = []
            for j, c in enumerate(cands[i]):
                opts = [(pc + trans_weight * _trans_cost(cands[i - 1][path[-1]], c, acts[i - 1], acts[i])
                         + (5.0 if any(cands[ii][jj]["track"] == c["track"] for ii, jj in enumerate(path)) else 0.0), path)
                        for pc, path in prev]  # no track may be reused by any earlier act
                pc, path = min(opts, key=lambda x: x[0])
                cur.append((pc + c["cost"] * fracs[i], path + [j]))
            prev = cur
        total, path = min(prev, key=lambda x: x[0])
        chosen = [cands[i][j] for i, j in enumerate(path)]
        dtw_mean = sum(ch["cost"] * f for ch, f in zip(chosen, fracs))
        if best is None or total < best["objective"]:
            best = {"k": k, "bounds": bounds, "fracs": fracs, "windows": chosen, "objective": total,
                    "dtw_mean": dtw_mean}
    return best


# ---------------------------------------------------------------- render
def _quiet_beat_near(ti, t, lo, hi, prefer="any"):
    """A beat in [lo, hi] near t with low energy (avoid cutting inside loud passages)."""
    lib = M.library()
    beats = lib["beats"][ti]
    raw, t0 = lib["raw"][ti], float(lib["t0"][ti])
    cand = beats[(beats >= lo) & (beats <= hi)]
    if len(cand) == 0:
        return float(np.clip(t, lo, hi))
    e = np.interp(cand, t0 + np.arange(len(raw)), raw)
    score = np.abs(cand - t) / 4.0 + (e - e.min()) / max(1e-6, np.ptp(e) or 1)
    return float(cand[np.argmin(score)])


def render(curve, p, out_path, ffmpeg="ffmpeg"):
    """Cut windows on beats, crossfade, loudness-normalise. Returns the combined alignment + credits."""
    import csv

    lib = M.library()
    rows = {r["id"]: r for r in csv.DictReader(open(ROOT / "library" / "tracks.csv", encoding="utf-8"))}
    segs = []
    k = len(p["windows"])
    for i, w in enumerate(p["windows"]):
        ti = w["ti"]
        dur = float(lib["duration"][ti])
        start = w["start"] if i == 0 else _quiet_beat_near(ti, w["start"], max(0, w["start"] - 4), w["start"] + 4)
        end = w["end"] if i == k - 1 else _quiet_beat_near(ti, w["end"], w["end"] - 4, min(dur, w["end"] + 4))
        if i == 0:
            start = _quiet_beat_near(ti, start, max(0, start - 2), start + 2)
        segs.append({**w, "cut_start": round(start, 3), "cut_end": round(min(end, dur), 3)})

    ins, filt = [], []
    for i, s in enumerate(segs):
        ins += ["-ss", f"{s['cut_start']:.3f}", "-to", f"{s['cut_end']:.3f}", "-i", str(ROOT / rows[s["track"]]["file"])]
        filt.append(f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo,afade=t=in:d=0.02[a{i}]")
    last = "a0"
    for i in range(1, k):
        nm = f"x{i}"
        filt.append(f"[{last}][a{i}]acrossfade=d={XFADE}:c1=tri:c2=tri[{nm}]")
        last = nm
    filt.append(f"[{last}]loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=out:st=0:d=0.01[out]")
    # final short fade-out at the end
    total = sum(s["cut_end"] - s["cut_start"] for s in segs) - XFADE * (k - 1)
    filt[-1] = f"[{last}]loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=out:st={max(0, total - 1.5):.2f}:d=1.5,aresample=44100[out]"
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg, "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(filt), "-map", "[out]", "-map_metadata", "-1",
           "-ac", "2", "-b:a", "128k", str(out_path)]
    subprocess.run(cmd, check=True)

    # combined alignment: data step -> output second
    vals = C.values(curve)
    step_to_sec = np.zeros(len(vals))
    moments = []
    offset = 0.0
    bounds = p["bounds"]
    for i, s in enumerate(segs):
        a, b = bounds[i], bounds[i + 1]
        act = {"steps": curve["steps"][a:b], "moments": [{**m, "t": m["t"] - a} for m in curve["moments"] if a <= m["t"] < b]}
        al = M.alignment(act, s["track"], window=(s["cut_start"], s["cut_end"]))
        local = np.array(al["step_to_sec"]) - s["cut_start"] + offset
        step_to_sec[a:b] = local
        for m in al["moments"]:
            moments.append({**m, "t": m["t"] + a, "song_s": round(m["song_s"] - s["cut_start"] + offset, 2),
                            "track": s["track"]})
        offset += (s["cut_end"] - s["cut_start"]) - XFADE
    step_to_sec = np.maximum.accumulate(step_to_sec)
    credits = [rows[s["track"]]["credit"] for s in segs]
    boundaries_out = []
    off = 0.0
    for s in segs[:-1]:
        off += (s["cut_end"] - s["cut_start"]) - XFADE
        boundaries_out.append(round(off, 2))  # crossfade spans [off, off + XFADE]
    return {"segments": [{k2: s[k2] for k2 in ("track", "cut_start", "cut_end", "cost")} for s in segs],
            "step_to_sec": [round(float(x), 2) for x in step_to_sec], "moments": moments, "credits": credits,
            "xfade_at": boundaries_out, "duration": round(total, 2), "bounds": bounds}
