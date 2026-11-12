// Exact port of engine/energy.py (energy_from_signal + per_second). No libraries.
// Frames 2048 / hop 1024, RMS dB -> 0..1, spectral flux / p95 (clipped 0..1), 0.6/0.4 mix,
// ~3 s centred moving average, trim < 5% of max, resample to 1 point per second.
(function (root) {
  const SR = 22050, N_FFT = 2048, HOP = 1024, SMOOTH_S = 3.0;

  function fftMag(re, im) {
    // in-place iterative radix-2 FFT
    const n = re.length;
    for (let i = 1, j = 0; i < n; i++) {
      let bit = n >> 1;
      for (; j & bit; bit >>= 1) j ^= bit;
      j ^= bit;
      if (i < j) { let t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
    }
    for (let len = 2; len <= n; len <<= 1) {
      const ang = -2 * Math.PI / len, wr = Math.cos(ang), wi = Math.sin(ang);
      for (let i = 0; i < n; i += len) {
        let cr = 1, ci = 0;
        for (let k = 0; k < len / 2; k++) {
          const a = i + k, b = a + len / 2;
          const xr = re[b] * cr - im[b] * ci, xi = re[b] * ci + im[b] * cr;
          re[b] = re[a] - xr; im[b] = im[a] - xi; re[a] += xr; im[a] += xi;
          const t = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = t;
        }
      }
    }
    const out = new Float64Array(n / 2 + 1);
    for (let k = 0; k <= n / 2; k++) out[k] = Math.hypot(re[k], im[k]);
    return out;
  }

  function percentile(arr, p) { // numpy default (linear)
    const s = Float64Array.from(arr).sort();
    if (!s.length) return 0;
    const pos = (p / 100) * (s.length - 1), lo = Math.floor(pos), hi = Math.min(lo + 1, s.length - 1);
    return s[lo] + (s[hi] - s[lo]) * (pos - lo);
  }

  function movingAverage(x, w) {
    w = Math.max(1, Math.round(w) | 1);
    const h = (w - 1) / 2, n = x.length, out = new Float64Array(n);
    const cs = new Float64Array(n + 1);
    for (let i = 0; i < n; i++) cs[i + 1] = cs[i] + x[i];
    for (let i = 0; i < n; i++) {
      const a = Math.max(0, i - h), b = Math.min(n - 1, i + h);
      out[i] = (cs[b + 1] - cs[a]) / (b - a + 1);
    }
    return out;
  }

  function energyFromSignal(y) {
    if (y.length < N_FFT) { const z = new Float32Array(N_FFT); z.set(y); y = z; }
    const nf = 1 + Math.floor((y.length - N_FFT) / HOP);
    const loud = new Float64Array(nf), flux = new Float64Array(nf);
    const win = new Float64Array(N_FFT);
    for (let i = 0; i < N_FFT; i++) win[i] = 0.5 - 0.5 * Math.cos(2 * Math.PI * i / N_FFT);
    let prev = null;
    const re = new Float64Array(N_FFT), im = new Float64Array(N_FFT);
    for (let f = 0; f < nf; f++) {
      const o = f * HOP;
      let ss = 0;
      for (let i = 0; i < N_FFT; i++) { const v = y[o + i]; ss += v * v; re[i] = v * win[i]; im[i] = 0; }
      const rms = Math.sqrt(ss / N_FFT);
      const db = 20 * Math.log10(rms + 1e-10);
      loud[f] = (Math.min(0, Math.max(-60, db)) + 60) / 60;
      const mag = fftMag(re, im);
      if (prev) { let s = 0; for (let k = 0; k < mag.length; k++) { const d = mag[k] - prev[k]; if (d > 0) s += d; } flux[f] = s; }
      prev = mag;
    }
    const p95 = percentile(flux, 95);
    const e = new Float64Array(nf);
    for (let f = 0; f < nf; f++) {
      const fl = p95 > 0 ? Math.min(1, Math.max(0, flux[f] / p95)) : 0;
      e[f] = 0.6 * loud[f] + 0.4 * fl;
    }
    const sm = movingAverage(e, Math.round(SMOOTH_S * SR / HOP));
    const times = new Float64Array(nf);
    for (let f = 0; f < nf; f++) times[f] = (f * HOP + N_FFT / 2) / SR;
    let mx = 0; for (const v of sm) mx = Math.max(mx, v);
    let a = 0, b = nf - 1;
    if (mx > 0) { while (a < nf && sm[a] < 0.05 * mx) a++; while (b > a && sm[b] < 0.05 * mx) b--; }
    return { times: times.slice(a, b + 1), energy: sm.slice(a, b + 1) };
  }

  function perSecond(times, e) {
    if (!e.length) return { t0: 0, values: new Float64Array(0) };
    const t0 = times[0], out = [];
    for (let t = t0; t <= times[times.length - 1] + 1e-9; t += 1.0) {
      // np.interp
      let lo = 0, hi = times.length - 1;
      if (t <= times[0]) { out.push(e[0]); continue; }
      if (t >= times[hi]) { out.push(e[hi]); continue; }
      while (hi - lo > 1) { const m = (lo + hi) >> 1; if (times[m] <= t) lo = m; else hi = m; }
      const fr = (t - times[lo]) / (times[hi] - times[lo]);
      out.push(e[lo] + (e[hi] - e[lo]) * fr);
    }
    return { t0, values: Float64Array.from(out) };
  }

  async function decodeToMono22k(arrayBuffer) {
    // decode straight into a 22.05 kHz context (resampled once, like librosa.load), then average channels
    const ctx = new OfflineAudioContext(1, SR, SR);
    const buf = await ctx.decodeAudioData(arrayBuffer.slice(0));
    const n = buf.length, ch = buf.numberOfChannels, y = new Float32Array(n);
    for (let c = 0; c < ch; c++) { const d = buf.getChannelData(c); for (let i = 0; i < n; i++) y[i] += d[i] / ch; }
    return y;
  }

  root.Energy = { SR, energyFromSignal, perSecond, decodeToMono22k, movingAverage, percentile };
})(typeof self !== 'undefined' ? self : this);
