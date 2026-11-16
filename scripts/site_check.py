"""Checkpoints 6 + 7 with a headless browser (the machine's Edge via Playwright):
screenshots (380 / 1280 px, light / dark: catalog, detail, song tab), console errors, playhead moves, test-tone upload works,
Python/JS parity (energy curve + top-5 reverse matches), blind test page end to end.
"""
import functools
import http.server
import json
import sys
import threading
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import energy as E  # noqa: E402
from engine import match as M  # noqa: E402

SITE = ROOT / "site"
SHOTS = ROOT / "logs" / "screens"
PORT = 8765
TONE = SITE / "test" / "test_tone.wav"


def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
    h.func.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def python_parity():
    """Python side of the parity test, against the same int8 index the site ships."""
    y = E.load_audio(TONE)
    t, e = E.energy_from_signal(y)
    t0, ps = E.per_second(t, e)
    meta = json.loads((SITE / "data" / "index_meta.json").read_text(encoding="utf-8"))
    q = np.fromfile(SITE / "data" / "index.bin", dtype=np.int8).reshape(-1, meta["N"]).astype(float) / 31.75
    d = M.dtw_batch(M.normalise(ps), q)
    top = [(meta["ids"][i], float(d[i])) for i in np.argsort(d)[:5]]
    return t0, ps, top


def main():
    from playwright.sync_api import sync_playwright

    SHOTS.mkdir(parents=True, exist_ok=True)
    srv = serve()
    base = f"http://127.0.0.1:{PORT}"
    report = {"console_errors": [], "screens": []}
    with sync_playwright() as p:
        br = p.chromium.launch(channel="msedge", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
        for scheme in ("light", "dark"):
            for w in (380, 1280):
                ctx = br.new_context(viewport={"width": w, "height": 900}, color_scheme=scheme)
                pg = ctx.new_page()
                pg.on("console", lambda m: m.type == "error" and report["console_errors"].append(m.text))
                pg.on("pageerror", lambda e: report["console_errors"].append(str(e)))
                pg.goto(base + "/index.html")
                pg.wait_for_selector(".card", timeout=30000)
                pg.wait_for_timeout(600)
                f = SHOTS / f"catalog_{w}_{scheme}.png"
                pg.screenshot(path=str(f), full_page=True)
                report["screens"].append(f.name)
                pg.click(".card >> nth=0")
                pg.wait_for_selector("#tracks li", timeout=30000)
                pg.wait_for_timeout(600)
                f = SHOTS / f"find_{w}_{scheme}.png"
                pg.screenshot(path=str(f), full_page=True)
                report["screens"].append(f.name)
                pg.click("#tab-song")
                pg.set_input_files("#song-file", str(TONE))
                pg.wait_for_selector("#song-result:not([hidden])", timeout=120000)
                pg.wait_for_timeout(500)
                f = SHOTS / f"song_{w}_{scheme}.png"
                pg.screenshot(path=str(f), full_page=True)
                report["screens"].append(f.name)
                if w == 1280 and scheme == "dark":
                    report["test_tone_result"] = pg.inner_text("#rev-title")
                    # playhead moves (data -> song tab)
                    pg.click("#tab-find")
                    pg.click("#player-find .b-play")
                    pg.wait_for_timeout(2500)
                    t1 = pg.evaluate("document.querySelector('#player-find audio').currentTime")
                    seek = pg.evaluate("document.querySelector('#player-find .seek').value")
                    report["playhead"] = {"audio_time_after_2_5s": round(t1, 2), "seek_value": seek, "moves": t1 > 0.5}
                    report["short_clip"] = {"len": pg.evaluate("document.querySelector('#len .on').dataset.len"),
                                            "duration": round(pg.evaluate("document.querySelector('#player-find audio').duration"), 2)}
                    # stitched mode (full-length view)
                    pg.click("#len [data-len=full]")
                    pg.click("#mode [data-mode=stitched]")
                    pg.wait_for_timeout(500)
                    pg.screenshot(path=str(SHOTS / "find_stitched_1280_dark.png"), full_page=True)
                    # parity, JS side
                    js = pg.evaluate("window.__parity('test/test_tone.wav')")
                    report["js_parity"] = js
                ctx.close()
        # blind test page end to end
        ctx = br.new_context(viewport={"width": 1280, "height": 900}, color_scheme="dark")
        pg = ctx.new_page()
        pg.on("console", lambda m: m.type == "error" and report["console_errors"].append("test.html: " + m.text))
        pg.on("pageerror", lambda e: report["console_errors"].append("test.html: " + str(e)))
        pg.goto(base + "/test.html")
        pg.click("#start")
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(SHOTS / "test_trial_1280_dark.png"), full_page=True)
        n = pg.evaluate("window.__testState().n")
        for i in range(n):
            for b in ("#pa", "#pb"):
                pg.click(b)
                pg.wait_for_function("!document.querySelector('#ta').paused", timeout=20000)
                # the local dev server has no HTTP range support (GitHub Pages does), so fast-forward instead of seeking
                pg.evaluate("document.querySelector('#ta').playbackRate = 16")
                pg.wait_for_function("document.querySelector('#ta').ended", timeout=30000)
            pg.click([".answer [data-a=A]", ".answer [data-a=B]", ".answer [data-a=tie]"][i % 3])
        pg.wait_for_selector("#done:not([hidden])")
        res = json.loads(pg.input_value("#json"))
        report["blind_test"] = {"trials": n, "answers": len(res["answers"]), "score_text": pg.inner_text("#score")}
        pg.screenshot(path=str(SHOTS / "test_done_1280_dark.png"), full_page=True)
        (ROOT / "logs" / "blind_test_sample_result.json").write_text(json.dumps(res, indent=1))
        ctx.close()
        br.close()
    srv.shutdown()

    # parity comparison
    t0, ps, top_py = python_parity()
    js = report.pop("js_parity")
    jc = np.array(js["curve"])
    same_len = len(jc) == len(ps)
    max_diff = float(np.max(np.abs(jc - ps))) if same_len else None
    ids_py, ids_js = [t for t, _ in top_py], [t for t, _ in js["top"]]
    report["parity"] = {"python_top5": top_py, "js_top5": js["top"], "top5_match": ids_py == ids_js,
                        "curve_len_py_js": [len(ps), len(jc)], "curve_max_abs_diff": max_diff,
                        "t0_py_js": [round(t0, 4), round(js["t0"], 4)]}
    (ROOT / "logs" / "site_check.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: v for k, v in report.items() if k != "screens"}, indent=1)[:3000])
    print("screens:", len(report["screens"]))


if __name__ == "__main__":
    main()
