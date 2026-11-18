"""Build the music library from licensed sources + a drop-in custom folder.

Sources:
  incompetech  Kevin MacLeod catalogue (CC BY 4.0), up to --max tracks spread across genres.
  musopen      Musopen Kickstarter orchestral recordings on archive.org (CC0 1.0): Beethoven, Brahms, Grieg,
               Mozart, Tchaikovsky, Smetana... Individual MP3s are read straight out of the archive's zip.
  classicals   classicals.de: a curated list of famous works (FAMOUS_PAGES). Each page's licence block is parsed
               per track; a track whose licence can't be pinned down is skipped, never guessed.

Polite: one request every 2 s, descriptive User-Agent. Resumable: skips files already on disk.
Usage: python scripts/build_library.py [--sources incompetech,musopen,classicals] [--max 600]
"""
import argparse
import csv
import html
import json
import random
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote, unquote

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


def uslug(s):
    """slug() that stays unique: names that would be cut at 60 chars get a short hash of the full name instead
    (movements of one symphony differ only at the end, so plain truncation made them collide)."""
    full = "".join(c.lower() if c.isalnum() else "_" for c in s).strip("_")
    if len(full) <= 60:
        return full
    import hashlib
    return full[:53].rstrip("_") + "_" + hashlib.sha1(full.encode("utf-8")).hexdigest()[:6]


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


_last_req = [0.0]
_req_lock = __import__("threading").Lock()


def polite_get(url, **kw):
    """GET with request *starts* spaced >= GAP_S apart (thread-safe), so <= 0.5 req/s overall."""
    with _req_lock:
        slot = max(_last_req[0] + GAP_S, time.time())
        _last_req[0] = slot
    wait = slot - time.time()
    if wait > 0:
        time.sleep(wait)
    return net.get(url, **kw)


