"""Open-Meteo historical archive (hourly precipitation) -> rain-intensity Curves.
Curve: hourly precipitation, 3-hour moving average, rescaled 0..1. Moments: the 5 wettest hours.
"""
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import curves, net  # noqa: E402
from engine.energy import moving_average  # noqa: E402

API = "https://archive-api.open-meteo.com/v1/archive"
EVENTS = [
    # id, city, lat, lon, start, end, showcase
    ("rain_mumbai_2005", "Mumbai", 19.076, 72.8777, "2005-07-25", "2005-07-28", True),
    ("rain_chennai_2015", "Chennai", 13.0827, 80.2707, "2015-11-30", "2015-12-03", True),
    ("rain_delhi_2023", "Delhi", 28.6139, 77.2090, "2023-07-07", "2023-07-13", True),
    ("rain_kochi_2018", "Kochi", 9.9312, 76.2673, "2018-08-14", "2018-08-18", True),
    # extra events for reverse-search variety
    ("rain_mumbai_2017", "Mumbai", 19.076, 72.8777, "2017-08-28", "2017-08-31", False),
    ("rain_bengaluru_2022", "Bengaluru", 12.9716, 77.5946, "2022-09-03", "2022-09-07", False),
    ("rain_guwahati_2022", "Guwahati", 26.1445, 91.7362, "2022-06-13", "2022-06-18", False),
    ("rain_kedarnath_2013", "Kedarnath", 30.7346, 79.0669, "2013-06-14", "2013-06-18", False),
    ("rain_chennai_2023", "Chennai", 13.0827, 80.2707, "2023-12-02", "2023-12-06", False),
    ("rain_kolkata_2020", "Kolkata", 22.5726, 88.3639, "2020-05-19", "2020-05-22", False),
]


def event_curve(cid, city, lat, lon, start, end, showcase):
    r = net.get(API, timeout=180, retries=6, params={"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
                             "hourly": "precipitation", "timezone": "Asia/Kolkata"}).json()
    times = r["hourly"]["time"]
    mm = np.array([x if x is not None else 0.0 for x in r["hourly"]["precipitation"]], float)
    v = curves.rescale01(moving_average(mm, 3))
    labels = [t.replace("T", " ") for t in times]
    moments = [{"t": int(i), "label": f"{city} {mm[i]:.1f} mm in the hour to {labels[i]}", "kind": "peak"}
               for i in curves.top_moves(mm, k=5, min_gap=2)]
    title = f"{city} rain, {start} to {end}"
    return curves.make(cid, "rain", title, labels, v, moments, aux={"mm": [round(float(x), 2) for x in mm]},
                       meta={"city": city, "lat": lat, "lon": lon, "start": start, "end": end, "showcase": showcase,
                             "total_mm": round(float(mm.sum()), 1),
                             "credit": "Weather data by Open-Meteo.com (CC BY 4.0), ERA5 reanalysis"})


def explain(c):
    """How the tension of a saved rain curve is built, for the site's step-by-step chart."""
    return {"input": {"label": "Rain", "unit": "mm/h", "values": c["aux"]["mm"]}, "parts": [],
            "formula": "tension = rain averaged over a 3-hour window, rescaled to 0–1"}


if __name__ == "__main__":
    n = 0
    for ev in EVENTS:
        if (curves.CURVES_DIR / "rain" / f"{ev[0]}.json").exists():
            n += 1
            continue
        try:
            c = event_curve(*ev)
        except Exception as e:
            print("FAILED", ev[0], type(e).__name__)
            continue
        curves.save(c)
        n += 1
        print(c["id"], len(c["steps"]), "h, total", c["meta"]["total_mm"], "mm")
        time.sleep(1.0)  # well inside Open-Meteo's free-use limits
    print("rain curves:", n)
