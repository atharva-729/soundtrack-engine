"""NSE daily closes (EOD2 dataset, split/bonus adjusted) -> two Curves per stock-period:
  shape: log price rescaled 0..1 (the story of the price)
  drama: 0.6 * vol_norm + 0.4 * drawdown, rescaled 0..1 (how eventful it was)
Moments: the 5 biggest absolute daily moves. No news text.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import curves  # noqa: E402

DAILY = ROOT / "data" / "eod2" / "daily"
NAMES = {"nifty 50": "Nifty 50", "infy": "Infosys", "adanient": "Adani Enterprises", "tcs": "TCS",
         "reliance": "Reliance", "hdfcbank": "HDFC Bank", "sbin": "SBI", "icicibank": "ICICI Bank",
         "bhartiartl": "Bharti Airtel", "itc": "ITC"}

SHOWCASE = [
    ("nifty 50", "2019-12-01", "2020-06-30", "nifty_covid", "Nifty 50 through the COVID crash"),
    # The EOD2 Nifty 50 file starts in 2012, so 2008 uses Reliance (then the index heavyweight) instead.
    ("reliance", "2008-01-01", "2008-12-31", "reliance_2008", "Reliance over 2008"),
    ("infy", "2019-07-01", "2020-06-30", "infy_2019_20", "Infosys, Jul 2019 - Jun 2020"),
    ("adanient", "2023-01-01", "2023-03-31", "adanient_2023q1", "Adani Enterprises, Jan - Mar 2023"),
]
LAST12 = ["tcs", "reliance", "hdfcbank"]


def load(sym):
    df = pd.read_csv(DAILY / f"{sym}.csv", usecols=["Date", "Close"], parse_dates=["Date"])
    return df.dropna().sort_values("Date").drop_duplicates("Date").set_index("Date")["Close"]


def fmt_pct(x):
    return f"{'+' if x >= 0 else '−'}{abs(x) * 100:.1f}%"


def _window(sym, start, end):
    """Closes, daily returns and the two drama ingredients for one period."""
    full = load(sym)
    # compute volatility with 10 days of look-back before the window
    s = full[(full.index >= pd.Timestamp(start) - pd.Timedelta(days=30)) & (full.index <= end)]
    ret = s.pct_change()
    vol = ret.rolling(10, min_periods=3).std()
    win = (s.index >= start)
    s, ret, vol = s[win], ret[win], vol[win]
    price = s.values
    vol_norm = curves.rescale01(vol.fillna(0).values) if len(s) else np.zeros(0)
    dd = 1 - price / np.maximum.accumulate(price) if len(s) else np.zeros(0)
    return s, ret, vol_norm, dd


def explain(c):
    """How the tension of a saved stock curve is built, for the site's step-by-step chart."""
    m = c["meta"]
    price = c["aux"]["price"]
    inp = {"label": "Daily close", "unit": "₹", "values": price}
    if m.get("kind") == "shape":
        return {"input": inp, "parts": [],
                "formula": "tension = the closing price itself (log scale), rescaled to 0–1"}
    s, _, vol_norm, dd = _window(m["symbol"], m["start"], m["end"])
    check = curves.rescale01(0.6 * vol_norm + 0.4 * dd)
    v = np.array([st["v"] for st in c["steps"]])
    assert len(check) == len(v) and np.abs(check - v).max() < 1e-3, c["id"]
    return {"input": inp,
            "parts": [{"label": "Swings", "help": "how much the price jumps day to day (10-day volatility, 0–1)",
                       "weight": 0.6, "fmt": "x", "values": [round(float(x), 4) for x in vol_norm]},
                      {"label": "Drop from high", "help": "how far below its best close so far",
                       "weight": 0.4, "fmt": "pct", "values": [round(float(x), 4) for x in dd]}],
            "formula": "tension = 0.6 × swings + 0.4 × drop from high, rescaled to 0–1"}


def period_curves(sym, start, end, cid, title, tag="stock"):
    s, ret, vol_norm, dd = _window(sym, start, end)
    if len(s) < 20:
        return []
    price = s.values
    dates = s.index
    labels = [d.strftime("%d %b %Y") for d in dates]
    name = NAMES.get(sym, sym.upper())

    shape = curves.rescale01(np.log(price))
    drama = curves.rescale01(0.6 * vol_norm + 0.4 * dd)

    r = ret.fillna(0).values
    moments = [{"t": int(i), "label": f"{name} {fmt_pct(r[i])} ({dates[i].day} {dates[i].strftime('%b %Y')})",
                "kind": "drop" if r[i] < 0 else "jump", "ret": round(float(r[i]), 4)}
               for i in curves.top_moves(np.abs(r), k=5)]
    aux = {"price": [round(float(p), 2) for p in price]}
    meta = {"symbol": sym, "name": name, "start": str(dates[0].date()), "end": str(dates[-1].date()),
            "credit": "NSE daily closes via the open-source EOD2 dataset (github.com/BennyThadikaran/eod2_data)"}
    out = []
    for kind, v in (("shape", shape), ("drama", drama)):
        c = curves.make(f"{cid}_{kind}", "stock", f"{title} · {kind}", labels, v, moments, aux,
                        {**meta, "kind": kind, "showcase": tag == "showcase"})
        out.append(c)
    return out


def main():
    made = []
    for sym, a, b, cid, title in SHOWCASE:
        made += period_curves(sym, a, b, cid, title, "showcase")
    end = load("tcs").index.max()
    start = end - pd.DateOffset(months=12)
    for sym in LAST12:
        made += period_curves(sym, start, end, f"{sym}_last12", f"{NAMES[sym]}, last 12 months", "showcase")
    # Extra calendar-year curves for every checked-out symbol: gives "which market moment is your song?" variety.
    for f in sorted(DAILY.glob("*.csv")):
        sym = f.stem
        s = load(sym)
        for y in range(max(2008, s.index.min().year + 1), end.year):
            made += period_curves(sym, f"{y}-01-01", f"{y}-12-31", f"{sym.replace(' ', '')}_{y}", f"{NAMES.get(sym, sym)} {y}")
    for c in made:
        curves.save(c)
    print("stock curves:", len(made), "| showcase:", sum(c["meta"]["showcase"] for c in made))


if __name__ == "__main__":
    main()