def download_many(pairs, workers=4):
    """pairs: [(url, dest)] -> list of bools. Up to `workers` transfers overlap (the file servers are slow per
    connection); request starts stay >= GAP_S apart."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(lambda p: download(*p), pairs))


def download(url, dest):
    if dest.exists() and dest.stat().st_size > 10_000:
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = polite_get(url, timeout=600, retries=5)
        b = r.content
        is_mp3 = b[:3] == b"ID3" or (len(b) > 1 and b[0] == 0xFF and b[1] & 0xE0 == 0xE0)
        if len(b) < 10_000 or not is_mp3:
            raise ValueError(f"not an MP3 ({len(b)} bytes)")
        tmp = dest.with_suffix(".part")
        tmp.write_bytes(r.content)
        tmp.replace(dest)
        return True
    except Exception as e:
        print(f"FAIL {url}: {e}", flush=True)
        return False


def rel(p):
    return str(p.relative_to(ROOT)).replace("\\", "/")


# ---------------------------------------------------------------- Musopen (archive.org, CC0)

MUSOPEN_ITEM = "https://archive.org/details/MusopenKickstarterRecordings"
MUSOPEN_ZIP = "https://archive.org/download/MusopenKickstarterRecordings/Musopen%20DVD.zip/"
LICENCE_CC0 = "CC0 1.0"
# Orchestral works + Dvořák's "American" quartet. Skipped: Goldberg Variations (30 short harpsichord-style
# variations), Schubert piano sonatas and the lesser-known string quartets: not "music people know".
MUSOPEN_KEEP = ("Beethoven - ", "Borodin - ", "Brahms - ", "Grieg - ", "Mendelssohn - ", "Mozart - ",
                "Rimsky Korsakov - ", "Smetana - ", "Tchaikovsky - ", "String Quartets/Dvorak - American")
MUSOPEN_SKIP = ("(take 2)",)
COMPOSERS = {"Beethoven": "Ludwig van Beethoven", "Borodin": "Alexander Borodin", "Brahms": "Johannes Brahms",
             "Grieg": "Edvard Grieg", "Mendelssohn": "Felix Mendelssohn", "Mozart": "Wolfgang Amadeus Mozart",
             "Rimsky Korsakov": "Nikolai Rimsky-Korsakov", "Smetana": "Bedřich Smetana",
             "Tchaikovsky": "Pyotr Ilyich Tchaikovsky", "Dvorak": "Antonín Dvořák"}


def build_musopen(rows):
    listing = polite_get(MUSOPEN_ZIP, timeout=120).text
    paths = [unquote(html.unescape(h)) for h in re.findall(r'href="//archive\.org/download/[^"]*?\.zip/([^"]+\.mp3)"', listing)]
    out = RAW / "musopen"
    todo = []
    for p in paths:
        inner = p.split("Musopen DVD/", 1)[-1]
        if not inner.startswith(MUSOPEN_KEEP) or any(s in inner for s in MUSOPEN_SKIP):
            continue
        folder, stem = inner.rsplit("/", 1)[0].split("/")[-1], inner.rsplit("/", 1)[1][:-4]
        comp_short, _, piece = folder.partition(" - ")
        composer = COMPOSERS.get(comp_short.strip(), comp_short.strip())
        # Some files are named only by movement ("1st Mov Molto allegro"): prefix the work's name.
        title = stem if len(stem) > 30 and not re.match(r"^\d|^Adagio Allegro", stem) else f"{piece.strip()}: {stem}"
        title = title.replace("Symphon No.", "Symphony No.")
        tid = "mo_" + uslug(f"{comp_short}_{title}")
        dest = out / (uslug(f"{comp_short}_{title}") + ".mp3")
        url = MUSOPEN_ZIP + quote(p, safe="")
        todo.append(((url, dest), {
            "id": tid, "title": title, "artist": composer, "source": "musopen", "source_url": MUSOPEN_ITEM,
            "audio_url": url, "file": rel(dest), "licence": LICENCE_CC0,
            "credit": f'{composer}: "{title}". Musopen Kickstarter recording (musopen.org), released under CC0 1.0 (public domain)',
            "duration": "", "genre": "Classical", "feel": "", "bpm": "",
        }))
    assert len({r["id"] for _, r in todo}) == len(todo), "duplicate musopen track ids"
    oks = download_many([pair for pair, _ in todo])
    for (_, row), ok in zip(todo, oks):
        if ok:
            rows[row["id"]] = row
    print(f"musopen: {sum(oks)} tracks ({len(todo) - sum(oks)} failed)", flush=True)
    save_rows(rows)


# ---------------------------------------------------------------- classicals.de (per-track licence)

CL_BASE = "https://www.classicals.de/"
# Works most listeners would recognise. Musopen recordings mirrored on classicals.de are skipped there
# (we take them from archive.org instead, under CC0).
FAMOUS_PAGES = [
    "bach-bwv-1068", "bach-gounod-ave-maria", "bach-badinerie", "bach-toccata", "bach-cello-suites",
    "beethoven-op62", "beethoven-elise", "beethoven-piano-sonata-no-14", "beethoven-symphony-no5",
    "beethoven-symphony-no7", "bizet-carmen", "brahms-woo1", "brahms-lullaby", "chopin-op9", "chopin-grand-valse",
    "debussy-bergamasque", "debussy-arabesques", "debussy-reverie", "delibes-flower-duet", "dvorak-humoresques",
    "elgar-op12", "fucik-gladiators", "gardel-por-una-cabeza", "gershwin-rhapsody", "grieg-piano-concerto-op16",
    "handel-sarabande", "joplin-maple-leaf-rag", "joplin-entertainer", "leontovych-carol-of-the-bells",
    "liszt-hungarian-rhapsody", "liszt-love-dreams", "massenet-meditation", "mascagni-cavalleria-rusticana",
    "mahler-symphony-no5", "mendelssohn-wedding-march", "mendelssohn-dream", "mendelssohn-felix-op64",
    "mozart-nachtmusik", "mozart-rondo", "mozart-requiem", "mozart-magic-flute", "mozart-piano-sonata-no16",
    "necke-csikos-post", "offenbach-orpheus", "pachelbel-canon-in-d", "paganini-caprices",
    "paganini-violin-concerto-no2", "puccini-turandot", "rachmaninoff-prelude-op3-2",
    "rachmaninoff-piano-concerto-no3", "ravel-m19", "rimsky-korsakov-bumblebee", "rimsky-korsakov-scheherazade",
    "rossini-barber-of-seville", "rossini-william-tell-overture", "saint-saens-carnival",
    "saint-saens-danse-macabre", "satie-gymnopedies-gnossiennes", "schubert-ave-maria", "schubert-d957",
    "sinding-spring", "smetana-ma-vlast", "strauss-zarathustra", "strauss-2-blue-danube", "strauss2-op324",
    "tchaikovsky-op23", "tchaikovsky-romeo-juliet", "tchaikovsky-swan-lake", "tchaikovsky-nutcracker",
    "tchaikovsky-symphony-no5", "verdi-traviata", "vivaldi-seasons", "wagner-valkyrie", "tetris-theme",
    "drunken-sailor", "amazing-grace",
]
# Licences we can host clips of. ND (no derivatives) is excluded: 10 s / 30 s excerpts are cuts of the track.
CL_OK = {"CC PDM 1.0", "CC0 1.0", "CC BY 4.0", "CC BY-SA 4.0", "CC BY-NC 4.0", "CC BY-NC-SA 4.0"}


def _text(s):
    s = re.sub(r"<br\s*/?>|</div>|</p>", "\n", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return "\n".join(re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in s.splitlines() if ln.strip())


def _norm_licence(s):
    s = s.strip().rstrip(".")
    s = re.sub(r"Get Commercial.*", "", s).strip()
    m = re.match(r"(CC\s*(?:PDM|0|BY(?:-NC)?(?:-SA|-ND)?)\s*\d\.\d)", s)
    return re.sub(r"\s+", " ", m.group(1)) if m else s


def _track_ranges(head):
    """'Track 1-12: ...', 'Tracks 3, 5-6 ...' -> set of 1-based indices; 'All other tracks' -> 'rest'; else None."""
    if re.search(r"all other tracks|remaining tracks", head, re.I):
        return "rest"
    m = re.search(r"tracks?\s+([\d\s,\-–&and]+)", head, re.I)
    if not m:
        return None
    idx = set()
    for part in re.split(r",|&|and", m.group(1)):
        part = part.strip(" -–")
        if re.fullmatch(r"\d+\s*[-–]\s*\d+", part):
            a, b = (int(x) for x in re.split(r"[-–]", part))
            idx.update(range(a, b + 1))
        elif part.isdigit():
            idx.add(int(part))
    return idx or None


def _performer(seg):
    for pat in (r"performed(?: and published)? by:?\s*(.+)", r"recorded,? produced,? and published(?: by)?:?\s*(.+)",
                r"recorded and produced by:?\s*(.+)", r"conducted by:?\s*(.+?)(?::\s*https?://.*)?$",
                r"recording by:?\s*(.+)", r"released by:?\s*(.+)", r"permission for publication by:?\s*(.+)",
                r"performer:?\s*(.+)"):
        m = re.search(pat, seg, re.I | re.M)
        if m:
            p = re.split(r"\s+-\s+Source:|\s+/\s*$|\s+\(Recorded", m.group(1).split("\n")[0])[0]
            return p.strip(" ./")
    return ""


ARRANGED = re.compile(r"arranged|music\s?box|for piano|piano version", re.I)


def _resolve_unranged(items, lic_for, perf_for, segs):
    """Pages whose licence block is split by version ("Orchestral version: ... / Piano version: ...") rather than
    track number. classicals.de's own arrangements are by Gregor Quendel; the other segment is the original
    recording. Assign by a performer name in the title if one matches, else by "Arranged for ..." in the title."""
    todo = [k for k in range(1, len(items) + 1) if k not in lic_for]
    if not todo:
        return
    info = [(head, lic, _performer(head)) for head, lic in segs if _track_ranges(head) is None]
    if not info:
        return
    if len({lic for _, lic, _ in info}) == 1 and len({p for _, _, p in info if p}) <= 1:
        perf = next((p for _, _, p in info if p), "")
        for k in todo:
            lic_for[k], perf_for[k] = info[0][1], perf
        return
    q = [x for x in info if "Quendel" in x[0]]
    o = [x for x in info if "Quendel" not in x[0]]
    if len(q) < 1 or len(o) > 1 or len({x[1] for x in q}) != 1:
        return  # ambiguous: leave unknown, track gets skipped
    q_lic, q_perf = q[0][1], "Gregor Quendel"
    if not o:
        for k in todo:
            if ARRANGED.search(_text(items[k - 1][1])):
                lic_for[k], perf_for[k] = q_lic, q_perf
        return
    o_lic, o_perf = o[0][1], o[0][2]
    names = [w for w in re.split(r"[ /,]+", o_perf) if len(w) > 3]
    by_name = any(any(w in _text(items[k - 1][1]) for w in names) for k in todo)
    for k in todo:
        t = _text(items[k - 1][1])
        orig = any(w in t for w in names) if by_name else not ARRANGED.search(t)
        lic_for[k], perf_for[k] = (o_lic, o_perf) if orig else (q_lic, q_perf)


def parse_classicals(page, slug_):
    """-> list of tracks {title, url, performer, publisher, licence}; licence '' if it can't be determined."""
    i = page.find('id="audio-player"')
    if i < 0:
        return []
    page = page[i:page.find('class="controls"', i) if 'class="controls"' in page[i:] else len(page)]
    items = re.findall(r'class="playlist-item"[^>]*?data-src="([^"]+)".*?class="playlist-item-name">(.*?)</div>', page, re.S)
    info = re.search(r'class="producer-info"[^>]*>(.*)', page, re.S)
    block = _text(info.group(1)) if info else ""
    # Split the block into segments, each ending in "License Terms: X".
    segs = [(m.group(1), _norm_licence(m.group(2))) for m in
            re.finditer(r"(.*?)License Terms:\s*([^\n]+)", block, re.S)]
    publisher = (re.search(r"Publisher:?\s*\n?(.+)", block) or [None, ""])[1].strip()
    lic_for, perf_for = {}, {}
    if len(segs) == 1:
        for k in range(1, len(items) + 1):
            lic_for[k], perf_for[k] = segs[0][1], _performer(segs[0][0])
    elif len(segs) > 1:
        claimed, rest = set(), None
        for head, lic in segs:
            r = _track_ranges(head)
            if r == "rest":
                rest = (lic, _performer(head))
            elif r:
                for k in r:
                    lic_for[k], perf_for[k] = lic, _performer(head)
                claimed |= r
        if rest:
            for k in range(1, len(items) + 1):
                if k not in claimed:
                    lic_for[k], perf_for[k] = rest
        _resolve_unranged(items, lic_for, perf_for, segs)
    out = []
    for k, (src, name) in enumerate(items, 1):
        title = _text(name).replace("\n", " ")
        perf = perf_for.get(k, "")
        if not perf and lic_for.get(k) and "Gregor Quendel" in block and ARRANGED.search(title):
            perf = "Gregor Quendel"
        out.append({"page": slug_, "title": title, "url": html.unescape(src),
                    "performer": perf, "publisher": publisher, "licence": lic_for.get(k, "")})
    return out


