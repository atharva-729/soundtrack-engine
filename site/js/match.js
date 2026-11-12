// Port of engine/match.py: normalise (resample to 200 + z-score), banded DTW (+-10, cost / path length),
// DTW path + alignment (data step -> song second). Also used inside the Web Worker (via its source text).
(function (root) {
  const N = 200, BAND = 10;

  function resample(v, n) {
    const out = new Float64Array(n), L = v.length;
    if (L === 0) return out;
    if (L === 1) { out.fill(v[0]); return out; }
    for (let i = 0; i < n; i++) {
      const p = i * (L - 1) / (n - 1), lo = Math.floor(p), hi = Math.min(lo + 1, L - 1);
      out[i] = v[lo] + (v[hi] - v[lo]) * (p - lo);
    }
    return out;
  }

  function normalise(v, n = N) {
    const r = resample(v, n);
    let m = 0; for (const x of r) m += x; m /= n;
    let s = 0; for (const x of r) s += (x - m) * (x - m); s = Math.sqrt(s / n);
    if (s < 1e-6) return null;
    for (let i = 0; i < n; i++) r[i] = (r[i] - m) / s;
    return r;
  }

  // banded DTW; b is read from `buf` at offset `off` with scale `scale` (int8 index) or plain array
  function dtw(a, b, off = 0, scale = 1, band = BAND) {
    const n = a.length;
    let Dp = new Float64Array(n).fill(Infinity), Lp = new Float64Array(n);
    let Dc = new Float64Array(n).fill(Infinity), Lc = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      const lo = Math.max(0, i - band), hi = Math.min(n - 1, i + band);
      for (let j = Math.max(0, lo - 1); j <= Math.min(n - 1, hi + 1); j++) Dc[j] = Infinity;
      for (let j = lo; j <= hi; j++) {
        const d = a[i] - b[off + j] * scale, c = d * d;
        if (i === 0 && j === 0) { Dc[0] = c; Lc[0] = 1; continue; }
        let best = Infinity, bl = 0;
        if (i > 0 && j > 0) { best = Dp[j - 1]; bl = Lp[j - 1]; }
        if (i > 0 && Dp[j] < best) { best = Dp[j]; bl = Lp[j]; }
        if (j > 0 && Dc[j - 1] < best) { best = Dc[j - 1]; bl = Lc[j - 1]; }
        Dc[j] = c + best; Lc[j] = bl + 1;
      }
      let t = Dp; Dp = Dc; Dc = t; t = Lp; Lp = Lc; Lc = t;
    }
    return Dp[n - 1] / Lp[n - 1];
  }

  function dtwPath(a, b, band = BAND) {
    const n = a.length, m = b.length, W = m + 1;
    const D = new Float64Array((n + 1) * W).fill(Infinity);
    D[0] = 0;
    for (let i = 1; i <= n; i++) {
      const jc = Math.round(i * m / n), lo = Math.max(1, jc - band), hi = Math.min(m, jc + band);
      for (let j = lo; j <= hi; j++) {
        const d = a[i - 1] - b[j - 1];
        D[i * W + j] = d * d + Math.min(D[(i - 1) * W + j - 1], D[(i - 1) * W + j], D[i * W + j - 1]);
      }
    }
    let i = n, j = m; const path = [];
    while (i > 0 && j > 0) {
      path.push([i - 1, j - 1]);
      const dg = D[(i - 1) * W + j - 1], up = D[(i - 1) * W + j], lf = D[i * W + j - 1];
      if (dg <= up && dg <= lf) { i--; j--; } else if (up <= lf) i--; else j--;
    }
    path.reverse();
    return { cost: D[n * W + m] / path.length, path };
  }

  // data values (any length) + song per-second curve -> step_to_sec for each data step
  function align(dataVals, songCurve, songT0) {
    const a = normalise(dataVals), b = normalise(songCurve);
    if (!a || !b) return null;
    const { cost, path } = dtwPath(a, b);
    const sum = new Float64Array(N), cnt = new Float64Array(N);
    for (const [i, j] of path) { sum[i] += j; cnt[i]++; }
    const songIdx = new Float64Array(N);
    let run = -Infinity;
    for (let i = 0; i < N; i++) { run = Math.max(run, sum[i] / cnt[i]); songIdx[i] = run; }
    const L = songCurve.length;
    const sec200 = Array.from(songIdx, s => songT0 + s * (L - 1) / (N - 1));
    const ns = dataVals.length, out = new Float64Array(ns);
    for (let k = 0; k < ns; k++) {
      const p = k * (N - 1) / Math.max(1, ns - 1), lo = Math.floor(p), hi = Math.min(lo + 1, N - 1);
      out[k] = sec200[lo] + (sec200[hi] - sec200[lo]) * (p - lo);
      if (k) out[k] = Math.max(out[k], out[k - 1]);
    }
    return { cost, stepToSec: out };
  }

  function matchPct(d, calib) {
    if (!calib) return null;
    let k = 0; while (k < calib.length && calib[k] <= d) k++;
    return Math.round(1000 * (1 - k / calib.length)) / 10;
  }

  root.Match = { N, BAND, resample, normalise, dtw, dtwPath, align, matchPct };
})(typeof self !== 'undefined' ? self : this);
