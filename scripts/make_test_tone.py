"""Synthetic test audio with a known build (NOT a real song): 120 s at 22.05 kHz.
Quiet sine pad that slowly grows, with noise bursts whose rate and level rise towards the end,
then a short hush and a final loud burst. Used for the Python/JS parity test.
"""
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
SR = 22050


def make(path=ROOT / "site" / "test" / "test_tone.wav", seconds=120, seed=3):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SR)) / SR
    x = t / seconds
    env = 0.02 + 0.5 * x ** 2
    env[(x > 0.82) & (x < 0.88)] = 0.02          # hush
    pad = env * (np.sin(2 * np.pi * 220 * t) + 0.5 * np.sin(2 * np.pi * 330 * t))
    bursts = np.zeros_like(t)
    rate = 0.5 + 6 * x                              # bursts per second, rising
    phase = np.cumsum(rate) / SR
    gate = (phase % 1.0) < 0.15
    bursts[gate] = rng.standard_normal(gate.sum()) * (0.05 + 0.5 * x[gate] ** 2)
    bursts[(x > 0.82) & (x < 0.88)] = 0
    y = np.clip(pad + bursts, -1, 1).astype(np.float32) * 0.8
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, y, SR, subtype="PCM_16")
    return path


if __name__ == "__main__":
    print(make())
