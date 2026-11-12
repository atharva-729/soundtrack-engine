"""Export site data: int8 curve index for in-browser reverse search, aux charts, calibration,
hosted-track energy curves (for in-browser alignment), library titles + credits."""
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import curves as C  # noqa: E402
from engine import match as M  # noqa: E402

D = ROOT / "site" / "data"
AUXK = {"stock": "price", "rain": "mm"}


def main():
    D.mkdir(parents=True, exist_ok=True)
    ix = M.curve_index()
    ids = ix["ids"]
    n = len(ids)
    q = np.round(np.clip(ix["M"], -4, 4) * 31.75).astype(np.int8)
    q.tofile(D / "index.bin")

    aux = np.zeros((n, M.N), np.uint8)
    meta = {"N": M.N, "band": M.BAND, "ids": ids, "title": ix["title"], "source": list(ix["source"]),
            "aux_kind": [], "aux_min": [], "aux_max": [], "moments": [], "steps": [], "date": []}
    paths = {p.stem: p for p in (ROOT / "curves").glob("*/*.json") if p.parent.name != "showcase"}
    for i, cid in enumerate(ids):
        c = C.load(paths[cid])
        k = AUXK[c["source"]]
        a = np.asarray(c["aux"][k], float)
        lo, hi = float(a.min()), float(a.max())
        aux[i] = np.round(255 * (C.resample(a, M.N) - lo) / ((hi - lo) or 1)).astype(np.uint8)
        ns = len(c["steps"])
        meta["aux_kind"].append(k); meta["aux_min"].append(round(lo, 3)); meta["aux_max"].append(round(hi, 3))
        meta["steps"].append(ns)
        meta["date"].append(c["meta"].get("date") or c["meta"].get("start") or "")
        meta["moments"].append([[round(m["t"] / max(1, ns - 1), 4), m["label"][:110]] for m in c["moments"][:5]])
    aux.tofile(D / "auxseries.bin")
    (D / "index_meta.json").write_text(json.dumps(meta, separators=(",", ":")), encoding="utf-8")

    cal = np.array(json.loads(M.CALIB.read_text())["sorted_distances"])
    (D / "calib.json").write_text(json.dumps([round(float(x), 5) for x in np.quantile(cal, np.linspace(0, 1, 201))]))

    rows = {r["id"]: r for r in csv.DictReader(open(ROOT / "library" / "tracks.csv", encoding="utf-8"))}
    (D / "library.json").write_text(json.dumps({t: [r["title"], r["credit"], r["genre"], r["feel"]] for t, r in rows.items()},
                                               separators=(",", ":")), encoding="utf-8")

    hosted = json.loads((D / "hosted.json").read_text())
    lib = M.library()
    hl = []
    for tid in hosted:
        i = lib["ids"].index(tid)
        hl.append({"id": tid, "audio": f"audio/{tid}.mp3", "t0": round(float(lib["t0"][i]), 3),
                   "curve": [round(float(x), 4) for x in lib["raw"][i]],
                   "beats": [round(float(x), 2) for x in lib["beats"][i]]})
    (D / "hosted_lib.json").write_text(json.dumps(hl, separators=(",", ":")))

    sizes = {f.name: round(f.stat().st_size / 1e6, 2) for f in D.glob("*.*")}
    print("site data (MB):", sizes)


if __name__ == "__main__":
    main()
