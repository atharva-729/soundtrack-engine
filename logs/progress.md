# Progress log

**Scope:** stocks (NSE) + rain (Open-Meteo). Sports were built first, then removed from this project; the matcher
and stitcher are source-agnostic. classicals.de pieces pending (drop-in folders supported).

## ✅ Checkpoint 0: setup
Python 3.14, librosa 1.0, ffmpeg 9.0.2. Behind a TLS-inspecting proxy, so Python uses the OS trust store. Playwright
uses the installed Edge.

## ✅ Checkpoint 1: library
596 tracks, 32.3 h, 23 genres, 21 feels, 0 rows missing licence/credit. Fetched from incompetech's published
`pieces.json` catalogue; request starts 2 s apart, descriptive User-Agent.

## ✅ Checkpoint 2: energy curves
All 596 tracks: energy (pure numpy, mirrored in JS), tempo, beats, onsets. `logs/energy_samples.png`: the
"steadiest build" detector picked MacLeod's own *Hall of the Mountain King* (rises to the end ✔).

## ✅ Checkpoint 3: adapters
Stocks 354 curves (shape + drama per period; 7 showcase), rain 9 events (4 showcase). Sanity plots:
`logs/sanity_stock.png`, `logs/sanity_rain.png`. Deviations: Reliance 2008 replaces Nifty 2008 (data starts 2012);
ERA5 smooths Mumbai 2005 into two peaks.

## ✅ Checkpoint 4: matcher
Self-test 1: **50/50**; self-test 2: **20/20**; flat curve unmatchable. Popularity penalty caps any track at 5% of #1s.
Calibration from 5,000 random pairs in `logs/match_calibration.json`.

## ✅ Checkpoint 5: stitching
Stitched beats single on **11/11** showcase curves (`logs/stitch_vs_single.md`); 2–3 tracks, ~191–198 s, no clicks
at crossfades (`logs/xfade/`), no track reused within a soundtrack, no time-stretching.
(Earlier, on 10 NFL games before sports were removed: 10/10.)

## ✅ Checkpoint 6: site
Screenshots 380/1280 px, light/dark, both tabs (`logs/screens/`); test tone gives a result; playhead moves;
no console errors; Python/JS parity: identical top-5. Live scoreboard + "listen for" cues. Audio ≈ 110 MB.

## ✅ Checkpoint 7: blind test
`site/test.html` end to end (11 trials, 40-s clips); `score_test.py --simulate` OK (`logs/score_test_simulated.txt`).

## ✅ Checkpoint 8: publish
Pushed to https://github.com/atharva-729/soundtrack-engine. `stitching-kit.zip` = the multi-song idea on its own.
