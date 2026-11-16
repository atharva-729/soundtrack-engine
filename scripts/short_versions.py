"""Short versions + catalog data for every showcase item (run after showcase.py).

For each showcase curve and each length L in (10, 30) seconds:
  * slide an L-second window over every library track (correlation pre-filter, then banded DTW on the
    z-scored shapes, exactly as for full tracks), keep the 3 best distinct tracks
  * snap the cut start to the nearby beat that keeps the best fit, render L seconds (short fades, loudnorm I=-16, metadata stripped)
  * align the whole event to the clip (data step -> clip second) and keep the 2 (10 s) or 3 (30 s) biggest
    moments
Also adds a thumbnail (raw series + tension, 80 points) to every item and writes each item's tension recipe
("explain": raw input -> weighted ingredients -> tension) into site/data/curves/<id>.json.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapters import rain as rain_adapter  # noqa: E402
from adapters import stock as stock_adapter  # noqa: E402
from engine import curves as C  # noqa: E402
from engine import match as M  # noqa: E402
from engine import stitch as S  # noqa: E402

SITE = ROOT / "site"
OUT = SITE / "audio" / "short"
LENGTHS = {10: 2, 30: 3}  # clip length (s) -> number of moments to flag
TOPK = 3
REUSE_PEN = 0.05  # nudge away from tracks already used by another item (either length)
EXPLAIN = {"stock": stock_adapter.explain, "rain": rain_adapter.explain}


def window_cost(q, ti, cs, L):
    """DTW cost of the event against the clip [cs, cs+L], sampled exactly as alignment() samples it."""
    lib = M.library()
    raw, t0 = lib["raw"][ti], float(lib["t0"][ti])
    secs = t0 + np.arange(len(raw))
    b = M.normalise(raw[(secs >= cs) & (secs <= cs + L)])
    return np.inf if b is None else float(M.dtw_batch(q, b[None, :])[0])


def best_windows(vals, L, used):
    """Top distinct tracks for an L-second clip. Each cut start is snapped to whichever nearby beat keeps the
    best fit (1 s matters in a 10 s clip), then candidates are re-ranked on that final cost."""
    lib = M.library()
    q = M.normalise(vals)
    cands = S.candidates(vals, L, step=1 if L <= 10 else 2, per_track=1, topw=40)
    out = []
    for c in cands:
        ti = c["ti"]
        beats, dur = lib["beats"][ti], float(lib["duration"][ti])
        starts = [b for b in beats if abs(b - c["start"]) <= 1.5 and b + L <= dur] or [c["start"]]
        cost, cs = min((window_cost(q, ti, b, L), b) for b in starts)
        out.append({**c, "cut_start": float(cs), "final": cost, "score": cost + (REUSE_PEN if c["track"] in used else 0.0)})
    out.sort(key=lambda c: c["score"])
    return out[:TOPK]


def render(src, cs, L, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    af = f"afade=t=in:d=0.08,loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=out:st={L - 0.7:.2f}:d=0.7,aresample=44100"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{cs:.3f}", "-t", f"{L:.3f}", "-i", str(src),
                    "-af", af, "-map_metadata", "-1", "-ac", "2", "-b:a", "128k", str(out)], check=True)


def pick_moments(c, moments, k, L):
    v = C.values(c)
    ms = sorted(moments, key=lambda m: -v[min(m["t"], len(v) - 1)])
    keep = []
    for m in ms:
        if 0.3 <= m["song_s"] <= L - 0.5 and all(abs(m["song_s"] - x["song_s"]) >= L / 8 for x in keep):
            keep.append(m)
        if len(keep) == k:
            break
    return sorted(keep, key=lambda m: m["song_s"])


def main():
    rows = {r["id"]: r for r in csv.DictReader(open(ROOT / "library" / "tracks.csv", encoding="utf-8"))}
    lib = M.library()
    items = json.loads((SITE / "data" / "showcase.json").read_text(encoding="utf-8"))
    used = set()  # shared across lengths and items
    for f in OUT.glob("*.mp3"):
        f.unlink()
    for it in items:
        c = C.load(ROOT / "curves" / it["source"] / f"{it['id']}.json")
        vals = C.values(c)
        it["short"] = {}
        for L, nm in LENGTHS.items():
            clips = []
            for rank, w in enumerate(best_windows(vals, L, used)):
                tid, ti = w["track"], w["ti"]
                cs = w["cut_start"]
                ce = cs + L
                al = M.alignment(c, tid, window=(cs, ce))
                out = OUT / f"{it['id']}_{L}s_{rank + 1}.mp3"
                render(ROOT / rows[tid]["file"], cs, L, out)
                ms = [{**m, "song_s": round(m["song_s"] - cs, 2)} for m in al["moments"]]
                clips.append({"track": tid, "title": rows[tid]["title"], "credit": rows[tid]["credit"],
                              "genre": rows[tid]["genre"], "feel": rows[tid]["feel"],
                              "cost": round(float(al["cost"]), 4),
                              "cut_start": round(cs, 2), "audio": f"audio/short/{out.name}",
                              "step_to_sec": [round(x - cs, 2) for x in al["step_to_sec"]],
                              "moments": pick_moments(c, ms, nm, L),
                              "song_curve": al["song_curve"], "song_t0": round(al["song_t0"] - cs, 2)})
            used.update(x["track"] for x in clips)
            it["short"][str(L)] = clips
            print(f"{it['id']:28s} {L:2d}s  " + " | ".join(f"{x['title'][:22]} {x['cost']:.3f}" for x in clips))
        aux = np.asarray(c["aux"][it["aux"]], float)
        it["thumb"] = {"aux": [round(float(x), 3) for x in C.resample(aux, 80)],
                       "v": [round(float(x), 3) for x in C.resample(vals, 80)]}
        it["n_steps"] = len(vals)
        c["explain"] = EXPLAIN[it["source"]](c)
        (SITE / "data" / "curves" / f"{it['id']}.json").write_text(json.dumps(c, separators=(",", ":"), ensure_ascii=False),
                                                                   encoding="utf-8")
    (SITE / "data" / "showcase.json").write_text(json.dumps(items, separators=(",", ":")), encoding="utf-8")
    mb = sum(f.stat().st_size for f in OUT.glob("*.mp3")) / 1e6
    print(f"short clips: {len(list(OUT.glob('*.mp3')))} files, {mb:.1f} MB")


if __name__ == "__main__":
    main()
