"""Audio -> energy curve.

Written with plain numpy (no librosa feature code) so that site/js/energy.js can reproduce it exactly:
  * mono, 22.05 kHz
  * frames of 2048 samples, hop 1024, no padding / centering
  * loud = RMS of the raw frame in dB, clipped to [-60, 0], mapped to 0..1
  * flux = sum of positive magnitude changes of a Hann-windowed spectrum, / its 95th percentile, clipped to [0, 1]
  * energy = 0.6*loud + 0.4*flux, moving average over ~3 s (edge-normalised)
  * trim leading/trailing frames below 5% of max
"""
import numpy as np

SR = 22050
N_FFT = 2048
HOP = 1024
SMOOTH_S = 3.0


def load_audio(path, sr=SR):
    import librosa

    y, _ = librosa.load(str(path), sr=sr, mono=True)
    return y.astype(np.float32)


def _frames(y):
    if len(y) < N_FFT:
        y = np.pad(y, (0, N_FFT - len(y)))
    n = 1 + (len(y) - N_FFT) // HOP
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n)[:, None]
    return y[idx]


def moving_average(x, w):
    """Centred moving average of odd width w; edges averaged over the part of the window that exists."""
    w = max(1, int(w) | 1)
    k = np.ones(w)
    num = np.convolve(x, k, mode="same")
    den = np.convolve(np.ones_like(x), k, mode="same")
    return num / den


def energy_from_signal(y, sr=SR):
    fr = _frames(np.asarray(y, dtype=np.float64))
    rms = np.sqrt(np.mean(fr * fr, axis=1))
    db = 20.0 * np.log10(rms + 1e-10)
    loud = (np.clip(db, -60.0, 0.0) + 60.0) / 60.0

    win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(N_FFT) / N_FFT)  # periodic Hann
    mag = np.abs(np.fft.rfft(fr * win, axis=1))
    d = np.diff(mag, axis=0)
    flux = np.concatenate([[0.0], np.maximum(d, 0).sum(axis=1)])
    p95 = np.percentile(flux, 95) if len(flux) else 0.0
    flux = np.clip(flux / p95, 0, 1) if p95 > 0 else np.zeros_like(flux)

    e = 0.6 * loud + 0.4 * flux
    fps = sr / HOP
    e = moving_average(e, round(SMOOTH_S * fps))
    times = (np.arange(len(e)) * HOP + N_FFT / 2) / sr

    if len(e) and e.max() > 0:
        keep = np.where(e >= 0.05 * e.max())[0]
        e, times = e[keep[0]: keep[-1] + 1], times[keep[0]: keep[-1] + 1]
    return times, e


def energy_curve(path):
    """-> (times [s], energy 0..1-ish) for an audio file."""
    return energy_from_signal(load_audio(path))


def per_second(times, e):
    """Resample to 1 point per second, starting at the first kept frame. Returns (t0, values)."""
    if len(e) == 0:
        return 0.0, np.zeros(0)
    t0 = float(times[0])
    grid = np.arange(t0, times[-1] + 1e-9, 1.0)
    return t0, np.interp(grid, times, e)


def rhythm(path_or_y, sr=SR):
    """Tempo, beat times and onset times (librosa). Used for alignment snapping and crossfade points."""
    import librosa

    y = load_audio(path_or_y) if not isinstance(path_or_y, np.ndarray) else path_or_y
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
    return float(np.atleast_1d(tempo)[0]), np.asarray(beats, float), np.asarray(onsets, float)
