"""World Bank open data (CC BY 4.0): cereal yield (crop) and real GDP (gdp), one value per year, 1961 onwards.

crop: tension = 0.7 x shortfall below the best yield of the previous 5 years + 0.3 x size of the year-on-year
      change, rescaled 0..1. Droughts and failed harvests spike.
gdp:  tension = 0.6 x swings (how far growth is from its usual pace, 0..1) + 0.4 x drop from the previous peak,
      rescaled 0..1 (the same idea as the stock "drama" curves; "usual pace" = median growth of the period, so a
      fast-growing economy is not "tense" just for growing fast).
Moments: the 5 biggest year-on-year moves.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import curves, net  # noqa: E402

API = "https://api.worldbank.org/v2/country/{c}/indicator/{ind}"
RAW = ROOT / "data" / "worldbank"
CREDIT = "World Bank Open Data (CC BY 4.0): {what}"
IND = {"crop": ("AG.YLD.CREL.KG", "cereal yield, kg per hectare (FAO)"), "gdp": ("NY.GDP.MKTP.KD", "GDP, constant US$")}
COUNTRIES = {"IND": "India", "AUS": "Australia", "USA": "United States", "CHN": "China", "BRA": "Brazil", "RUS": "Russia",
             "ARG": "Argentina", "ZAF": "South Africa", "ETH": "Ethiopia", "KEN": "Kenya", "PAK": "Pakistan",
             "BGD": "Bangladesh", "IDN": "Indonesia", "NGA": "Nigeria", "EGY": "Egypt", "MEX": "Mexico", "FRA": "France",
             "DEU": "Germany", "GBR": "United Kingdom", "JPN": "Japan", "KOR": "South Korea", "TUR": "Turkey",
             "UKR": "Ukraine", "CAN": "Canada", "THA": "Thailand", "VNM": "Vietnam", "GRC": "Greece", "IRN": "Iran",
             "SAU": "Saudi Arabia", "CHL": "Chile"}
SHOW = {"crop": ["IND", "AUS", "USA"], "gdp": ["IND"]}


def _fetch(kind):
    """All countries for one indicator in a single request (the API is slow per call)."""
    RAW.mkdir(parents=True, exist_ok=True)
    cache = RAW / f"{kind}_all.json"
    if not cache.exists():
        r = net.get(API.format(c=";".join(COUNTRIES), ind=IND[kind][0]),
                    params={"format": "json", "per_page": 20000, "date": "1960:2030"}, timeout=300, retries=4)
        cache.write_text(r.text, encoding="utf-8")
    rows = json.loads(cache.read_text(encoding="utf-8"))
    out = {}
    for x in rows[1] if len(rows) > 1 and rows[1] else []:
        if x["value"] is not None:
            out.setdefault(x["countryiso3code"], []).append((int(x["date"]), x["value"]))
    return out


def series(code, kind, _cache={}):
    if kind not in _cache:
        _cache[kind] = _fetch(kind)
    pts = sorted(_cache[kind].get(code, []))
    if not pts:
        return [], np.zeros(0)
    # keep the longest run without gaps, ending at the latest year
    years, vals = [pts[-1][0]], [pts[-1][1]]
    for y, v in reversed(pts[:-1]):
        if y != years[0] - 1:
            break
        years.insert(0, y); vals.insert(0, v)
    return years, np.array(vals, float)


def poss(name):
    return "The US" if name == "United States" else name + ("'" if name.endswith("s") else "'s")


def crop_parts(y):
    best5 = np.array([y[max(0, i - 5): i].max() if i else y[0] for i in range(len(y))])
    shortfall = np.clip(1 - y / best5, 0, None)
    yoy = np.zeros(len(y)); yoy[1:] = y[1:] / y[:-1] - 1
    return shortfall, yoy


def gdp_parts(g, avg=1, prev=None):
    """growth per period (prev = the value just before the window, for the first period);
    swings = |growth - median growth| (averaged over `avg` periods, centred), rescaled 0..1;
    dd = drop from the previous peak."""
    from engine.energy import moving_average
    growth = np.zeros(len(g)); growth[1:] = g[1:] / g[:-1] - 1
    if prev:
        growth[0] = g[0] / prev - 1
    else:
        growth[0] = np.median(growth[1:])
    swings = curves.rescale01(moving_average(np.abs(growth - np.median(growth)), avg))
    dd = 1 - g / np.maximum.accumulate(g)
    return swings, dd, growth


def make_curve(code, kind, showcase):
    years, y = series(code, kind)
    if len(y) < 30:
        return None
    name = COUNTRIES[code]
    labels = [str(t) for t in years]
    if kind == "crop":
        shortfall, yoy = crop_parts(y)
        v = curves.rescale01(0.7 * shortfall + 0.3 * np.abs(yoy))
        aux = {"yield": [round(float(x), 0) for x in y], "shortfall": [round(float(x), 4) for x in shortfall],
               "yoy": [round(float(x), 4) for x in yoy]}
        title = f"{'US' if name == 'United States' else poss(name)} cereal harvests, {years[0]}–{years[-1]}"
        moves = yoy
        what = "cereal yield"
    else:
        swings, dd, growth = gdp_parts(y)
        v = curves.rescale01(0.6 * swings + 0.4 * dd)
        aux = {"gdp": [round(float(x) / 1e9, 1) for x in y], "swings": [round(float(x), 4) for x in swings],
               "drop": [round(float(x), 4) for x in dd], "growth": [round(float(x), 4) for x in growth]}
        title = f"{poss(name)} economy, {years[0]}–{years[-1]}"
        moves = growth
        what = "GDP"
    moments = [{"t": int(i), "label": f"{name} {what} {'+' if moves[i] >= 0 else '−'}{abs(moves[i]) * 100:.1f}% ({years[i]})",
                "kind": "jump" if moves[i] >= 0 else "drop"} for i in curves.top_moves(np.abs(moves), k=5, min_gap=2)]
    return curves.make(f"{kind}_{code.lower()}_{years[0]}_{years[-1]}", kind, title, labels, v, moments, aux,
                       {"country": name, "code": code, "start": str(years[0]), "end": str(years[-1]), "showcase": showcase,
                        "credit": CREDIT.format(what=IND[kind][1])})


def explain(c):
    a = c["aux"]
    if c["source"] == "crop":
        return {"input": {"label": "Cereal yield", "unit": "kg/ha", "values": a["yield"]},
                "parts": [{"label": "Shortfall", "help": "how far below the best of the previous 5 years", "weight": 0.7,
                           "fmt": "pct", "values": a["shortfall"]},
                          {"label": "Year-on-year change", "help": "size of the change from last year", "weight": 0.3,
                           "fmt": "pct", "values": [abs(x) for x in a["yoy"]]}],
                "formula": "tension = 0.7 × shortfall + 0.3 × size of the yearly change, rescaled to 0–1"}
    return {"input": {"label": "Real GDP", "unit": "$bn", "values": a["gdp"]},
            "parts": [{"label": "Swings", "help": "how far growth is from its usual pace (0–1)", "weight": 0.6, "fmt": "x",
                       "values": a["swings"]},
                      {"label": "Drop from peak", "help": "how far below its previous high", "weight": 0.4, "fmt": "pct",
                       "values": a["drop"]}],
            "formula": "tension = 0.6 × swings + 0.4 × drop from peak, rescaled to 0–1"}


def main():
    made = []
    for kind in ("crop", "gdp"):
        for code in COUNTRIES:
            c = make_curve(code, kind, code in SHOW[kind])
            if c:
                made.append(c)
    for c in made:
        curves.save(c)
    for kind in ("crop", "gdp"):
        print(kind, "curves:", sum(c["source"] == kind for c in made),
              "| showcase:", [c["id"] for c in made if c["source"] == kind and c["meta"]["showcase"]])


if __name__ == "__main__":
    main()
