# Stitched soundtracks: one long event, 2–3 songs, cut on the beat

## The idea

One song rarely fits a long event. A 3-hour game, a year of a stock or a week of rain has *acts*: a slow
opening, a long middle, a frantic finish. So instead of looking for the single track whose shape matches the whole
thing, we:

1. **split the event's intensity curve into 1–3 acts**,
2. **find, for each act, the window of some track (≥ 40 s) whose energy curve has the same shape**,
3. **choose the combination that also joins up well** (no jarring energy or tempo jumps, no loud cuts, no repeats),
4. **cut each window on a quiet beat, crossfade, loudness-normalise**, and
5. **keep a map from every data step to the second of the output audio** where it lands, so anything else (a
   chart, a scoreboard, video clips) can be synced to the music.

The engine only chooses and aligns existing licensed recordings. It never generates music.

On the 10 NFL showcase games this beat the best single track on alignment cost in **10/10** games, and on the 11 stock
and rain showcase curves in **11/11** (see `stitch_vs_single.md`).

## Inputs

**A data curve** (`engine/curves.py`):
```python
{"id": "...", "title": "...",
 "steps":   [{"t": 0, "label": "Q1 15:00", "v": 0.31}, ...],       # v = tension / intensity, 0..1
 "moments": [{"t": 161, "label": "65-yd punt-return TD", "kind": "swing"}, ...]}
```
Any series works. For a game: `tension = close × stake + 3 × |Δ win prob|`, EWM-smoothed (α = 0.3), scaled to 0..1.

**An indexed music library** (`scripts/index_library.py` → `library/curves.npz`): for every track, an energy curve at
1 point per second plus tempo, beat times and onset times. The energy curve (`engine/energy.py`) is:
2048-sample frames, hop 1024, mono 22.05 kHz; `0.6 × loudness (RMS dB clipped to [-60, 0] → 0..1) + 0.4 × spectral
flux (÷ its 95th percentile, clipped)`; 3-second moving average; leading/trailing silence trimmed.

## How it works (`engine/stitch.py`)

