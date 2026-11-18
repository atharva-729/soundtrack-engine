"""Machine performance: NASA C-MAPSS turbofan engines run to failure (FD001, 100 engines, public domain).

Curve per engine, one step per operating cycle:
  wear = average drift of 14 informative sensors away from a healthy engine (fleet baseline from the first 20
  cycles of every engine), signed so that "up" is always worse, smoothed (EWM alpha 0.1), rescaled 0..1.
Moments: wear passes 50%, wear passes 80%, failure.
"""
import io
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import curves, net  # noqa: E402

URL = "https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip"
RAW = ROOT / "data" / "cmapss"
CREDIT = ("Turbofan run-to-failure data: A. Saxena & K. Goebel (2008), 'Turbofan Engine Degradation Simulation "
          "Data Set', NASA Prognostics Data Repository (public domain)")
# sensor number -> +1 if it rises as the engine wears, -1 if it falls (FD001; the other 7 sensors are flat)
SENSORS = {2: 1, 3: 1, 4: 1, 7: -1, 8: 1, 9: 1, 11: 1, 12: -1, 13: 1, 14: 1, 15: 1, 17: 1, 20: -1, 21: -1}
SHOW_SENSOR = 4  # low-pressure turbine outlet temperature, shown as the raw input


def load():
    f = RAW / "train_FD001.txt"
    if not f.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        outer = zipfile.ZipFile(io.BytesIO(net.get(URL, timeout=300).content))
        inner_name = next(n for n in outer.namelist() if n.lower().endswith("cmapssdata.zip"))
        inner = zipfile.ZipFile(io.BytesIO(outer.read(inner_name)))
        f.write_bytes(inner.read(next(n for n in inner.namelist() if n.endswith("train_FD001.txt"))))
    a = np.loadtxt(f)
    return a  # columns: unit, cycle, 3 settings, sensors 1..21


def wear_parts(a):
    """Per-row wear index (unsmoothed) for the whole fleet."""
    base = np.concatenate([a[a[:, 0] == u][:20] for u in np.unique(a[:, 0])])
    cols = [4 + s for s in SENSORS]
    mu, sd = base[:, cols].mean(0), base[:, cols].std(0) + 1e-9
    signs = np.array(list(SENSORS.values()))
    return ((a[:, cols] - mu) / sd * signs).mean(1)


def engine_curve(a, wear_all, unit, showcase, title=None):
    m = a[:, 0] == unit
    cyc, raw_w = a[m, 1].astype(int), wear_all[m]
    temp = a[m, 4 + SHOW_SENSOR]
    sm = curves.ewm(raw_w, 0.1)
    v = curves.rescale01(sm)
    n = len(v)
    labels = [f"cycle {c}" for c in cyc]
    moments = []
    for thr, word in ((0.5, "Wear passes 50%: the slow decline speeds up"), (0.8, "Wear passes 80%: time for maintenance")):
        i = int(np.argmax(v >= thr))
        moments.append({"t": i, "label": f"{word} (cycle {cyc[i]})", "kind": "warn"})
    moments.append({"t": n - 1, "label": f"Engine {unit} fails after {cyc[-1]} cycles", "kind": "failure"})
    return curves.make(f"machine_engine_{unit:03d}", "machine", title or f"Jet engine {unit}, run to failure", labels, v, moments,
                       aux={"temp": [round(float(x), 2) for x in temp], "wear": [round(float(x), 3) for x in raw_w]},
                       meta={"unit": unit, "cycles": int(cyc[-1]), "showcase": showcase, "credit": CREDIT})


def explain(c):
    return {"input": {"label": "Turbine outlet temperature", "unit": "°R", "values": c["aux"]["temp"]},
            "parts": [{"label": "Wear", "help": "average drift of 14 sensors from a healthy engine (unsmoothed)",
                       "weight": 1, "fmt": "x", "values": c["aux"]["wear"]}],
            "formula": "tension = wear, smoothed, rescaled to 0–1 (0 = like new, 1 = failure)"}


def main():
    a = load()
    w = wear_parts(a)
    units = np.unique(a[:, 0]).astype(int)
    life = {u: int((a[:, 0] == u).sum()) for u in units}
    order = sorted(units, key=lambda u: life[u])
    # showcase rule, fixed in advance: the shortest-lived, the median and the longest-lived engine
    show = {order[0]: "shortest life", order[len(order) // 2]: "a typical life", order[-1]: "longest life"}
    made = []
    for u in units:
        t = f"Jet engine {u} run to failure ({show[u]}, {life[u]} cycles)" if u in show else None
        made.append(engine_curve(a, w, int(u), u in show, t))
    for c in made:
        curves.save(c)
    print("machine curves:", len(made), "| showcase:", {int(u): life[u] for u in show})


if __name__ == "__main__":
    main()
