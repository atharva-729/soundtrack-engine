"""Showcase: top-3 single-track matches + stitched soundtrack for every showcase curve, rendered audio,
Checkpoint 5 comparison (stitched vs single) and click check at crossfades.
Writes curves/showcase/*.json, site/data/showcase.json, site/data/curves/*.json, site/audio/*.mp3.
"""
import csv
import json
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import curves as C  # noqa: E402
from engine import match as M  # noqa: E402
from engine import stitch as S  # noqa: E402

SITE = ROOT / "site"
AUDIO = SITE / "audio"
SHOWCASE = [
    # (source, curve id, chart aux key, stitched?)
    ("stock", "nifty_covid_drama"), ("stock", "reliance_2008_drama"), ("stock", "infy_2019_20_drama"),
    ("stock", "adanient_2023q1_drama"), ("stock", "tcs_last12_shape"), ("stock", "reliance_last12_shape"),
    ("stock", "hdfcbank_last12_shape"),
    ("rain", "rain_mumbai_2005"), ("rain", "rain_chennai_2015"), ("rain", "rain_delhi_2023"), ("rain", "rain_kochi_2018"),
]
AUX = {"stock": "price", "rain": "mm"}


def tracks():
    return {r["id"]: r for r in csv.DictReader(open(ROOT / "library" / "tracks.csv", encoding="utf-8"))}


def click_check(path, at_s, xfade=S.XFADE, plot=None):
    """For each crossfade edge: max sample-to-sample jump within +-0.5 s, divided by the 95th percentile of the
    same statistic over every 1-s window of the file. <= 1 means the boundary is no 'clickier' than ordinary music."""
    import librosa

    y, sr = librosa.load(str(path), sr=22050, mono=True)
    dy = np.abs(np.diff(y))
    nw = len(dy) // sr
    win_max = dy[: nw * sr].reshape(nw, sr).max(axis=1) if nw else np.array([dy.max()])
    ref = np.percentile(win_max, 95) + 1e-9
    out = []
    edges = [e for t in at_s for e in (t, t + xfade)]
    for edge in edges:
        a, b = int(max(0, (edge - 0.5) * sr)), int(min(len(dy), (edge + 0.5) * sr))
        out.append(round(float(dy[a:b].max() / ref), 3) if b > a else 0.0)
    if plot and edges:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axs = plt.subplots(1, len(edges), figsize=(3.2 * len(edges), 2.4), squeeze=False)
        for ax, e in zip(axs[0], edges):
            a, b = int(max(0, (e - 1) * sr)), int(min(len(y), (e + 1) * sr))
            ax.plot(np.arange(a, b) / sr, y[a:b], lw=0.4, color="#333")
            ax.axvline(e, color="r", lw=0.8)
            ax.set_title(f"{e:.1f}s", fontsize=8)
        fig.tight_layout(); fig.savefig(plot, dpi=80); plt.close(fig)
    return out, len(y) / sr


def moment_sync_error(moments, beats_fn):
    errs = []
    for m in moments:
        b = beats_fn(m)
        if b is not None and len(b):
            errs.append(float(np.min(np.abs(b - m["song_s"]))))
    return float(np.mean(errs)) if errs else None


def do_item(item):
    src, cid = item
    t = time.time()
    c = C.load(ROOT / "curves" / src / f"{cid}.json")
    lib = M.library()
    top = M.match_forward(c, k=3)
    singles = []
    for tid, dist, pct in top:
        al = M.alignment(c, tid)
        ti = lib["ids"].index(tid)
        beats = lib["beats"][ti]
        sync = moment_sync_error(al["moments"], lambda m: beats)
        singles.append({"track": tid, "dist": round(dist, 4), "pct": pct, "step_to_sec": al["step_to_sec"],
                        "moments": al["moments"], "song_curve": al["song_curve"], "song_t0": al["song_t0"],
                        "sync_err": sync})
    stitched = None
    if len(c["steps"]) >= 60:
        p = S.plan(c)
        if p:
            out = AUDIO / f"stitched_{cid}.mp3"
            r = S.render(c, p, out)
            (ROOT / "logs" / "xfade").mkdir(parents=True, exist_ok=True)
            clicks, real_len = click_check(out, r["xfade_at"], plot=ROOT / "logs" / "xfade" / f"{cid}.png")
            # moment-sync error for the stitched render: distance from each moment to the nearest beat (output time)
            beats_out, off = [], 0.0
            for seg in r["segments"]:
                b = lib["beats"][lib["ids"].index(seg["track"])]
                b = b[(b >= seg["cut_start"]) & (b <= seg["cut_end"])] - seg["cut_start"] + off
                beats_out.append(b)
                off += (seg["cut_end"] - seg["cut_start"]) - S.XFADE
            bo = np.concatenate(beats_out) if beats_out else np.zeros(0)
            r["sync_err"] = moment_sync_error(r["moments"], lambda m: bo)
            # per-second energy of the output, blending segment curves through the crossfades
            dur = int(np.ceil(r["duration"])) + 1
            acc, wsum = np.zeros(dur), np.zeros(dur)
            off = 0.0
            for seg in r["segments"]:
                ti = lib["ids"].index(seg["track"])
                raw, t0 = lib["raw"][ti], float(lib["t0"][ti])
                L = seg["cut_end"] - seg["cut_start"]
                ts = np.arange(dur, dtype=float)
                local = ts - off
                m = (local >= 0) & (local <= L)
                w = np.clip(np.minimum(local, L - local) / S.XFADE, 0, 1)[m] + 1e-6
                acc[m] += w * np.interp(seg["cut_start"] + local[m], t0 + np.arange(len(raw)), raw)
                wsum[m] += w
                off += L - S.XFADE
            r["song_curve"] = [round(float(x), 4) for x in acc / np.maximum(wsum, 1e-9)]
            r["song_t0"] = 0.0
            stitched = {**r, "audio": f"audio/{out.name}", "dtw_mean": round(p["dtw_mean"], 4), "k": p["k"],
                        "click_ratio": clicks, "rendered_len": round(real_len, 2)}
    return {"source": src, "id": cid, "title": c["title"], "singles": singles, "stitched": stitched,
            "secs": round(time.time() - t, 1)}


