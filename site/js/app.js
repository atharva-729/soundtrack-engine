(function () {
  const $ = s => document.querySelector(s);
  const J = u => fetch(u).then(r => { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); });
  const AUXK = { stock: 'price', rain: 'mm', energy: 'gw', machine: 'temp', crop: 'yield', gdp: 'gdp' };
  const SRC_CREDIT = {
    stock: 'Data: NSE daily closes via the open-source EOD2 dataset',
    rain: 'Data: Open-Meteo.com (CC BY 4.0), ERA5 reanalysis',
    energy: 'Data: UK generation by fuel type, Elexon BMRS (Elexon Open Data Licence)',
    machine: 'Data: NASA C-MAPSS turbofan run-to-failure simulation (Saxena & Goebel 2008, public domain)',
    crop: 'Data: World Bank Open Data (CC BY 4.0), cereal yield from FAO',
    gdp: 'Data: World Bank Open Data (CC BY 4.0); US quarterly GDP: BEA via FRED',
  };
  const SRC_NAME = { stock: 'Stocks', rain: 'Rain', energy: 'Energy', machine: 'Machines', crop: 'Crops', gdp: 'Economy' };
  const S = { showcase: null, lib: null, calib: null, hosted: null, idx: null, item: null, len: '30', mode: 'single', sel: 0,
    fSrc: '', fShape: '' };
  const pFind = new Player($('#player-find'));
  let pSong = null;

  // ---------------------------------------------------------------- tabs
  for (const b of document.querySelectorAll('.tabs button')) {
    b.onclick = () => {
      for (const o of document.querySelectorAll('.tabs button')) {
        const on = o === b; o.setAttribute('aria-selected', on);
        document.getElementById(o.getAttribute('aria-controls')).hidden = !on;
      }
      if (b.id === 'tab-song') { pFind.audio.pause(); if (!pSong) pSong = new Player($('#player-song')); else pSong.autoplaySoon(); }
      else { if (pSong) pSong.audio.pause(); pFind.autoplaySoon(); }
    };
  }
  function hostOf(u) { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return 'the source site'; } }
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

  // ---------------------------------------------------------------- tab 1: catalog of examples
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const dmy = iso => { const [y, m, d] = iso.split('-').map(Number); return { y, m: MON[m - 1], d }; };
  function title(it) {
    if (it.source === 'rain') {
      const a = dmy(it.meta.start), b = dmy(it.meta.end);
      return `${it.meta.city} rain, ${a.d}${a.m !== b.m ? ' ' + a.m : ''}–${b.d} ${b.m} ${b.y}`;
    }
    return it.title.replace(/ · (drama|shape)$/, '').replace(' - ', ' – ');
  }
  function subtitle(it) {
    const m = it.meta;
    if (it.source === 'rain') return `${it.n_steps} hours · ${Math.round(m.total_mm).toLocaleString('en-IN')} mm of rain in total`;
    if (it.source === 'energy') return `${it.n_steps} hours · wind from ${m.low_gw} to ${m.peak_gw} GW · Great Britain`;
    if (it.source === 'machine') return `${m.cycles} operating cycles · tension = wear, from like-new to failure · simulated engine (NASA)`;
    if (it.source === 'crop') return `${it.n_steps} harvests · tension = how far a harvest falls short`;
    if (it.source === 'gdp') return `${it.n_steps} ${m.freq === 'quarterly' ? 'quarters' : 'years'} · tension = how eventful the economy was`;
    const a = dmy(it.meta.start), b = dmy(it.meta.end);
    return `${a.m} ${a.y} – ${b.m} ${b.y} · ${it.n_steps} trading days · ` +
      (it.meta.kind === 'drama' ? 'tension = how eventful the market was' : 'tension = the price itself');
  }

  // A one-word description of the tension curve's shape, so cards can be filtered by pattern.
  function shapeOf(v) {
    const n = v.length, mean = v.reduce((a, x) => a + x, 0) / n;
    const sd = Math.sqrt(v.reduce((a, x) => a + (x - mean) ** 2, 0) / n) || 1;
    const corr = v.reduce((a, x, i) => a + (x - mean) * (i / (n - 1) - .5), 0) / (n * sd * Math.sqrt(1 / 12));
    if (corr > .7) return 'Slow build';
    if (corr < -.7) return 'Fades away';
    // separate peaks: tops above 0.7 with a dip below 0.4 between them
    let peaks = 0, armed = true;
    for (const x of v) { if (armed && x >= .7) { peaks++; armed = false; } else if (x <= .4) armed = true; }
    if (peaks >= 3) return 'Rollercoaster';
    if (peaks === 2) return 'Twin peaks';
    const pos = v.indexOf(Math.max(...v)) / (n - 1);
    return pos < .34 ? 'Early shock' : pos < .67 ? 'Mid-story peak' : 'Late climax';
  }

  function sizeCanvas(c) {
    const dpr = window.devicePixelRatio || 1, w = c.clientWidth, h = c.clientHeight;
    c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
    const g = c.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); return [g, w, h];
  }
  function drawThumb(c, th) {
    const [g, w, h] = sizeCanvas(c), css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
    const pad = 6, X = i => pad + i / (th.v.length - 1) * (w - 2 * pad);
    g.beginPath(); g.moveTo(X(0), h);
    th.v.forEach((y, i) => g.lineTo(X(i), h - pad - y * (h - 2 * pad)));
    g.lineTo(X(th.v.length - 1), h); g.closePath();
    g.fillStyle = css('--data'); g.globalAlpha = .22; g.fill(); g.globalAlpha = 1;
    const lo = Math.min(...th.aux), hi = Math.max(...th.aux);
    g.beginPath(); g.strokeStyle = css('--fg'); g.lineWidth = 1.6; g.lineJoin = 'round';
    th.aux.forEach((y, i) => { const yy = h - pad - (y - lo) / ((hi - lo) || 1) * (h - 2 * pad); i ? g.lineTo(X(i), yy) : g.moveTo(X(i), yy); });
    g.stroke();
    const pk = th.v.indexOf(Math.max(...th.v));
    g.fillStyle = css('--song'); g.beginPath(); g.arc(X(pk), h - pad - th.v[pk] * (h - 2 * pad), 3.5, 0, 7); g.fill();
  }

  function filters() {
    const srcs = [...new Set(S.showcase.map(x => x.source))];
    const fs = $('#f-src'); fs.innerHTML = '';
    for (const [k, label] of [['', 'All'], ...srcs.map(x => [x, SRC_NAME[x] || x])]) {
      const b = document.createElement('button'); b.textContent = label; b.dataset.src = k; b.classList.toggle('on', k === S.fSrc);
      b.onclick = () => { S.fSrc = k; segOn(fs, b); renderCards(); };
      fs.appendChild(b);
    }
    const shapes = [...new Set(S.showcase.map(x => x.shape))].sort();
    const fp = $('#f-shape'); fp.innerHTML = '<span class="chips-lab">Shape</span>';
    for (const k of ['', ...shapes]) {
      const b = document.createElement('button'); b.className = 'chip'; b.textContent = k || 'Any'; b.classList.toggle('on', k === S.fShape);
      b.onclick = () => { S.fShape = k; for (const x of fp.querySelectorAll('.chip')) x.classList.toggle('on', x === b); renderCards(); };
      fp.appendChild(b);
    }
  }

  function renderCards() {
    const box = $('#cards'); box.innerHTML = '';
    const list = S.showcase.filter(x => (!S.fSrc || x.source === S.fSrc) && (!S.fShape || x.shape === S.fShape));
    for (const it of list) {
      const a = document.createElement('a');
      a.className = 'card'; a.href = '#' + it.id;
      const top = it.short && it.short['30'] && it.short['30'][0];
      a.innerHTML = `<canvas class="thumb" aria-hidden="true"></canvas><div class="c-body">
        <div class="c-chips"><span class="chip src"></span><span class="chip shape"></span></div>
        <h3></h3><p class="c-sub"></p><p class="c-top"></p></div>`;
      a.querySelector('.src').textContent = SRC_NAME[it.source];
      a.querySelector('.shape').textContent = it.shape;
      a.querySelector('h3').textContent = title(it);
      a.querySelector('.c-sub').textContent = subtitle(it).split(' · ').slice(0, 2).join(' · ');
      a.querySelector('.c-top').textContent = top ? '♪ ' + top.title : '';
      box.appendChild(a);
      requestAnimationFrame(() => drawThumb(a.querySelector('canvas'), it.thumb));
    }
    if (!list.length) box.innerHTML = '<p class="empty">No examples with that shape here. Try another filter.</p>';
  }
  let rT; window.addEventListener('resize', () => { clearTimeout(rT); rT = setTimeout(() => { if (!$('#catalog').hidden) renderCards(); }, 150); });

  // ---------------------------------------------------------------- detail view
  const FIT = c => c < 0.05 ? 'tight fit' : c < 0.15 ? 'good fit' : 'loose fit';
  const LEN_NOTE = {
    10: 'The dramatic part of the 30-second version: the same music, cut around the event\'s biggest moment.',
    30: 'The whole event over the best-fitting 30 seconds of any track in the library.',
    full: 'The whole event spread over the best-fitting complete track.',
  };

  async function route() {
    await base();
    const it = S.showcase.find(x => x.id === decodeURIComponent(location.hash.slice(1)));
    if (it) {
      if ($('#tab-find').getAttribute('aria-selected') !== 'true') $('#tab-find').click();
      $('#catalog').hidden = true; $('#detail').hidden = false;
      await showItem(it);
      window.scrollTo({ top: $('.tabs').offsetTop - 8 });
    } else {
      pFind.audio.pause();
      $('#detail').hidden = true; $('#catalog').hidden = false;
      renderCards();
    }
  }
  window.addEventListener('hashchange', route);

  for (const b of document.querySelectorAll('#len button')) b.onclick = () => { segOn($('#len'), b); S.len = b.dataset.len; S.sel = 0; S.mode = 'single'; renderTracks(); play(); };
  for (const b of document.querySelectorAll('#mode button')) b.onclick = () => { if (b.disabled) return; segOn($('#mode'), b); S.mode = b.dataset.mode; renderTracks(); play(); };

  function trackRow(rank, tid, right, hosted, on, extra) {
    const li = document.createElement('li');
    const L = S.lib[tid] || [tid, '', '', ''];
    li.innerHTML = `<span class="rank">${rank}</span><span class="name"></span><span class="pct"></span>`;
    li.querySelector('.pct').textContent = right || '';
    li.querySelector('.name').innerHTML = `<b></b> <span class="tags"></span>`;
    li.querySelector('b').textContent = L[0];
    li.querySelector('.tags').textContent = [L[2], (L[3] || '').split(',')[0]].filter(Boolean).join(' · ') + (extra ? ' · ' + extra : '');
    if (!hosted) { const b = document.createElement('span'); b.className = 'badge'; b.textContent = 'index only'; li.insertBefore(b, li.lastChild); }
    li.classList.toggle('on', !!on);
    return li;
  }

  function renderTracks() {
    const it = S.item, ol = $('#tracks'); ol.innerHTML = '';
    const full = S.len === 'full';
    const rows = full ? it.singles.map(s => [s.track, s.pct.toFixed(1) + '%', !!s.audio, ''])
      : it.short[S.len].map(s => [s.track, FIT(s.cost), true, 'from ' + fmtTime(s.cut_start)]);
    rows.forEach(([tid, right, hosted, extra], i) => {
      const li = trackRow(i + 1, tid, right, hosted, i === S.sel && S.mode === 'single', extra);
      li.onclick = () => { S.sel = i; S.mode = 'single'; segOn($('#mode'), $('#mode [data-mode=single]')); for (const x of ol.children) x.classList.toggle('on', x === li); play(); };
      ol.appendChild(li);
    });
    $('#mode').hidden = !full;
    const stBtn = $('#mode [data-mode=stitched]');
    stBtn.disabled = !it.stitched;
    stBtn.textContent = it.stitched ? `Stitched (${it.stitched.segments.length} tracks)` : 'Stitched';
    segOn($('#mode'), $(`#mode [data-mode=${S.mode}]`));
    $('.len-note').textContent = LEN_NOTE[S.len];
  }

  async function showItem(it) {
    S.item = it; S.sel = 0; S.mode = 'single';
    S.curve = await J(`data/curves/${it.id}.json`);
    $('#item-title').textContent = title(it);
    $('.d-sub').textContent = subtitle(it);
    $('.d-chips').innerHTML = '<span class="chip src"></span><span class="chip shape"></span>';
    $('.d-chips .src').textContent = SRC_NAME[it.source];
    $('.d-chips .shape').textContent = it.shape;
    renderTracks();
    play();
  }

  function boardFor(it, c) {
    const labels = c.steps.map(s => s.label), m = c.meta;
    if (it.source === 'stock') return { kind: 'stock', name: m.name, labels };
    if (it.source === 'rain') return { kind: 'rain', name: m.city, labels: labels.map(l => l.slice(5)) };
    if (it.source === 'energy') return { kind: 'energy', name: 'UK wind', labels, x: c.aux };
    if (it.source === 'machine') return { kind: 'machine', name: 'Engine ' + m.unit, labels, x: c.aux };
    if (it.source === 'crop') return { kind: 'crop', name: m.country, labels, x: c.aux };
    if (it.source === 'gdp') return { kind: 'gdp', name: m.country, labels, x: c.aux, quarterly: m.freq === 'quarterly' };
    return null;
  }

  function play() {
    const it = S.item, c = S.curve, aux = c.aux[AUXK[it.source]], tension = c.steps.map(s => s.v);
    const src = c.meta.credit ? 'Data: ' + c.meta.credit : SRC_CREDIT[it.source], board = boardFor(it, c);
    const common = { aux, auxKind: AUXK[it.source], tension, board, explain: c.explain };
    if (S.len !== 'full') {
      const s = it.short[S.len][S.sel];
      pFind.load({ ...common, stepToSec: s.step_to_sec, songCurve: s.song_curve, songT0: s.song_t0, audio: s.audio,
        moments: s.moments.map(m => ({ song_s: m.song_s, label: m.label })),
        credits: [`${s.credit} (${S.len}-second excerpt from ${fmtTime(s.cut_start)})`, src] });
    } else if (S.mode === 'stitched' && it.stitched) {
      const st = it.stitched;
      pFind.load({ ...common, stepToSec: st.step_to_sec, songCurve: st.song_curve, songT0: 0,
        audio: st.audio, moments: st.moments.map(m => ({ song_s: m.song_s, label: m.label })),
        credits: [...st.credits, src] });
    } else {
      const s = it.singles[S.sel];
      pFind.load({ ...common, stepToSec: s.step_to_sec, songCurve: s.song_curve, songT0: s.song_t0,
        audio: s.audio, moments: s.moments.map(m => ({ song_s: m.song_s, label: m.label })),
        credits: [s.credit, src], nohost: s.audio ? '' : `This track is in the index only (no audio hosted here). Listen at ${hostOf(s.source_url)}.` });
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
    status('Searching every event…');
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
    $('#rev-pct').innerHTML = `<span class="pct">${r.pct.toFixed(1)}% match</span> · ${{ stock: 'market moment', rain: 'rain event', energy: 'week of wind power', machine: 'engine life', crop: 'harvest history', gdp: 'stretch of an economy' }[c.source]}`;
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
  base().then(() => { for (const it of S.showcase) it.shape = shapeOf(it.thumb.v); filters(); return route(); })
    .catch(err => { $('#cards').textContent = 'Could not load data: ' + err.message; });
})();
