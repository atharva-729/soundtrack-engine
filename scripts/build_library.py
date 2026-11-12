"""Build the music library: Kevin MacLeod (incompetech.com) catalogue + classicals.de + drop-in custom folder.

Polite: one request every 2 s, descriptive User-Agent. Resumable: skips files already on disk.
Usage: python scripts/build_library.py [--max 600]
"""
import argparse
import csv
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import net  # noqa: E402

RAW = ROOT / "library" / "raw"
CSV_PATH = ROOT / "library" / "tracks.csv"
FIELDS = ["id", "title", "artist", "source", "source_url", "audio_url", "file", "licence", "credit",
          "duration", "genre", "feel", "bpm"]
INC_BASE = "https://incompetech.com/music/royalty-free/"
LICENCE_INC = "CC BY 4.0"
GAP_S = 2.0


def hms(s):
    try:
        h, m, sec = (int(x) for x in s.split(":"))
        return h * 3600 + m * 60 + sec
    except Exception:
        return 0


def slug(s):
    return "".join(c.lower() if c.isalnum() else "_" for c in s).strip("_")[:60]


def load_rows():
    if not CSV_PATH.exists():
        return {}
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def save_rows(rows):
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CSV_PATH.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in sorted(rows.values(), key=lambda r: r["id"]):
            w.writerow({k: r.get(k, "") for k in FIELDS})
    tmp.replace(CSV_PATH)


def pick_incompetech(pieces, genres, n, seed=7):
    """Round-robin across genres, and within a genre across feels, so the library is spread out."""
    gname = {str(g["id"]): g["genre"] for g in genres}
    ok = [p for p in pieces if p.get("filename") and 45 <= hms(p.get("length", "")) <= 600]
    rng = random.Random(seed)
    by_genre = defaultdict(lambda: defaultdict(list))
    for p in ok:
        g = gname.get(str(p.get("genre")), "Other")
        feel = (p.get("feel") or "none").split(",")[0].strip()
        by_genre[g][feel].append(p)
    queues = {}
    for g, feels in by_genre.items():
        for lst in feels.values():
            rng.shuffle(lst)
        order = []
        fl = list(feels.values())
        rng.shuffle(fl)
        while any(fl):
            for lst in fl:
                if lst:
                    order.append(lst.pop())
        queues[g] = order
    chosen = []
    gs = sorted(queues)
    while len(chosen) < n and any(queues[g] for g in gs):
        for g in gs:
            if queues[g] and len(chosen) < n:
                chosen.append((queues[g].pop(0), g))
    return chosen


def build_incompetech(rows, n):
    data = ROOT / "data"
    data.mkdir(exist_ok=True)
    pj, gj = data / "inc_pieces.json", data / "inc_genre.json"
    if not pj.exists():
        pj.write_text(json.dumps(net.get(INC_BASE + "pieces.json").json()))
        time.sleep(GAP_S)
    if not gj.exists():
        gj.write_text(json.dumps(net.get(INC_BASE + "genre.json").json()))
        time.sleep(GAP_S)
    pieces, genres = json.loads(pj.read_text()), json.loads(gj.read_text())
    chosen = pick_incompetech(pieces, genres, n)
    out = RAW / "incompetech"
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    # Polite: request *starts* are spaced >= GAP_S apart globally (<= 0.5 req/s); up to 4 transfers may overlap.
    import threading
    from concurrent.futures import ThreadPoolExecutor

    lock = threading.Lock()
    next_slot = [time.time()]

    def fetch(item):
        p, _ = item
        dest = out / p["filename"]
        url = INC_BASE + "mp3-royaltyfree/" + quote(p["filename"])
        if dest.exists() and dest.stat().st_size > 10_000:
            return True
        with lock:
            wait = next_slot[0] - time.time()
            next_slot[0] = max(next_slot[0], time.time()) + GAP_S
        if wait > 0:
            time.sleep(wait)
        try:
            r = net.get(url, timeout=300, retries=2)
            tmp = dest.with_suffix(".part")
            tmp.write_bytes(r.content)
            tmp.replace(dest)
            return True
        except Exception as e:
            print(f"FAIL {p['title']}: {e}", flush=True)
            return False

    with ThreadPoolExecutor(4) as ex:
        results = ex.map(fetch, chosen)
        oks = []
        for i, ok in enumerate(results, 1):
            oks.append(ok)
            if i % 20 == 0:
                print(f"[{i}/{len(chosen)}] {(time.time() - t0)/60:.1f} min elapsed", flush=True)

    for i, ((p, gname), ok) in enumerate(zip(chosen, oks), 1):
        if not ok:
            continue
        tid = "km_" + slug(p["title"])
        dest = out / p["filename"]
        url = INC_BASE + "mp3-royaltyfree/" + quote(p["filename"])
        rows[tid] = {
            "id": tid, "title": p["title"], "artist": "Kevin MacLeod", "source": "incompetech",
            "source_url": "https://incompetech.com/music/royalty-free/music.html",
            "audio_url": url, "file": str(dest.relative_to(ROOT)).replace("\\", "/"),
            "licence": LICENCE_INC,
            "credit": f'"{p["title"]}" Kevin MacLeod (incompetech.com), Licensed under Creative Commons: By Attribution 4.0',
            "duration": hms(p["length"]), "genre": gname, "feel": p.get("feel") or "", "bpm": p.get("bpm") or "",
        }
    save_rows(rows)


def register_folder(rows, sub, source):
    """classicals/ and custom/ folders: any audio file with a row in tracks.csv is kept; audio without a row
    is listed in logs so its licence can be recorded (we never index audio whose licence we can't record)."""
    d = RAW / sub
    missing = []
    for f in sorted(d.glob("*")):
        if f.suffix.lower() not in {".mp3", ".wav", ".flac", ".ogg", ".m4a"}:
            continue
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        if not any(r.get("file") == rel for r in rows.values()):
            missing.append(rel)
    if missing:
        (ROOT / "logs").mkdir(exist_ok=True)
        (ROOT / "logs" / f"unlicensed_{sub}.txt").write_text("\n".join(missing))
        print(f"{len(missing)} file(s) in {sub}/ have no tracks.csv row (licence unknown) - not indexed")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=600)
    a = ap.parse_args()
    rows = load_rows()
    build_incompetech(rows, a.max)
    register_folder(rows, "classicals", "classicals.de")
    register_folder(rows, "custom", "custom")
    print("tracks:", len(rows))
