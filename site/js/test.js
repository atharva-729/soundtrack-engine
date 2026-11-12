(function () {
  const $ = s => document.querySelector(s);
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const N_TRIALS = 12;
  let trials = [], cur = 0, answers = [], heard = { A: false, B: false }, raf = null;
  const audio = $('#ta');

  function shuffle(a, rnd = Math.random) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

  function pickTrials(all) {
    // mix sources: round-robin over shuffled per-source lists
    const by = {};
    for (const t of shuffle(all.slice())) (by[t.source] = by[t.source] || []).push(t);
    const out = [], srcs = shuffle(Object.keys(by));
    while (out.length < Math.min(N_TRIALS, all.length)) for (const s of srcs) if (by[s].length && out.length < N_TRIALS) out.push(by[s].pop());
    return out.map(t => ({ ...t, engineIs: Math.random() < 0.5 ? 'A' : 'B' }));
  }

  function draw(t, map, sec) {
    const c = $('#tc'), dpr = devicePixelRatio || 1, w = c.clientWidth, h = c.clientHeight;
    c.width = w * dpr; c.height = h * dpr;
    const g = c.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, w, h);
    const aux = t.aux, n = aux.length, CLIP = 40;
    let lo = Math.min(...aux), hi = Math.max(...aux); 
    const tl = Math.min(...t.tension), th = Math.max(...t.tension);
    const pad = 12;
    const shown = map.filter(x => x <= sec).length;
    const X = i => i / (n - 1) * w;
    // tension (red) under, aux (fg) on top: both reveal as the music plays
    g.lineWidth = 2; g.strokeStyle = css('--data'); g.beginPath();
    for (let i = 0; i < shown; i++) { const y = h - pad - (t.tension[i] - tl) / ((th - tl) || 1) * (h - 2 * pad); i ? g.lineTo(X(i), y) : g.moveTo(X(i), y); }
    g.stroke();
    g.lineWidth = 1.6; g.strokeStyle = css('--fg'); g.beginPath();
    for (let i = 0; i < shown; i++) { const y = h - pad - (aux[i] - lo) / ((hi - lo) || 1) * (h - 2 * pad); i ? g.lineTo(X(i), y) : g.moveTo(X(i), y); }
    g.stroke();
    if (shown > 0) { g.fillStyle = css('--acc'); g.beginPath(); g.arc(X(shown - 1), h - pad - (aux[shown - 1] - lo) / ((hi - lo) || 1) * (h - 2 * pad), 4, 0, 7); g.fill(); }
  }

  function playAs(label) {
    const t = trials[cur], which = label === t.engineIs ? 'engine' : 'random';
    cancelAnimationFrame(raf);
    audio.src = t[which].audio; audio.currentTime = 0; audio.play();
    $('#pa').classList.toggle('playing', label === 'A'); $('#pb').classList.toggle('playing', label === 'B');
    const map = t[which].map;
    const step = () => { draw(t, map, audio.currentTime); if (!audio.paused && !audio.ended) raf = requestAnimationFrame(step); };
    audio.onended = () => {
      heard[label] = true; $('#p' + label.toLowerCase()).classList.add('heard'); $('#p' + label.toLowerCase()).classList.remove('playing');
      draw(t, map, 1e9);
      if (heard.A && heard.B) for (const b of document.querySelectorAll('.answer button')) b.disabled = false;
    };
    step();
  }

  function show() {
    const t = trials[cur];
    heard = { A: false, B: false };
    $('#tn').textContent = `Trial ${cur + 1} of ${trials.length}`;
    $('#tsrc').textContent = { stock: 'a stock market period', rain: 'a rain event' }[t.source];
    for (const b of document.querySelectorAll('.answer button')) b.disabled = true;
    for (const id of ['#pa', '#pb']) $(id).classList.remove('heard', 'playing');
    draw(t, t.engine.map, -1);
  }

  $('#pa').onclick = () => playAs('A');
  $('#pb').onclick = () => playAs('B');
  for (const b of document.querySelectorAll('.answer button')) b.onclick = () => {
    const t = trials[cur], a = b.dataset.a;
    answers.push({ trial: t.id, source: t.source, engine_was: t.engineIs, answer: a,
      choice: a === 'tie' ? 'tie' : (a === t.engineIs ? 'engine' : 'random'), heard_both: heard.A && heard.B });
    audio.pause(); cur++;
    cur < trials.length ? show() : finish();
  };

  function finish() {
    $('#trial').hidden = true; $('#done').hidden = false;
    const eng = answers.filter(a => a.choice === 'engine').length, dec = answers.filter(a => a.choice !== 'tie').length;
    $('#score').textContent = `${eng} of ${answers.length}`;
    $('#score2').textContent = `${answers.length - dec} "can't tell" · random pick preferred ${dec - eng} times`;
    const res = { test: 'soundtrack-engine-blind-v1', when: new Date().toISOString(), n: answers.length, answers };
    $('#json').value = JSON.stringify(res);
    $('#copy').onclick = () => navigator.clipboard.writeText($('#json').value).then(() => { $('#copy').textContent = 'Copied!'; });
    const ul = $('#tcredits'), seen = new Set();
    for (const t of trials) for (const k of ['engine', 'random']) if (!seen.has(t[k].credit)) { seen.add(t[k].credit); const li = document.createElement('li'); li.textContent = t[k].credit; ul.appendChild(li); }
  }

  $('#start').onclick = async () => {
    const all = await fetch('data/test_trials.json').then(r => r.json());
    trials = pickTrials(all);
    $('#intro').hidden = true; $('#trial').hidden = false;
    show();
  };
  window.__testState = () => ({ cur, answers, n: trials.length });
})();
