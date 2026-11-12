"""Checkpoint 4: matcher self-tests, match-% calibration, top-1 reuse (popularity) across all curves.

1. 50 random tracks' own energy curves fed in as data must return that track as #1
2. 20 random data curves fed in reverse must return themselves as #1
3. synthetic shapes (slow build, explosive start, rollercoaster, flat) -> top-3
Also: calibration from 5,000 random (curve, track) pairs; top-1 reuse; popularity penalty if any track > 5%.
"""
import json
import os
import sys
import time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import curves as C  # noqa: E402
from engine import match as M  # noqa: E402

LOGS = ROOT / "logs"


def _top1(i):
    ix = M.curve_index()
    lib = M.library()
    d = M.dtw_batch(ix["M"][i], lib["M"])
    return int(np.argmin(d)), d


def calibration(n=5000, seed=0):
    ix, lib = M.curve_index(), M.library()
    rng = np.random.default_rng(seed)
    ci = rng.integers(0, len(ix["ids"]), n)
    ti = rng.integers(0, len(lib["ids"]), n)
    d = M.dtw_batch(ix["M"][ci], lib["M"][ti])
    d.sort()
    LOGS.mkdir(exist_ok=True)
    M.CALIB.write_text(json.dumps({"n": n, "pairs": "random (data curve, library track)", "N": M.N, "band": M.BAND,
                                   "percentiles": {p: float(np.percentile(d, p)) for p in (1, 5, 25, 50, 75, 95)},
                                   "sorted_distances": [round(float(x), 5) for x in d]}))
    M._calib.cache_clear()
    return d


def popularity():
    ix, lib = M.curve_index(), M.library()
    with Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        res = pool.map(_top1, range(len(ix["ids"])), chunksize=20)
    wins = Counter(lib["ids"][r[0]] for r in res)
    total = len(res)
    share = {t: c / total for t, c in wins.most_common()}
    flagged = {t: s for t, s in share.items() if s > 0.05}
    # small additive penalty, grown iteratively until no track is #1 for more than 5% of curves
    lib_ids = np.array(lib["ids"])
    Dall = np.array([r[1] for r in res])
    pen_arr = np.zeros(len(lib_ids))
    for _ in range(200):
        w = np.bincount(np.argmin(Dall + pen_arr, axis=1), minlength=len(lib_ids)) / total
        over = w > 0.05
        if not over.any():
            break
        pen_arr[over] += 0.2 * (w[over] - 0.05) + 0.002
    penalty = {str(t): round(float(v), 4) for t, v in zip(lib_ids, pen_arr) if v > 0}
    wins2 = Counter(lib_ids[np.argmin(Dall + pen_arr, axis=1)])
    # save every curve's top-5 (with the penalty) for the site's search
    top5 = {}
    for cid, r in zip(ix["ids"], res):
        d = r[1] + pen_arr
        o = np.argsort(d)[:5]
        top5[cid] = [[lib["ids"][j], round(float(r[1][j]), 4)] for j in o]
    (ROOT / "curves" / "forward_top5.json").write_text(json.dumps(top5))
    return total, wins, flagged, penalty, wins2


def main():
    t = time.time()
    n_curves = M.build_curve_index()
    lib = M.library()
    rng = np.random.default_rng(42)
    lines = [f"# Matcher self-test\n\nLibrary: {len(lib['ids'])} tracks · data curves: {n_curves} · N={M.N}, band=±{M.BAND}\n"]

    d = calibration()
    lines.append(f"Calibration: 5,000 random pairs, median distance {np.median(d):.3f}, 5th pct {np.percentile(d, 5):.3f}\n")

    total, wins, flagged, penalty, wins2 = popularity()
    M.POP.write_text(json.dumps(penalty, indent=1))
    M._penalty.cache_clear()
    top = wins.most_common(10)
    lines.append(f"\n## Top-1 reuse across all {total} curves (no penalty)\n")
    lines.append(f"Distinct #1 tracks: {len(wins)} of {len(lib['ids'])}. Most reused:\n")
    lines += [f"- {tid}: {c} ({100*c/total:.1f}%)" for tid, c in top]
    lines.append(f"\nFlagged (> 5%): {', '.join(f'{k} {100*v:.1f}%' for k, v in flagged.items()) or 'none'}")
    if flagged:
        lines.append(f"Popularity penalty applied: {penalty}. After penalty: distinct #1 = {len(wins2)}, "
                     f"max share = {100*wins2.most_common(1)[0][1]/total:.1f}% ({wins2.most_common(1)[0][0]})")

    # 1. own energy curve -> that track
    pick = rng.choice(len(lib["ids"]), size=min(50, len(lib["ids"])), replace=False)
    ok1 = 0
    lines.append("\n## Test 1: track's own energy curve as data (top-3)\n")
    for i in pick:
        res = M.match_forward(lib["raw"][i], k=3)
        hit = res[0][0] == lib["ids"][i]
        ok1 += hit
        lines.append(f"- {'PASS' if hit else 'FAIL'} {lib['ids'][i]} -> " + ", ".join(f"{r[0]} ({r[1]:.3f})" for r in res))
    # 2. data curve in reverse -> itself
    ix = M.curve_index()
    pick2 = rng.choice(len(ix["ids"]), size=20, replace=False)
    ok2 = 0
    lines.append("\n## Test 2: data curve fed in reverse (top-3)\n")
    for i in pick2:
        c = C.load(next((ROOT / "curves").glob(f"*/{ix['ids'][i]}.json")))
        res = M.match_reverse(C.values(c), k=3)
        hit = res[0][0] == ix["ids"][i]
        ok2 += hit
        lines.append(f"- {'PASS' if hit else 'FAIL'} {ix['ids'][i]} -> " + ", ".join(f"{r[0]} ({r[1]:.3f})" for r in res))
    # 3. synthetic shapes
    x = np.linspace(0, 1, 300)
    shapes = {"slow build": x ** 1.5, "explosive start": np.exp(-4 * x), "rollercoaster": 0.5 + 0.5 * np.sin(2 * np.pi * 3 * x),
              "flat": np.full(300, 0.5)}
    lines.append("\n## Test 3: synthetic shapes (top-3)\n")
    rows = {}
    import csv
    for r in csv.DictReader(open(ROOT / "library" / "tracks.csv", encoding="utf-8")):
        rows[r["id"]] = r
    for name, v in shapes.items():
        res = M.match_forward(v, k=3)
        if not res:
            lines.append(f"- {name}: unmatchable (flat curve) - expected")
        else:
            lines.append(f"- {name}: " + ", ".join(f"{rows.get(r[0], {}).get('title', r[0])} ({r[2]}% match)" for r in res))
    lines.insert(1, f"\n**Test 1: {ok1}/{len(pick)} · Test 2: {ok2}/{len(pick2)}** · {time.time()-t:.0f}s\n")
    (LOGS / "selftest.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"test1 {ok1}/{len(pick)} test2 {ok2}/{len(pick2)}; flagged {list(flagged)}; distinct top1 {len(wins)}")


if __name__ == "__main__":
    main()
