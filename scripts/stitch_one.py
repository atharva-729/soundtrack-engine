"""Stitch one soundtrack for one data curve.

    python scripts/stitch_one.py path/to/curve.json out.mp3 [--target 195]

Needs an indexed library (library/tracks.csv + library/curves.npz, built by scripts/index_library.py).
Writes out.mp3 (2-3 track windows crossfaded on beats, loudness-normalised) and out.json:
  segments (track, cut_start, cut_end), step_to_sec (data step -> output second), moments (with output time),
  xfade_at (output seconds where each crossfade starts), credits, duration.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import curves as C  # noqa: E402
from engine import match as M  # noqa: E402
from engine import stitch as S  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("curve")
    ap.add_argument("out")
    ap.add_argument("--target", type=float, default=195, help="target soundtrack length in seconds (150-240 works well)")
    a = ap.parse_args()
    c = C.load(a.curve)
    p = S.plan(c, target_s=a.target)
    if not p:
        sys.exit("no plan: curve too flat or too short")
    r = S.render(c, p, a.out)
    single = M.match_forward(c, k=1)
    r.update({"acts": p["k"], "dtw_mean_stitched": round(p["dtw_mean"], 4),
              "dtw_best_single": round(single[0][1], 4) if single else None})
    Path(a.out).with_suffix(".json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(f"{p['k']} acts -> {a.out} ({r['duration']:.0f}s); stitched DTW {p['dtw_mean']:.3f} vs best single "
          f"{r['dtw_best_single']}")
    for s, cr in zip(r["segments"], r["credits"]):
        print(f"  {s['cut_start']:7.1f}-{s['cut_end']:7.1f}s  {cr}")


if __name__ == "__main__":
    main()
