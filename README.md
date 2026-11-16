# Soundtrack Engine: data sonification

**Hear your data. Anything that changes over time has a shape, and so does every song. Match the shapes.**

A stock's year or a monsoon week becomes a **curve** of how tense or intense it was, moment by
moment. Every track in a music library becomes an **energy curve**. The engine finds the track whose rises, calms
and drops line up with the data's, and shows *where* they line up ("the drop lands on the interception").

- **Data → song:** what's the soundtrack of this market crash or storm? The page opens on a catalog of real
  events as cards: each shows a thumbnail of the raw data and its tension, and you can filter by source or by
  shape (early shock, twin peaks, late climax…). Every event comes as a **10 s clip, a 30 s clip and a full song**,
  and the player shows step by step how the raw data becomes the tension curve the music follows.
- **Song → data:** upload a song and find the market moment or rain event that felt like it.
  The song is analysed in your browser and never leaves your device.
- **Stitched soundtracks:** 2–3 track windows, crossfaded on beats, so each act of a long event gets its own music.

The engine only *chooses and aligns* existing, licensed recordings. It never generates or composes music.

**Live site:** see `SUMMARY.md` (GitHub Pages, served from `/site`).

## How it works

```
 stocks    ─┐   adapters: any data -> Curve (0..1 over time + labelled key moments)
 rainfall  ─┴──────────────────────────────────────────────────────────────┐
                                                                           ▼
 music library ──► energy curve per track ──► index ──► banded-DTW matcher
                                                            │
             data → top songs + alignment · song → top curves · stitched soundtrack
                                                            │
                               player page with one playhead + blind listening test
```

* **Energy curve** (`engine/energy.py`, mirrored exactly in `site/js/energy.js`): 2048/1024 frames,
  `0.6 × loudness (RMS dB → 0..1) + 0.4 × spectral flux (/ 95th pct)`, ~3 s moving average, silence trimmed.
* **Stocks:** `shape` (log price) and `drama` (0.6 × 10-day volatility + 0.4 × drawdown). **Rain:** hourly mm,
  3-h smoothed. Any time series can be added as an adapter that writes a 0..1 curve plus labelled key moments.
  Each adapter also has an `explain(curve)` that returns the raw input, the weighted ingredients and the formula,
  which the page draws as raw → ingredients → tension.
* **Matcher** (`engine/match.py`): both curves resampled to 200 points and z-scored; DTW with a Sakoe–Chiba band
  of ±10 (cost / path length). The band matters: without it every curve matches every song. Match % is a
  percentile against 5,000 random (curve, track) pairs. A small popularity penalty stops a few tracks winning everything.
* **10 s / 30 s clips** (`scripts/short_versions.py`): the same matcher, run over every 10 s or 30 s window of every
  track (correlation pre-filter, then banded DTW). The cut start snaps to the nearby beat that keeps the best fit.
  The 3 best distinct tracks are kept, with no track reused across examples, and each is rendered with short
  fades and `loudnorm`. The whole event is squeezed into the clip, and the 2–3 biggest moments are flagged. Clips
  are labelled tight, good or loose fit by DTW cost. A match % would always read ~100% here, because the best of
  ~100k windows always beats random pairs.
* **Alignment:** the DTW path becomes a monotonic map from data step to song second; key moments snap to the
  nearest beat or onset within ±0.5 s.
* **Stitching** (`engine/stitch.py`): DP split into acts (each ≥ 25%), correlation pre-filter over every ≥ 40 s
  window of every track, banded DTW on the top 30, DP over acts with transition costs (energy jump at the cut,
  loud cuts, tempo jumps > 25%, reuse), then cut on quiet beats, 3.5 s crossfade, `loudnorm I=-16`.

## Stitching kit

`stitching-kit.zip` (and the `stitching-kit/` folder) holds the multi-song idea on its own: an explainer of how
2–3 track windows are chosen, cut on beats and crossfaded, plus all the code it needs (`engine/`,
`scripts/index_library.py`, `scripts/stitch_one.py`) and a worked example.

## Repo layout

```
engine/    energy.py curves.py match.py stitch.py net.py
adapters/  stock.py rain.py
scripts/   build_library.py index_library.py selftest_match.py showcase.py make_site.py
           short_versions.py make_test.py make_test_tone.py score_test.py site_check.py sanity_plots.py
           stitch_one.py serve.py
library/   tracks.csv (id, title, artist, source, licence, credit, ...), curves.npz
curves/showcase/   the showcase Curve JSONs
site/      index.html, test.html, js/, css/, data/, audio/ (showcase tracks + audio/short/ clips, all CC BY)
logs/      progress, self-tests, calibration, plots, screenshots
```

## Rebuild

```bash
pip install numpy scipy pandas pyarrow librosa soundfile requests beautifulsoup4 scikit-learn matplotlib truststore playwright
# ffmpeg on PATH
python scripts/build_library.py --max 600   # polite: 1 request every 2 s
python scripts/index_library.py
python adapters/stock.py && python adapters/rain.py   # data sources: see below
python scripts/selftest_match.py && python scripts/showcase.py && python scripts/short_versions.py && python scripts/make_site.py
python scripts/make_test.py && python scripts/make_test_tone.py && python scripts/site_check.py
python scripts/serve.py          # local preview with audio seeking: http://localhost:8000
```

Your own music: put audio in `library/raw/custom/`, add a row (with licence and credit) to `library/tracks.csv`,
and re-run `index_library.py`. Audio without a recorded licence is never indexed.

## Data and music credits

* Music: **Kevin MacLeod (incompetech.com)**, licensed under Creative Commons: By Attribution 4.0. Each track's
  exact credit line is in `library/tracks.csv` and shown wherever it plays.
* NSE daily closes: the open-source [EOD2](https://github.com/BennyThadikaran/eod2_data) dataset.
* Weather: [Open-Meteo.com](https://open-meteo.com/) historical archive (ERA5), CC BY 4.0.

No Spotify, no backend, no analytics. The site makes no network calls beyond its own files.
