"""Compute an energy curve (1 point / second), tempo, beats and onsets for every track in tracks.csv
-> library/curves.npz. Parallel over CPU cores; per-track results cached in library/cache/ so reruns are incremental.
"""
import csv
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import energy  # noqa: E402

CACHE = ROOT / "library" / "cache"
OUT = ROOT / "library" / "curves.npz"


def process(row):
    tid, rel = row["id"], row["file"]
    cp = CACHE / f"{tid}.npz"
    if cp.exists():
        return tid, True
    try:
        y = energy.load_audio(ROOT / rel)
        times, e = energy.energy_from_signal(y)
        t0, ps = energy.per_second(times, e)
        tempo, beats, onsets = energy.rhythm(y)
        np.savez_compressed(cp, curve=ps.astype(np.float32), t0=t0, duration=len(y) / energy.SR, tempo=tempo,
                            beats=beats.astype(np.float32), onsets=onsets.astype(np.float32),
                            frame_e=e.astype(np.float32), frame_t=times.astype(np.float32))
        return tid, True
    except Exception as ex:
        return tid, f"{type(ex).__name__}: {ex}"


def pack(ids):
    cur, beats, ons = [], [], []
    t0, dur, tempo = [], [], []
    for tid in ids:
        z = np.load(CACHE / f"{tid}.npz")
        cur.append(z["curve"]); beats.append(z["beats"]); ons.append(z["onsets"])
        t0.append(float(z["t0"])); dur.append(float(z["duration"])); tempo.append(float(z["tempo"]))

    def flat(lst):
        off = np.cumsum([0] + [len(x) for x in lst])
        return (np.concatenate(lst) if lst else np.zeros(0)).astype(np.float32), off.astype(np.int64)

    c, co = flat(cur); b, bo = flat(beats); o, oo = flat(ons)
    np.savez_compressed(OUT, ids=np.array(ids), curve=c, curve_off=co, beats=b, beats_off=bo, onsets=o, onsets_off=oo,
                        t0=np.array(t0), duration=np.array(dur), tempo=np.array(tempo))


if __name__ == "__main__":
    CACHE.mkdir(parents=True, exist_ok=True)
    with open(ROOT / "library" / "tracks.csv", newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("licence") and r.get("credit") and (ROOT / r["file"]).exists()]
    t = time.time()
    ok, bad = [], []
    with Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        for i, (tid, res) in enumerate(pool.imap_unordered(process, rows, chunksize=2), 1):
            (ok if res is True else bad).append((tid, res))
            if i % 50 == 0:
                print(f"{i}/{len(rows)}  {time.time()-t:.0f}s", flush=True)
    ids = sorted(t for t, _ in ok)
    pack(ids)
    print(f"indexed {len(ids)} tracks in {time.time()-t:.0f}s; failed {len(bad)}")
    for tid, err in bad:
        print("  FAIL", tid, err)
