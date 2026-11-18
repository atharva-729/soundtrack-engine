"""Short versions + catalog data for every showcase item (run after showcase.py).

For each showcase curve:
  * 30 s: slide a 30-second window over every library track (correlation pre-filter, then banded DTW on the
    z-scored shapes, exactly as for full tracks), keep the 3 best distinct tracks; snap the cut start to the
    nearby beat that keeps the best fit; align the whole event to the clip and keep its 3 biggest moments
  * 10 s: NOT searched separately (on a 10 s scale the loudness-based energy rarely matches what sounds
    dramatic). Each 10 s clip is the dramatic part of the matching 30 s clip: same track, cut around the point
    where the event's biggest moment lands, framed by the music itself (see dramatic_cut). The player shows the
    section of the event that this cut plays in the 30 s version.
Render: short fades, loudnorm I=-16, metadata stripped.
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
from adapters import energy, fred, machine, worldbank  # noqa: E402
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
EXPLAIN = {"stock": stock_adapter.explain, "rain": rain_adapter.explain, "energy": energy.explain,
           "machine": machine.explain, "crop": worldbank.explain,
           "gdp": lambda c: (fred.explain if c["meta"].get("freq") == "quarterly" else worldbank.explain)(c)}


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


HIT_AT = 6.0          # preferred second of the 10 s cut where the big moment lands (more build-up than release)
HIT_RANGE = (3.5, 7.5)  # allowed range for it (>= 2.5 s of aftermath before the fade-out)


def drama_step(c, vals):
    """The moment the event is about: its highest-tension labelled moment (e.g. the crash, the failure),
    else the highest-tension step."""
    ms = [m for m in c.get("moments", []) if 0 <= m["t"] < len(vals)]
    return max(ms, key=lambda m: vals[m["t"]])["t"] if ms else int(np.argmax(vals))


def frame_energy(tid):
    """Fine-grained music energy (one value per ~46 ms, from the index cache), smoothed over ~0.5 s."""
    z = np.load(ROOT / "library" / "cache" / f"{tid}.npz")
    e, t = z["frame_e"].astype(float), z["frame_t"].astype(float)
    k = max(1, int(round(0.5 / float(np.median(np.diff(t))))))
    return t, np.convolve(e, np.ones(k) / k, mode="same")


def dramatic_cut(tid, ti, cs30, peak_s, L=10):
    """Start of the 10 s cut inside the 30 s clip [cs30, cs30 + 30]. Candidates: beats that put the big moment
    (peak_s) between HIT_RANGE seconds into the cut. Each is scored on the music itself, scaled by the 30 s
    clip's energy range:
      hit    how far the music near the moment (+-0.75 s) stands above the cut's typical level
      build  how much it rises from the cut's first 2 s into the moment
      - distance from the moment to the loudest point of the cut, and from the moment to HIT_AT
      - a start in near-silence
    Returns (cut_start, details)."""
    lib = M.library()
    t, e = frame_energy(tid)
    clip = (t >= cs30) & (t <= cs30 + 30)
    lo_e, hi_e = np.percentile(e[clip], 5), np.percentile(e[clip], 95)
    rng = max(hi_e - lo_e, 1e-6)
    lo, hi = cs30, cs30 + 30 - L
    beats = [float(b) for b in lib["beats"][ti]
             if lo <= b <= hi and HIT_RANGE[0] <= peak_s - b <= HIT_RANGE[1]]
    if not beats:  # the moment sits near an edge of the 30 s clip: take the closest legal cut
        beats = [min(max(peak_s - HIT_AT, lo), hi)]
    best = None
    for b in beats:
        w = (t >= b) & (t <= b + L)
        ew, tw = e[w], t[w]
        if len(ew) < 10:
            continue
        near = np.abs(tw - peak_s) <= 0.75
        e_hit = ew[near].max() if near.any() else ew[np.argmin(np.abs(tw - peak_s))]
        hit = (e_hit - np.median(ew)) / rng
        build = (e_hit - ew[tw <= b + 2].mean()) / rng
        dist = abs(tw[np.argmax(ew)] - peak_s) / L
        pos = abs((peak_s - b) - HIT_AT) / L
        silent = 0.5 if ew[tw <= b + 1].mean() < lo_e else 0.0
        score = hit + 0.5 * build - 0.5 * dist - 0.3 * pos - silent
        if best is None or score > best[0]:
            best = (score, b, {"hit": round(float(hit), 2), "build": round(float(build), 2),
                              "loudest_off_s": round(float(dist * L), 1)})
    return (float(best[1]), best[2]) if best else (float(beats[0]), {})


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
        p = drama_step(c, vals)

        def clip_row(tid, cs, L, rank, al, extra=None):
            """al: alignment of the whole event to the 30 s clip (absolute song seconds); shifted to the cut."""
            out = OUT / f"{it['id']}_{L}s_{rank + 1}.mp3"
            render(ROOT / rows[tid]["file"], cs, L, out)
            ms = [{**m, "song_s": round(m["song_s"] - cs, 2)} for m in al["moments"]]
            return {"track": tid, "title": rows[tid]["title"], "credit": rows[tid]["credit"],
                    "genre": rows[tid]["genre"], "feel": rows[tid]["feel"],
                    "cost": round(float(al["cost"]), 4),
                    "cut_start": round(cs, 2), "audio": f"audio/short/{out.name}",
                    # for the 10 s cut, steps outside it fall before 0 / after 10 s: the player draws only the
                    # section of the event that this cut plays
                    "step_to_sec": [round(x - cs, 2) for x in al["step_to_sec"]],
                    "moments": pick_moments(c, ms, LENGTHS[L], L),
                    "song_curve": al["song_curve"], "song_t0": round(al["song_t0"] - cs, 2), **(extra or {})}

        c30, c10 = [], []
        for rank, w in enumerate(best_windows(vals, 30, used)):
            tid, ti, cs30 = w["track"], w["ti"], w["cut_start"]
            al = M.alignment(c, tid, window=(cs30, cs30 + 30))
            c30.append(clip_row(tid, cs30, 30, rank, al))
            peak_s = al["step_to_sec"][p]  # where the big moment lands in the 30 s clip (absolute seconds)
            cs10, why = dramatic_cut(tid, ti, cs30, peak_s)
            c10.append(clip_row(tid, cs10, 10, rank, al, {"from30": True, "hit_s": round(peak_s - cs10, 2),
                                                          "drama": why}))
        used.update(x["track"] for x in c30)
        it["short"] = {"10": c10, "30": c30}
        print(f"{it['id']:28s} 30s  " + " | ".join(f"{x['title'][:22]} {x['cost']:.3f}" for x in c30))
        print(f"{'':28s} 10s  " + " | ".join(f"@{x['cut_start'] - y['cut_start']:4.1f}s hit {x['hit_s']:.1f}s {x['drama']}"
                                            for x, y in zip(c10, c30)))
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