def _arr_rank(title):
    t = title.lower()
    return (0 if re.search(r"string|orchestra|woodwind|symphon", t) else 1 if "piano" in t else
            3 if re.search(r"music\s?box", t) else 2)


def pick_classicals(tracks, max_arr=2, max_arr_only=4):
    """Per page: every original recording, plus the best few of classicals.de's own arrangements (strings /
    orchestra before piano before guitar etc., music box last), so one tune doesn't flood the library."""
    by_page = defaultdict(list)
    for t in tracks:
        by_page[t["page"]].append(t)
    keep = []
    for ts in by_page.values():
        orig = [t for t in ts if not ARRANGED.search(t["title"])]
        arr = sorted((t for t in ts if ARRANGED.search(t["title"])), key=lambda t: _arr_rank(t["title"]))
        keep += orig + arr[:max_arr if orig else max_arr_only]
    return keep


def build_classicals(rows, catalog_only=False):
    cache = ROOT / "data" / "classicals"
    cache.mkdir(parents=True, exist_ok=True)
    catalog, skipped = [], []
    for s in FAMOUS_PAGES:
        f = cache / f"{s}.html"
        if not f.exists():
            try:
                f.write_text(polite_get(CL_BASE + s, timeout=60).text, encoding="utf-8")
            except Exception as e:
                print(f"FAIL page {s}: {e}", flush=True)
                continue
        found = parse_classicals(f.read_text(encoding="utf-8"), s)
        if not found:
            skipped.append(f"{s}: no playable tracks found on the page")
        catalog += found
    (cache / "catalog.json").write_text(json.dumps(catalog, indent=1, ensure_ascii=False), encoding="utf-8")
    if catalog_only:
        print(f"catalog: {len(catalog)} tracks -> {rel(cache / 'catalog.json')}")
        return
    out = RAW / "classicals"
    n = 0
    usable = []
    for t in catalog:
        why = ("musopen duplicate (taken from archive.org)" if "Musopen" in t["publisher"] else
               "incompetech duplicate (already in library)" if "Kevin MacLeod" in t["performer"] else
               "licence unknown" if not t["licence"] else
               f"licence {t['licence']} not allowed" if t["licence"] not in CL_OK else
               "no performer" if not t["performer"] else "")
        if why:
            skipped.append(f"{t['page']}: {t['title']} -- {why}")
        else:
            usable.append(t)
    chosen = pick_classicals(usable)
    skipped += [f"{t['page']}: {t['title']} -- extra arrangement" for t in usable if t not in chosen]
    todo, seen = [], set()
    for t in chosen:
        fname = unquote(t["url"].split("?", 1)[0].rsplit("/", 1)[-1])
        if fname in seen:  # the same recording listed on two pages (e.g. the Wedding March)
            skipped.append(f"{t['page']}: {t['title']} -- same recording as on another page")
            continue
        seen.add(fname)
        dest = out / fname
        title = re.sub(r"^Classicals\.de\s*-\s*", "", t["title"])
        composer_page = next((v for k, v in CL_COMPOSER.items() if t["page"].startswith(k)), "")
        tid = "cl_" + uslug(f"{t['page']}_{title}")
        todo.append(((t["url"], dest), t, {
            "id": tid, "title": title, "artist": composer_page, "source": "classicals.de",
            "source_url": CL_BASE + t["page"], "audio_url": t["url"], "file": rel(dest), "licence": t["licence"],
            "credit": f'Music: "{title}" by {t["performer"]}. Source: https://www.classicals.de ({t["licence"]})',
            "duration": "", "genre": "Classical", "feel": "", "bpm": "",
        }))
    assert len({r["id"] for *_, r in todo}) == len(todo), "duplicate classicals track ids"
    assert len({str(p[1]) for p, *_ in todo}) == len(todo), "duplicate classicals file names"
    oks = download_many([pair for pair, *_ in todo])
    for (_, t, row), ok in zip(todo, oks):
        if ok:
            rows[row["id"]] = row
            n += 1
        else:
            skipped.append(f"{t['page']}: {t['title']} -- download failed (dead link on the site)")
    (ROOT / "logs").mkdir(exist_ok=True)
    (ROOT / "logs" / "classicals_skipped.txt").write_text("\n".join(skipped), encoding="utf-8")
    print(f"classicals.de: {n} tracks from {len(FAMOUS_PAGES)} pages; {len(skipped)} skipped "
          f"(logs/classicals_skipped.txt)", flush=True)
    save_rows(rows)


