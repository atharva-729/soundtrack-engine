(function () {
  const $ = s => document.querySelector(s);
  const J = u => fetch(u).then(r => { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); });
  const AUXK = { stock: 'price', rain: 'mm' };
  const SRC_CREDIT = {
    stock: 'Data: NSE daily closes via the open-source EOD2 dataset',
    rain: 'Data: Open-Meteo.com (CC BY 4.0), ERA5 reanalysis',
  };
  const S = { showcase: null, lib: null, calib: null, hosted: null, idx: null, source: 'stock', item: null, mode: 'single', sel: 0 };
  const pFind = new Player($('#player-find'));
  let pSong = null;

  // ---------------------------------------------------------------- tabs
  for (const b of document.querySelectorAll('.tabs button')) {
    b.onclick = () => {
      for (const o of document.querySelectorAll('.tabs button')) {
        const on = o === b; o.setAttribute('aria-selected', on);
        document.getElementById(o.getAttribute('aria-controls')).hidden = !on;
      }
      if (b.id === 'tab-song' && !pSong) pSong = new Player($('#player-song'));
    };
  }
  function segOn(group, btn) { for (const x of group.querySelectorAll('button')) x.classList.toggle('on', x === btn); }

  // ---------------------------------------------------------------- data
  async function base() {
    if (!S.showcase) [S.showcase, S.lib, S.calib, S.hosted] = await Promise.all([
      J('data/showcase.json'), J('data/library.json'), J('data/calib.json'), J('data/hosted_lib.json')]);
  }
  async function index() {
    if (S.idx) return S.idx;
    const [meta, ib, ab] = await Promise.all([J('data/index_meta.json'),
      fetch('data/index.bin').then(r => r.arrayBuffer()), fetch('data/auxseries.bin').then(r => r.arrayBuffer())]);
    S.idx = { meta, q: new Int8Array(ib), aux: new Uint8Array(ab), pos: new Map(meta.ids.map((id, i) => [id, i])) };
    return S.idx;
  }
  function fromIndex(i) {
    const { meta, q, aux } = S.idx, N = meta.N;
    const tension = Array.from(q.subarray(i * N, (i + 1) * N), v => v / 31.75);
    const lo = meta.aux_min[i], hi = meta.aux_max[i];
    const a = Array.from(aux.subarray(i * N, (i + 1) * N), v => lo + v / 255 * (hi - lo));
    return { id: meta.ids[i], title: meta.title[i], source: meta.source[i], auxKind: meta.aux_kind[i], tension, aux: a,
      moments: meta.moments[i].map(([f, label]) => ({ f, label })) };
  }

  // ---------------------------------------------------------------- tab 1: data -> song
  function fillItems() {
    const sel = $('#item');
    sel.innerHTML = '';
    for (const it of S.showcase.filter(x => x.source === S.source)) {
      const o = document.createElement('option'); o.value = it.id; o.textContent = it.title; sel.appendChild(o);
    }
    showItem(S.showcase.find(x => x.id === sel.value));
  }
  for (const b of document.querySelectorAll('#sources button')) b.onclick = async () => { segOn($('#sources'), b); S.source = b.dataset.src; await base(); fillItems(); };
  $('#item').onchange = () => showItem(S.showcase.find(x => x.id === $('#item').value));
  for (const b of document.querySelectorAll('#mode button')) b.onclick = () => { if (b.disabled) return; segOn($('#mode'), b); S.mode = b.dataset.mode; play(); };

  function trackRow(rank, tid, pct, hosted, on, extra) {
    const li = document.createElement('li');
    const L = S.lib[tid] || [tid, '', '', ''];
    li.innerHTML = `<span class="rank">${rank}</span><span class="name"></span><span class="pct">${pct == null ? '' : pct.toFixed(1) + '%'}</span>`;
    li.querySelector('.name').innerHTML = `<b></b> <span class="tags"></span>`;
    li.querySelector('b').textContent = L[0];
    li.querySelector('.tags').textContent = [L[2], (L[3] || '').split(',')[0]].filter(Boolean).join(' · ') + (extra ? ' · ' + extra : '');
    if (!hosted) { const b = document.createElement('span'); b.className = 'badge'; b.textContent = 'index only'; li.insertBefore(b, li.lastChild); }
    li.classList.toggle('on', !!on);
    return li;
  }

  async function showItem(it) {
    if (!it) return;
    S.item = it; S.sel = 0;
    S.curve = await J(`data/curves/${it.id}.json`);
    $('#item-title').textContent = it.title;
    const ol = $('#tracks'); ol.innerHTML = '';
    it.singles.forEach((s, i) => {
      const li = trackRow(i + 1, s.track, s.pct, !!s.audio, i === 0);
      li.onclick = () => { S.sel = i; segOn($('#mode'), $('#mode [data-mode=single]')); S.mode = 'single'; for (const x of ol.children) x.classList.toggle('on', x === li); play(); };
      ol.appendChild(li);
    });
    const stBtn = $('#mode [data-mode=stitched]');
    stBtn.disabled = !it.stitched;
    stBtn.textContent = it.stitched ? `Stitched (${it.stitched.segments.length} tracks)` : 'Stitched';
    if (!it.stitched && S.mode === 'stitched') { S.mode = 'single'; segOn($('#mode'), $('#mode [data-mode=single]')); }
    play();
  }

  function boardFor(it, c) {
    const labels = c.steps.map(s => s.label), m = c.meta;
    if (it.source === 'stock') return { kind: 'stock', name: m.name, labels };
    if (it.source === 'rain') return { kind: 'rain', name: m.city, labels: labels.map(l => l.slice(5)) };
    return null;
  }

  function play() {
    const it = S.item, c = S.curve, aux = c.aux[AUXK[it.source]], tension = c.steps.map(s => s.v);
    const src = SRC_CREDIT[it.source], board = boardFor(it, c);
    if (S.mode === 'stitched' && it.stitched) {
      const st = it.stitched;
      pFind.load({ aux, auxKind: AUXK[it.source], tension, stepToSec: st.step_to_sec, songCurve: st.song_curve, songT0: 0,
        audio: st.audio, moments: st.moments.map(m => ({ song_s: m.song_s, label: m.label })),
        credits: [...st.credits, src], board });
    } else {
      const s = it.singles[S.sel];
      pFind.load({ aux, auxKind: AUXK[it.source], tension, stepToSec: s.step_to_sec, songCurve: s.song_curve, songT0: s.song_t0,
        audio: s.audio, moments: s.moments.map(m => ({ song_s: m.song_s, label: m.label })),
        credits: [s.credit, src], board, nohost: s.audio ? '' : 'This track is in the index only (no audio hosted here). Listen at incompetech.com.' });
    }
  }

  // ---------------------------------------------------------------- tab 2: song -> data
  let worker = null;
  async function getWorker() {
    if (worker) return worker;
    const src = await fetch('js/match.js').then(r => r.text());
    const body = `${src}
      let IDX = null, N = 200, n = 0;
      onmessage = e => {
        const m = e.data;
        if (m.type === 'index') { IDX = new Int8Array(m.buf); N = m.N; n = IDX.length / N; postMessage({ type: 'ready' }); return; }
        const q = Float64Array.from(m.q), out = [];
        for (let i = 0; i < n; i++) {
          if (m.mask && !m.mask[i]) continue;
          out.push([i, Match.dtw(q, IDX, i * N, 1 / 31.75)]);
          if (i % 500 === 0) postMessage({ type: 'progress', done: i, n });
        }
        out.sort((a, b) => a[1] - b[1]);
        postMessage({ type: 'result', top: out.slice(0, m.k || 6) });
      };`;
    const url = URL.createObjectURL(new Blob([body], { type: 'text/javascript' }));
    worker = new Worker(url);
    const ix = await index();
    await new Promise(res => { worker.onmessage = e => e.data.type === 'ready' && res(); worker.postMessage({ type: 'index', buf: ix.q.buffer.slice(0), N: ix.meta.N }); });
    return worker;
  }

  function search(q, sources, k = 6, onProgress) {
    return getWorker().then(w => new Promise(res => {
      const meta = S.idx.meta;
      const mask = sources ? Uint8Array.from(meta.source, s => sources.includes(s) ? 1 : 0) : null;
      w.onmessage = e => { if (e.data.type === 'progress') onProgress && onProgress(e.data); else if (e.data.type === 'result') res(e.data.top); };
      w.postMessage({ type: 'search', q: Array.from(q), mask, k });
    }));
  }

  async function analyse(arrayBuffer, sources, status = () => {}) {
    await base(); await index();
    status('Decoding audio…');
    const y = await Energy.decodeToMono22k(arrayBuffer);
    status('Measuring the song’s energy…');
    await new Promise(r => setTimeout(r, 20));
    const { times, energy } = Energy.energyFromSignal(y);
    const ps = Energy.perSecond(times, energy);
    const q = Match.normalise(ps.values);
    if (!q) throw new Error('This audio is too flat to match.');
    status('Searching every market moment and storm…');
    const top = await search(q, sources, 6, p => status(`Searching… ${Math.round(100 * p.done / p.n)}%`));
    return { ps, top: top.map(([i, d]) => ({ i, id: S.idx.meta.ids[i], d, pct: Match.matchPct(d, S.calib) })) };
  }

  let revSources = null;
  for (const b of document.querySelectorAll('#rev-sources button')) b.onclick = () => { segOn($('#rev-sources'), b); revSources = b.dataset.src ? [b.dataset.src] : null; };

  let objUrl = null;
  $('#song-file').onchange = async e => {
    const f = e.target.files[0];
    if (!f) return;
    const st = $('#song-status');
    try {
      const res = await analyse(await f.arrayBuffer(), revSources, s => { st.textContent = s; });
      if (objUrl) URL.revokeObjectURL(objUrl);
      objUrl = URL.createObjectURL(f);
      st.textContent = '';
      showReverse(res, f.name, objUrl, 0);
    } catch (err) { st.textContent = '⚠ ' + err.message; }
  };

  function showReverse(res, name, url, k) {
    if (!pSong) pSong = new Player($('#player-song'));
    const r = res.top[k], c = fromIndex(r.i);
    $('#song-result').hidden = false;
    $('#rev-title').textContent = c.title;
    $('#rev-pct').innerHTML = `<span class="pct">${r.pct.toFixed(1)}% match</span> · ${{ stock: 'market moment', rain: 'rain event' }[c.source]}`;
    const al = Match.align(c.tension, res.ps.values, res.ps.t0);
    const n = c.tension.length;
    pSong.load({ aux: c.aux, auxKind: c.auxKind, tension: c.tension, stepToSec: al.stepToSec, songCurve: Array.from(res.ps.values),
      songT0: res.ps.t0, audio: url, moments: c.moments.map(m => ({ label: m.label, song_s: al.stepToSec[Math.round(m.f * (n - 1))] })),
      credits: [`Your audio: ${name} (played from your device only)`, SRC_CREDIT[c.source]] });
    const line = `My song "${name.replace(/\.[^.]+$/, '')}" is ${c.title}: ${r.pct.toFixed(0)}% match on Soundtrack Engine.`;
    $('#share-line').textContent = line;
    $('#share-copy').onclick = () => navigator.clipboard.writeText(line + ' ' + location.href.split('#')[0]).then(() => { $('#share-copy').textContent = 'Copied'; setTimeout(() => $('#share-copy').textContent = 'Copy', 1500); });
    const ol = $('#runners'); ol.innerHTML = '';
    res.top.forEach((x, j) => {
      if (j === k) return;
      const li = document.createElement('li');
      li.innerHTML = `<span class="rank">${j + 1}</span><span class="name"></span><span class="pct">${x.pct.toFixed(1)}%</span>`;
      li.querySelector('.name').textContent = S.idx.meta.title[x.i];
      li.onclick = () => showReverse(res, name, url, j);
      ol.appendChild(li);
    });
  }

  // parity hook (used by the automated Python/JS parity test; same code path as an upload)
  window.__parity = async (url, sources) => {
    const ab = await fetch(url).then(r => r.arrayBuffer());
    const res = await analyse(ab, sources || null);
    return { t0: res.ps.t0, curve: Array.from(res.ps.values), top: res.top.slice(0, 5).map(x => [x.id, x.d]) };
  };

  // ---------------------------------------------------------------- boot
  base().then(fillItems).catch(err => { $('#item-title').textContent = 'Could not load data: ' + err.message; });
})();