### 1. Split into acts
Smooth the curve (EWM α = 0.1) and pick the split that minimises within-act variance (sum of squared error around
each act's mean), using exact search over all boundaries. Every act must be **≥ 25%** of the curve. Both k = 2 and
k = 3 are tried; the one with the lower total objective (step 4) wins.

### 2. Give each act a slice of the target length
Target length defaults to **195 s** (150–240 works). Act *i* gets `target × its share of the curve`, plus crossfade
overlap, and at least **40 s**.

### 3. Candidate windows per act (fast pre-filter, then DTW)
For every track, slide a window of the act's length over its energy curve (step 4 s), resample each window and the
act to 64 points, z-score both, and score by **Pearson correlation** (one matrix product per track). Keep the best
2 windows per track and the **top 30** overall. Re-score those 30 with **banded DTW**:

* both curves resampled to **200 points** and **z-scored** (shape only, not level),
* squared-difference cost, **Sakoe–Chiba band ±10 points**, total cost **÷ path length**.

The band is essential: unbanded DTW can warp anything onto anything, so every song "matches" every curve.

### 4. Choose the combination (dynamic programming over acts)
```
objective = Σ_acts  DTW_cost(act, window) × act_share
          + 0.15 × Σ_joins transition_cost(window_a, window_b)

transition_cost =
    |energy at end of A − energy at start of B| / 0.5       # prefer cutting where both sides are calm, or both build
  + 0.5 × max(0, max(endA, startB) − 0.7) / 0.15             # don't crossfade inside a loud passage
  + 0.3 if tempo jump > 25%
  + 5.0 if B's track was already used by any earlier act       # no reuse
  + 0.3 × (act intensity goes up but window energy goes down, or vice versa)   # keep the acts' relative intensity
```

### 5. Render (ffmpeg)
* Each cut point snaps to a **beat within ±4 s** of the planned boundary, preferring the quietest nearby beat.
* Filtergraph: per-segment `aformat` + 20 ms fade-in → chained `acrossfade=d=3.5:c1=tri:c2=tri` →
  `loudnorm=I=-16:TP=-1.5:LRA=11` → 1.5 s fade-out → 128 kbps MP3. Source metadata stripped.
* **No time-stretching.** (The spec allowed ±8% only if it clearly helps; it never needed it.)

### 6. The alignment map
Each act is aligned to its window with the DTW path (monotonic): data step → song second, then shifted into output
time: `offset_i = Σ_{j<i} (len_j − 3.5 s)`. Moments get an output timestamp, snapped to the nearest beat or onset
within ±0.5 s. Output (`stitch_one.py` writes this as JSON next to the MP3):

```json
{"segments": [{"track": "km_...", "cut_start": 12.4, "cut_end": 78.9}, ...],
 "step_to_sec": [0.0, 0.4, ...],          // one entry per data step: where it lands in the output audio
 "moments": [{"label": "...", "song_s": 91.3, "track": "km_..."}],
 "xfade_at": [63.0, 128.2],               // output seconds where each 3.5 s crossfade begins
 "credits": ["\"Title\" Kevin MacLeod (incompetech.com), Licensed under Creative Commons: By Attribution 4.0", ...],
 "duration": 195.6}
```

## Checking it worked
* **Stitched vs single:** mean DTW cost per step of the stitched plan vs the best whole track for the same curve.
* **Moment sync:** distance from each key moment's output time to the nearest beat.
* **Clicks:** around each crossfade edge, the max sample-to-sample jump within ±0.5 s ÷ the 95th percentile of the
  same statistic over every 1-s window of the file. ≈ 1 means no sharper than ordinary music. Also plot the
  waveform ±1 s around each boundary.
* **Length:** rendered length should equal the planned length.

## Using it for video mashups
* The `step_to_sec` map is the edit decision list: if a highlight clip covers data steps *a..b*, place it at output
  seconds `step_to_sec[a] .. step_to_sec[b]`. Big plays land on the music's peaks because the alignment put them there.
* Put **video transitions on `xfade_at`** (the music changes there anyway), and keep big plays out of the 3.5 s
  crossfade windows (raise the transition cost if a moment falls inside one).
* Acts often line up with game phases (dull first half / comeback / overtime). You can also force act boundaries at
  known phase changes (half-time, OT) instead of the variance split; the rest of the pipeline is unchanged.
* For a fixed video length, pass `--target` = the video's length.

## Known limits
* Each act is z-normalised on its own, so stitching has more freedom than one whole track; part of its DTW win is
  structural. The relative-intensity term keeps louder acts on louder music, but a listening test is the real proof.
* Windows are ≥ 40 s, so very short events (< ~2 min of music) work better as a single track.

## Files in this kit
```
EXPLAINER.md            this file
requirements.txt
engine/energy.py        audio -> energy curve (+ tempo, beats, onsets via librosa)
engine/curves.py        Curve type, resample, rescale, EWM
engine/match.py         normalise, banded DTW (vectorised), DTW path, alignment, forward search
engine/stitch.py        acts, candidate windows, DP plan, ffmpeg render, combined alignment map
scripts/index_library.py   build library/curves.npz from library/tracks.csv (parallel, cached)
scripts/stitch_one.py      plan + render one curve:  python scripts/stitch_one.py curve.json out.mp3
example/                a stock curve, its stitched result JSON, and the stitched-vs-single table
```
Library format (`library/tracks.csv`): `id,title,artist,source,source_url,audio_url,file,licence,credit,duration,genre,feel,bpm`.
Only tracks with a recorded licence and credit get indexed.

```bash
pip install -r requirements.txt          # plus ffmpeg on PATH
python scripts/index_library.py          # once per library
python scripts/stitch_one.py example/nifty_covid_drama.json out.mp3 --target 195
```
