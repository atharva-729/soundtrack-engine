"""Checkpoint 3: one sanity plot per source + curve counts."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import curves as C  # noqa: E402

PLOTS = [("stock", "nifty_covid_drama", "price"), ("rain", "rain_mumbai_2005", "mm")]
counts = {d.name: len(list(d.glob("*.json"))) for d in (ROOT / "curves").iterdir() if d.is_dir() and d.name != "showcase"}
print("curve counts:", counts)
(ROOT / "logs" / "curve_counts.json").write_text(json.dumps(counts, indent=1))
for src, cid, auxk in PLOTS:
    c = C.load(ROOT / "curves" / src / f"{cid}.json")
    fig, ax = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
    ax[0].plot(c["aux"][auxk], color="#555"); ax[0].set_ylabel(auxk)
    ax[1].plot(C.values(c), color="#d33"); ax[1].set_ylabel("tension 0..1")
    for m in c["moments"]:
        ax[1].axvline(m["t"], color="#999", lw=0.8, ls="--")
    ax[0].set_title(c["title"])
    fig.tight_layout(); fig.savefig(ROOT / "logs" / f"sanity_{src}.png", dpi=90); plt.close(fig)
