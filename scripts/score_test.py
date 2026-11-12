"""Aggregate pasted blind-test result JSONs: engine-vs-random win rate with a 95% CI and a binomial test,
overall and per source. Ties ("can't tell") are reported and excluded from the win rate.

Usage: python scripts/score_test.py results/*.json      (each file: one pasted JSON, or a JSON list of them)
       python scripts/score_test.py --simulate 20       (simulated sessions, for checking the script)
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

from scipy.stats import binomtest


def load(paths):
    out = []
    for p in paths:
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        out += d if isinstance(d, list) else [d]
    return out


def simulate(n_sessions, p_engine=0.65, p_tie=0.12, seed=1):
    rnd = random.Random(seed)
    srcs = ["stock", "rain"]
    sessions = []
    for _ in range(n_sessions):
        ans = []
        for i in range(12):
            r = rnd.random()
            choice = "tie" if r < p_tie else ("engine" if rnd.random() < p_engine else "random")
            ans.append({"trial": f"t{i}", "source": srcs[i % len(srcs)], "choice": choice})
        sessions.append({"test": "soundtrack-engine-blind-v1", "n": 12, "answers": ans})
    return sessions


def summarise(sessions):
    groups = defaultdict(lambda: {"engine": 0, "random": 0, "tie": 0})
    for s in sessions:
        for a in s["answers"]:
            for g in ("overall", a["source"]):
                groups[g][a["choice"]] += 1
    rows = []
    for g in ["overall"] + sorted(k for k in groups if k != "overall"):
        c = groups[g]
        n = c["engine"] + c["random"]
        if n == 0:
            continue
        bt = binomtest(c["engine"], n, 0.5, alternative="greater")
        ci = binomtest(c["engine"], n, 0.5).proportion_ci(confidence_level=0.95, method="wilson")
        rows.append({"group": g, "engine": c["engine"], "random": c["random"], "ties": c["tie"],
                     "win_rate": round(c["engine"] / n, 3), "ci95": [round(ci.low, 3), round(ci.high, 3)],
                     "p_value": float(f"{bt.pvalue:.3g}")})
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--simulate", type=int, default=0)
    a = ap.parse_args()
    sessions = simulate(a.simulate) if a.simulate else load(a.files)
    if not sessions:
        sys.exit("no results given")
    rows = summarise(sessions)
    print(f"sessions: {len(sessions)}{' (SIMULATED)' if a.simulate else ''}")
    print(f"{'group':<9}{'engine':>7}{'random':>7}{'ties':>6}{'win%':>7}  95% CI          one-sided binomial p")
    for r in rows:
        print(f"{r['group']:<9}{r['engine']:>7}{r['random']:>7}{r['ties']:>6}{100*r['win_rate']:>6.1f}%  "
              f"[{100*r['ci95'][0]:.1f}, {100*r['ci95'][1]:.1f}]   {r['p_value']}")
