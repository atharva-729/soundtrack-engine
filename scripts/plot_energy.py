"""Checkpoint 2: plot 6 energy curves (strongest steady build, steadiest high, biggest late drop, + 3 random)."""
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import curves as C  # noqa: E402

z = np.load(ROOT / "library" / "curves.npz")
ids = [str(x) for x in z["ids"]]
off = z["curve_off"]
raw = [z["curve"][off[i]: off[i + 1]] for i in range(len(ids))]
titles = {r["id"]: r["title"] for r in csv.DictReader(open(ROOT / "library" / "tracks.csv", encoding="utf-8"))}
x = np.linspace(0, 1, 100)
R = np.array([C.resample(r, 100) for r in raw])
build = int(np.argmax([np.corrcoef(r, x)[0, 1] * (r[80:95].mean() - r[5:20].mean()) for r in R]))
sc = R.mean(1) - 3 * R.std(1); sc[build] = -9; steady = int(np.argmax(sc))
drop = int(np.argmax([r[:80].mean() - r[85:].mean() for r in R]))
rng = np.random.default_rng(5)
pick = [(build, "steady build (like Mountain King)"), (steady, "high throughout (like Valkyries)"),
        (drop, "big late drop")] + [(int(i), "random") for i in rng.choice(len(ids), 3, replace=False)]
fig, axs = plt.subplots(3, 2, figsize=(11, 7))
for ax, (i, why) in zip(axs.flat, pick):
    ax.plot(z["t0"][i] + np.arange(len(raw[i])), raw[i], color="#1a7")
    ax.set_title(f"{titles.get(ids[i], ids[i])}: {why}", fontsize=9)
    ax.set_ylim(0, 1)
fig.supxlabel("seconds"); fig.supylabel("energy")
fig.tight_layout(); fig.savefig(ROOT / "logs" / "energy_samples.png", dpi=85)
print([titles.get(ids[i]) for i, _ in pick])
