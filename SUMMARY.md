# Soundtrack Engine: summary

## 1. Live link
Code is on GitHub: https://github.com/atharva-729/soundtrack-engine. To turn on the site:
repo **Settings → Pages → Deploy from a branch → `main` / `/ (root)`**, then open
`https://atharva-729.github.io/soundtrack-engine/site/`.
Local preview with working audio seeking: `python scripts/serve.py` → http://localhost:8000

## 2. Library
596 Kevin MacLeod tracks (incompetech.com, CC BY 4.0), 32.3 hours, 23 genres, 21 "feels". Every row has a licence
and a credit line. classicals.de pieces not added yet (drop them in `library/raw/classicals/` + a `tracks.csv` row).

## 3. Curves
Stocks 354 (NSE via EOD2; 7 showcase periods) and rain 9 events (Open-Meteo; 4 showcase). Sports were taken out of
this project (they live in a separate project); the matcher and stitcher are source-agnostic, so any time series
can be added as an adapter.

## 4. IPL model
Not built (sports out of scope here).

## 5. Self-tests
Own-curve → own-track **50/50**, curve-in-reverse → itself **20/20**, flat curve correctly unmatchable.
Spazzmatica Polka was #1 for 12.4% of curves; an iterative popularity penalty caps any track at 5% (104 distinct #1s).
Python ↔ browser parity: identical top-5, energy curves within ~1e-6.

## 6. Stitched vs single
Stitched (2–3 track windows, cut on beats, 3.5 s crossfades) beats the best single track on DTW cost on **11/11**
showcase curves; no audible clicks; no track reused within a soundtrack. Caveat: per-act normalisation gives
stitching structural slack. See `logs/stitch_vs_single.md`. The idea is packaged on its own in
**`stitching-kit.zip`** (explainer + code + example).

## 6b. Short versions and the catalog page
Every showcase event also comes as a **10 s and a 30 s clip**: 3 tracks each, 66 clips, 21 MB, with no track reused
across examples. The page opens on a filterable card catalog (source and shape), and the player shows raw data
→ tension ingredients → formula → tension vs song energy on one playhead. Weakest fit: Delhi 2023 (7 bumpy days)
in 10 s, labelled "loose fit".

## 7. Fun matches (chosen by shape alone)
- **Nifty 50 through the COVID crash** → *One of Them*; stitched → *Welcome to HorrorLand* then *Symmetry*.
- **Adani Enterprises, Jan–Mar 2023**, stitched → opens with *Hall of the Mountain King*.
- **Mumbai floods, July 2005** → *Devastation and Revenge*.
- **Chennai floods 2015**, stitched → opens with *Danse Macabre*.
- **Reverse:** the synthetic "slow build, hush, final burst" test tone finds its closest market moment or storm.
- With no help from titles, the "steadiest build" detector picked MacLeod's own *Hall of the Mountain King*.

## 8. Deviations from the plan
- Scope: stocks + rain only (sports removed), classicals.de pending.
- "Nifty 50 over 2008" → **Reliance over 2008** (the Nifty file starts in 2012).
- Mumbai 2005 isn't "one massive spike": ERA5 reanalysis smooths the cloudburst into two ~5 mm/h peaks. Not hand-tuned.
- Act splitting uses a DP (ruptures won't build on Python 3.14). Rain: 9 of 10 events (one API failure).
- Blind test uses 40-s clips (engine's best window vs a loudness-matched random window): 11 trials per session.
- Gemini pre-check (optional) not built.

## 9. Pitch
*Data sonification.* *Anything that changes over time has a shape, and so does every song. We match them: a market crash or a monsoon
week picks its own soundtrack from any licensed library, and the drop lands on the turning point. It reads the
drama from data, not pixels, so the sync is exact and explainable.*