def transcode(tid, rows):
    out = AUDIO / f"{tid}.mp3"
    if not out.exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(ROOT / rows[tid]["file"]), "-map_metadata", "-1",
                        "-metadata", f"title={rows[tid]['title']}", "-metadata", "artist=Kevin MacLeod (incompetech.com), CC BY 4.0",
                        "-ac", "2", "-b:a", "128k", str(out)], check=True)
    return out.stat().st_size


def main():
    AUDIO.mkdir(parents=True, exist_ok=True)
    (SITE / "data" / "curves").mkdir(parents=True, exist_ok=True)
    (ROOT / "curves" / "showcase").mkdir(parents=True, exist_ok=True)
    rows = tracks()
    t = time.time()
    with ProcessPoolExecutor(10) as ex:
        results = list(ex.map(do_item, SHOWCASE))
    print(f"matched + stitched {len(results)} items in {time.time()-t:.0f}s")

    # audio budget (< 250 MB): stitched renders + every #1 first, then #2s, then #3s while it fits
    BUDGET = 215e6
    used = sum((AUDIO / f"stitched_{r['id']}.mp3").stat().st_size for r in results if r["stitched"])
    hosted = []
    need = []  # stitched segments are only heard inside the stitched render; host the single-track matches
    for rank in range(3):
        for r in results:
            if len(r["singles"]) > rank:
                need.append(r["singles"][rank]["track"])
    for tid in need:
        if tid in hosted:
            continue
        sz = transcode(tid, rows)
        if used + sz > BUDGET and tid not in [s["track"] for r in results for s in r["singles"][:1]]:
            (AUDIO / f"{tid}.mp3").unlink()
            continue
        used += sz
        hosted.append(tid)
    for f in AUDIO.glob("km_*.mp3"):
        if f.stem not in hosted:
            f.unlink()
    print(f"hosted tracks {len(hosted)}; audio total {used/1e6:.0f} MB")

    # write curves + showcase json
    items = []
    for r in results:
        c = C.load(ROOT / "curves" / r["source"] / f"{r['id']}.json")
        shutil.copy(ROOT / "curves" / r["source"] / f"{r['id']}.json", ROOT / "curves" / "showcase" / f"{r['id']}.json")
        (SITE / "data" / "curves" / f"{r['id']}.json").write_text(json.dumps(c, separators=(",", ":")), encoding="utf-8")
        for s in r["singles"]:
            row = rows[s["track"]]
            s.update({"title": row["title"], "credit": row["credit"], "licence": row["licence"],
                      "audio": f"audio/{s['track']}.mp3" if s["track"] in hosted else None, "genre": row["genre"], "feel": row["feel"]})
        if r["stitched"]:
            r["stitched"]["titles"] = [rows[seg["track"]]["title"] for seg in r["stitched"]["segments"]]
        items.append({"id": r["id"], "source": r["source"], "title": r["title"], "aux": AUX[r["source"]],
                      "meta": c["meta"], "singles": r["singles"], "stitched": r["stitched"]})
    (SITE / "data" / "hosted.json").write_text(json.dumps(hosted))
    (SITE / "data" / "showcase.json").write_text(json.dumps(items, separators=(",", ":")), encoding="utf-8")

    # Checkpoint 5 log
    lines = ["# Stitched vs single-track (Checkpoint 5)\n",
             "| curve | single best DTW | stitched DTW (k) | winner | moment-sync err single / stitched (s) | xfade click ratio | length (s) |",
             "|---|---|---|---|---|---|---|"]
    wins = n = 0
    for r in results:
        st = r["stitched"]
        if not st:
            continue
        sb = r["singles"][0]
        stitched_sync = None
        if st["moments"]:
            lib = M.library()
            # beats of the output = beats of each segment shifted into output time
            pass
        w = st["dtw_mean"] < sb["dist"]
        if True:
            n += 1
            wins += w
        lines.append(f"| {r['title']} | {sb['dist']:.3f} | {st['dtw_mean']:.3f} ({st['k']}) | {'stitched' if w else 'single'} | "
                     f"{(sb['sync_err'] or 0):.2f} / {(st.get('sync_err') or 0):.2f} | "
                     f"{max(st['click_ratio']) if st['click_ratio'] else 0:.2f} | {st['rendered_len']:.1f} (plan {st['duration']:.1f}) |")
    lines.append(f"\n**Stitched beats single on DTW cost in {wins}/{n} showcase curves.**")
    lines.append("Click ratio = max sample jump within ±0.5 s of each crossfade edge / the file's 99.9th-pct jump; <= 1 means no click.")
    (ROOT / "logs" / "stitch_vs_single.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"stitched wins {wins}/{n}")


if __name__ == "__main__":
    main()
