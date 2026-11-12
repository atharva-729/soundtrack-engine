"""Blind listening test material: for every showcase curve, a 40-s clip of the engine's best-matching window
(aligned with banded DTW) and a 40-s clip of a random library track window with similar overall loudness
(engine top-10 excluded; played with plain linear timing). Writes site/data/test_trials.json + site/audio/test/*.mp3.
"""
import csv
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import curves as C  # noqa: E402
from engine import match as M  # noqa: E402
from engine import stitch as S  # noqa: E402

CLIP = 40
OUT = ROOT / "site" / "audio" / "test"
AUXK = {"stock": "price", "rain": "mm"}


def cut(src, start, dst):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", str(CLIP), "-i", str(src),
                    "-af", f"afade=t=in:d=0.6,afade=t=out:st={CLIP-1.2}:d=1.2,loudnorm=I=-16:TP=-1.5", "-ac", "2",
                    "-map_metadata", "-1", "-b:a", "128k", str(dst)], check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = {r["id"]: r for r in csv.DictReader(open(ROOT / "library" / "tracks.csv", encoding="utf-8"))}
    showcase = json.loads((ROOT / "site" / "data" / "showcase.json").read_text(encoding="utf-8"))
    lib = M.library()
    rng = np.random.default_rng(2026)
    trials, jobs = [], []
    for it in showcase:
        c = C.load(ROOT / "curves" / it["source"] / f"{it['id']}.json")
        vals = C.values(c)
        cands = S.candidates(vals, CLIP, topw=40)
        best = min(cands, key=lambda x: x["cost"])
        al = M.alignment(c, best["track"], window=(best["start"], best["end"]))
        eng_map = [round(s - best["start"], 2) for s in al["step_to_sec"]]
        # foil: random track not in the engine's top-10, window with similar mean energy
        top10 = {t for t, _, _ in M.match_forward(c, k=10)} | {best["track"]}
        target = best["mean_e"]
        foil = None
        for _ in range(4000):
            ti = int(rng.integers(len(lib["ids"])))
            raw = lib["raw"][ti]
            if lib["ids"][ti] in top10 or len(raw) < CLIP + 2:
                continue
            s0 = int(rng.integers(0, len(raw) - CLIP))
            if abs(raw[s0: s0 + CLIP].mean() - target) < 0.03:
                foil = (ti, float(lib["t0"][ti]) + s0, raw[s0: s0 + CLIP])
                break
        if foil is None:
            continue
        ti, fstart, fraw = foil
        ftid = lib["ids"][ti]
        n = len(vals)
        lin_map = [round(CLIP * i / max(1, n - 1), 2) for i in range(n)]
        e_name, f_name = f"{it['id']}_engine.mp3", f"{it['id']}_random.mp3"
        jobs += [(ROOT / rows[best["track"]]["file"], best["start"], OUT / e_name),
                 (ROOT / rows[ftid]["file"], fstart, OUT / f_name)]
        trials.append({"id": it["id"], "source": it["source"], "aux_kind": AUXK[it["source"]],
                       "aux": c["aux"][AUXK[it["source"]]], "tension": [round(float(v), 3) for v in vals],
                       "engine": {"audio": f"audio/test/{e_name}", "map": eng_map, "track": best["track"],
                                  "credit": rows[best["track"]]["credit"], "dtw": round(best["cost"], 4)},
                       "random": {"audio": f"audio/test/{f_name}", "map": lin_map, "track": ftid,
                                  "credit": rows[ftid]["credit"]}})
    with ThreadPoolExecutor(10) as ex:
        list(ex.map(lambda j: cut(*j), jobs))
    (ROOT / "site" / "data" / "test_trials.json").write_text(json.dumps(trials, separators=(",", ":")), encoding="utf-8")
    mb = sum(f.stat().st_size for f in OUT.glob("*.mp3")) / 1e6
    print(f"{len(trials)} trial curves, {len(jobs)} clips, {mb:.1f} MB")


if __name__ == "__main__":
    main()
