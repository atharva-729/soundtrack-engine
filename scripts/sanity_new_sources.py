"""Sanity plot: raw series + tension for every showcase curve of the energy, machine, crop and gdp sources."""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import curves as C  # noqa: E402

AUX = {"energy": "gw", "machine": "temp", "crop": "yield", "gdp": "gdp"}


def main():
    items = [c for c in C.load_all(list(AUX)) if c["meta"].get("showcase")]
    fig, axs = plt.subplots(len(items), 1, figsize=(10, 2.0 * len(items)), squeeze=False)
    for ax, c in zip(axs[:, 0], items):
        raw = c["aux"][AUX[c["source"]]]
        ax.plot(raw, color="#333", lw=1)
        ax2 = ax.twinx()
        ax2.fill_between(range(len(c["steps"])), [s["v"] for s in c["steps"]], color="#0077b6", alpha=.25)
        for m in c["moments"]:
            ax.axvline(m["t"], color="#d81b60", lw=.8)
        ax.set_title(f"{c['title']}  ({len(c['steps'])} steps)", fontsize=9)
    fig.tight_layout()
    out = ROOT / "logs" / "sanity_new_sources.png"
    fig.savefig(out, dpi=70)
    print(out, len(items))


if __name__ == "__main__":
    main()
