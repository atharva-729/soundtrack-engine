"""The shared Curve type and helpers.

Curve = {
  "id", "source", "title",
  "steps":   [{"t": int, "label": str, "v": float 0..1}, ...],
  "moments": [{"t": int, "label": str, "kind": str}, ...],
  "aux":     {"wp": [...], ...},
  "meta":    {...},
}
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CURVES_DIR = ROOT / "curves"
# which aux series is "the raw data" for each source (charts, scoreboard, reverse-search thumbnails)
AUX_KEY = {"stock": "price", "rain": "mm", "energy": "gw", "machine": "temp", "crop": "yield", "gdp": "gdp"}


def rescale01(x):
    x = np.asarray(x, dtype=float)
    lo, hi = np.nanmin(x), np.nanmax(x)
    if not np.isfinite(lo) or hi - lo < 1e-12:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def ewm(x, alpha):
    x = np.asarray(x, dtype=float)
    out = np.empty_like(x)
    acc = x[0] if len(x) else 0.0
    for i, v in enumerate(x):
        acc = alpha * v + (1 - alpha) * acc if i else v
        out[i] = acc
    return out


def resample(values, n):
    v = np.asarray(values, dtype=float)
    if len(v) == 0:
        return np.zeros(n)
    if len(v) == 1:
        return np.full(n, v[0])
    return np.interp(np.linspace(0, len(v) - 1, n), np.arange(len(v)), v)


def values(curve):
    return np.array([s["v"] for s in curve["steps"]], dtype=float)


def make(cid, source, title, labels, v, moments, aux=None, meta=None):
    v = np.asarray(v, dtype=float)
    return {
        "id": cid,
        "source": source,
        "title": title,
        "steps": [{"t": i, "label": str(labels[i]), "v": round(float(v[i]), 4)} for i in range(len(v))],
        "moments": moments,
        "aux": aux or {},
        "meta": meta or {},
    }


def save(curve, sub=None):
    d = CURVES_DIR / (sub or curve["source"])
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{curve['id']}.json"
    p.write_text(json.dumps(curve, separators=(",", ":")), encoding="utf-8")
    return p


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_all(sources=None):
    out = []
    for d in sorted(CURVES_DIR.iterdir()) if CURVES_DIR.exists() else []:
        if not d.is_dir() or d.name == "showcase":
            continue
        if sources and d.name not in sources:
            continue
        out += [load(p) for p in sorted(d.glob("*.json"))]
    return out


def top_moves(series, k=5, min_gap=1):
    """Indices of the k largest values of `series`, at least min_gap apart."""
    order = np.argsort(-np.asarray(series))
    picked = []
    for i in order:
        if all(abs(int(i) - j) >= min_gap for j in picked):
            picked.append(int(i))
        if len(picked) == k:
            break
    return sorted(picked)
