"""UK wind power (Elexon BMRS, generation by fuel type, half-hourly) -> energy-production Curves.

Curve: hourly transmission-metered wind output (GW), 3-hour moving average, rescaled 0..1.
So the music follows how much power the wind is making: storms surge, still spells fade.
Moments: the 5 biggest 3-hour swings in output (ramps up and down).
Reporting gaps (wind suddenly reads below 40% of the local 3.5-hour median, e.g. 15 GW -> 0 -> 15 GW within
two hours, which real wind cannot do) are interpolated before anything else.
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import curves, net  # noqa: E402
from engine.energy import moving_average  # noqa: E402

API = "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH"
RAW = ROOT / "data" / "elexon"
CREDIT = "UK generation by fuel type: Elexon BMRS (Elexon Open Data Licence)"
INTERCONNECTORS = ("INT",)  # imports are not generation

# id, title, first day, showcase   (named storms and still spells, chosen before looking at the data)
EVENTS = [
    ("energy_storm_ciaran_2023", "UK wind power through Storm Ciarán", "2023-10-30", True),
    ("energy_storm_isha_2024", "UK wind power through Storms Isha and Jocelyn", "2024-01-19", True),
    ("energy_still_week_2025", "UK wind power in the still, freezing week of Jan 2025", "2025-01-04", True),
    ("energy_storm_eowyn_2025", "UK wind power through Storm Éowyn", "2025-01-21", True),
]


def fetch_days(first, n_days=7):
    """{start_time_utc: {fuel: MW}} for n_days from `first` (cached)."""
    RAW.mkdir(parents=True, exist_ok=True)
    out = {}
    d0 = dt.date.fromisoformat(first)
    for k in range(0, n_days, 7):
        a = d0 + dt.timedelta(days=k)
        b = min(d0 + dt.timedelta(days=n_days - 1), a + dt.timedelta(days=6))
        cache = RAW / f"fuelhh_{a}_{b}.json"
        if not cache.exists():
            r = net.get(API, params={"settlementDateFrom": str(a), "settlementDateTo": str(b), "format": "json"},
                        timeout=120, retries=4)
            cache.write_text(r.text, encoding="utf-8")
            time.sleep(2)
        for x in json.loads(cache.read_text(encoding="utf-8"))["data"]:
            out.setdefault(x["startTime"], {})[x["fuelType"]] = x["generation"]
    return out


def despike(x, half=3, frac=0.4):
    x = np.asarray(x, float).copy()
    med = np.array([np.median(x[max(0, i - half): i + half + 1]) for i in range(len(x))])
    bad = x < frac * med
    if bad.any() and not bad.all():
        idx = np.arange(len(x))
        x[bad] = np.interp(idx[bad], idx[~bad], x[~bad])
    return x, int(bad.sum())


def week_curve(cid, title, first, showcase, n_days=7):
    hh = fetch_days(first, n_days)
    times = sorted(hh)
    wind, fixed = despike([hh[t].get("WIND", 0) for t in times])
    wind = wind / 1000  # GW
    total = np.array([sum(v for f, v in hh[t].items() if not f.startswith(INTERCONNECTORS)) for t in times], float) / 1000
    # half-hourly -> hourly
    n = len(times) // 2
    wind_h = wind[: 2 * n].reshape(n, 2).mean(1)
    total_h = total[: 2 * n].reshape(n, 2).mean(1)
    hours = [dt.datetime.fromisoformat(times[2 * i].replace("Z", "+00:00")) for i in range(n)]
    labels = [h.strftime("%a %d %b %H:00") for h in hours]
    smooth = moving_average(wind_h, 3)
    v = curves.rescale01(smooth)
    ramp = np.zeros(n)
    ramp[3:] = smooth[3:] - smooth[:-3]
    moments = [{"t": int(i), "label": f"Wind power {'surges' if ramp[i] > 0 else 'drops'} {abs(ramp[i]):.1f} GW in 3 hours "
                                      f"({labels[i]} UTC)", "kind": "jump" if ramp[i] > 0 else "drop"}
               for i in curves.top_moves(np.abs(ramp), k=5, min_gap=6)]
    share = 100 * wind_h / np.maximum(total_h, 1e-6)
    return curves.make(cid, "energy", title, labels, v, moments,
                       aux={"gw": [round(float(x), 2) for x in wind_h], "share": [round(float(x), 1) for x in share]},
                       meta={"region": "Great Britain", "start": hours[0].date().isoformat(), "end": hours[-1].date().isoformat(),
                             "peak_gw": round(float(wind_h.max()), 1), "low_gw": round(float(wind_h.min()), 1),
                             "gaps_interpolated": fixed,
                             "showcase": showcase, "credit": CREDIT})


def explain(c):
    return {"input": {"label": "Wind output", "unit": "GW", "values": c["aux"]["gw"]}, "parts": [],
            "formula": "tension = UK wind power output, averaged over 3 hours, rescaled to 0–1"}


def main():
    made = []
    for cid, title, first, show in EVENTS:
        made.append(week_curve(cid, title, first, show))
    # every week of 2024, for "which moment is your song?" variety
    d = dt.date(2024, 1, 1)
    while d.year == 2024:
        made.append(week_curve(f"energy_week_{d}", f"UK wind power, week of {d.strftime('%d %b %Y')}", str(d), False))
        d += dt.timedelta(days=7)
    for c in made:
        curves.save(c)
    print("energy curves:", len(made), "| showcase:", sum(c["meta"]["showcase"] for c in made))


if __name__ == "__main__":
    main()
