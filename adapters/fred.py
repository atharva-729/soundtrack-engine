"""US real GDP, quarterly (FRED series GDPC1, U.S. Bureau of Economic Analysis), 1947 onwards -> gdp Curves.

tension = 0.6 x swings (how far growth is from its usual pace, averaged over 3 quarters, 0..1) + 0.4 x drop from the previous peak,
rescaled 0..1 (the same recipe as the World Bank GDP curves and the stock "drama" curves).
Moments: the 5 biggest quarterly moves.
"""
import csv
import io
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapters.worldbank import explain as _explain, gdp_parts  # noqa: E402
from engine import curves, net  # noqa: E402

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDPC1"
RAW = ROOT / "data" / "fred" / "GDPC1.csv"
CREDIT = "US real GDP (GDPC1): U.S. Bureau of Economic Analysis via FRED, Federal Reserve Bank of St. Louis"
# id, title, first year, last year, showcase (decades with a well-known story, fixed in advance)
WINDOWS = [
    ("gdp_usa_1970_1985", "The US economy through the oil shocks, 1970–1985", 1970, 1985, True),
    ("gdp_usa_2000_2015", "The US economy through the Great Recession, 2000–2015", 2000, 2015, True),
    ("gdp_usa_2015_2025", "The US economy through the COVID shock, 2015–2025", 2015, 2025, True),
]


def load():
    if not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        RAW.write_text(net.get(URL, timeout=60).text, encoding="utf-8")
    rows = [r for r in csv.reader(io.StringIO(RAW.read_text(encoding="utf-8")))][1:]
    return [(r[0], float(r[1])) for r in rows if r[1] not in ("", ".")]


def quarter(d):
    y, m = d[:4], int(d[5:7])
    return f"{y} Q{(m - 1) // 3 + 1}"


def window_curve(rows, cid, title, y0, y1, showcase):
    sel = [(d, v) for d, v in rows if y0 <= int(d[:4]) <= y1]
    if len(sel) < 24:
        return None
    g = np.array([v for _, v in sel])
    labels = [quarter(d) for d, _ in sel]
    # the first quarter's growth needs the quarter before the window
    first = next(i for i, (d, _) in enumerate(rows) if d == sel[0][0])
    swings, dd, growth = gdp_parts(g, avg=3, prev=rows[first - 1][1] if first else None)
    v = curves.rescale01(0.6 * swings + 0.4 * dd)
    moments = [{"t": int(i), "label": f"US GDP {'+' if growth[i] >= 0 else '−'}{abs(growth[i]) * 100:.1f}% in {labels[i]}",
                "kind": "jump" if growth[i] >= 0 else "drop"} for i in curves.top_moves(np.abs(growth), k=5, min_gap=2)]
    aux = {"gdp": [round(float(x), 1) for x in g], "swings": [round(float(x), 4) for x in swings],
           "drop": [round(float(x), 4) for x in dd], "growth": [round(float(x), 4) for x in growth]}
    return curves.make(cid, "gdp", title, labels, v, moments, aux,
                       {"country": "United States", "code": "USA", "freq": "quarterly", "start": labels[0], "end": labels[-1],
                        "showcase": showcase, "credit": CREDIT})


def explain(c):
    e = _explain(c)
    e["parts"][0]["help"] = "how far growth is from its usual pace, averaged over 3 quarters (0–1)"
    return e


def main():
    rows = load()
    made = [window_curve(rows, *w) for w in WINDOWS]
    # rolling 15-year windows every 5 years, for reverse-search variety
    last = int(rows[-1][0][:4])
    for y0 in range(1950, last - 9, 5):
        made.append(window_curve(rows, f"gdp_usa_{y0}_{min(last, y0 + 14)}", f"The US economy, {y0}–{min(last, y0 + 14)}",
                                 y0, y0 + 14, False))
    made = [c for c in made if c]
    for c in made:
        curves.save(c)
    print("fred gdp curves:", len(made), "| showcase:", [c["id"] for c in made if c["meta"]["showcase"]])


if __name__ == "__main__":
    main()