CL_COMPOSER = {
    "bach-gounod": "Johann Sebastian Bach / Charles Gounod", "bach": "Johann Sebastian Bach",
    "beethoven": "Ludwig van Beethoven", "bizet": "Georges Bizet", "brahms": "Johannes Brahms",
    "chopin": "Frédéric Chopin", "debussy": "Claude Debussy", "delibes": "Léo Delibes", "dvorak": "Antonín Dvořák",
    "elgar": "Edward Elgar", "fucik": "Julius Fučík", "gardel": "Carlos Gardel", "gershwin": "George Gershwin",
    "grieg": "Edvard Grieg", "handel": "George Frideric Handel", "joplin": "Scott Joplin",
    "leontovych": "Mykola Leontovych", "liszt": "Franz Liszt", "massenet": "Jules Massenet",
    "mascagni": "Pietro Mascagni", "mahler": "Gustav Mahler", "mendelssohn": "Felix Mendelssohn",
    "mozart": "Wolfgang Amadeus Mozart", "necke": "Hermann Necke", "offenbach": "Jacques Offenbach",
    "pachelbel": "Johann Pachelbel", "paganini": "Niccolò Paganini", "puccini": "Giacomo Puccini",
    "rachmaninoff": "Sergei Rachmaninoff", "ravel": "Maurice Ravel", "rimsky-korsakov": "Nikolai Rimsky-Korsakov",
    "rossini": "Gioachino Rossini", "saint-saens": "Camille Saint-Saëns", "satie": "Erik Satie",
    "schubert": "Franz Schubert", "sinding": "Christian Sinding", "smetana": "Bedřich Smetana",
    "strauss-zarathustra": "Richard Strauss", "strauss": "Johann Strauss II", "tchaikovsky": "Pyotr Ilyich Tchaikovsky",
    "verdi": "Giuseppe Verdi", "vivaldi": "Antonio Vivaldi", "wagner": "Richard Wagner",
    "tetris-theme": "Traditional (Korobeiniki)", "drunken-sailor": "Traditional", "amazing-grace": "Traditional",
}


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
    ap.add_argument("--sources", default="incompetech,musopen,classicals")
    ap.add_argument("--catalog-only", action="store_true", help="classicals.de: fetch + parse pages, download nothing")
    a = ap.parse_args()
    src = set(a.sources.split(","))
    rows = load_rows()
    if a.catalog_only:
        build_classicals(rows, catalog_only=True)
        sys.exit(0)
    if "incompetech" in src:
        build_incompetech(rows, a.max)
    if "musopen" in src:
        build_musopen(rows)
    if "classicals" in src:
        build_classicals(rows)
    register_folder(rows, "classicals", "classicals.de")
    register_folder(rows, "musopen", "musopen")
    register_folder(rows, "custom", "custom")
    print("tracks:", len(rows))
