// One playhead through everything: data chart (top), tension vs song energy overlay (middle), moments, credits.
// x axis = song time. Data steps are placed at their aligned song second (step_to_sec).
(function (root) {
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const fmt = s => { s = Math.max(0, s || 0); return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`; };

  function minmax(a) {
    let lo = Infinity, hi = -Infinity;
    for (const v of a) { if (v < lo) lo = v; if (v > hi) hi = v; }
    return [lo, hi === lo ? lo + 1 : hi];
  }

  class Player {
    constructor(host) {
      this.host = host;
      host.innerHTML = '';
      host.appendChild(document.getElementById('player-tpl').content.cloneNode(true));
      const q = s => host.querySelector(s);
      Object.assign(this, {
        cData: q('.c-data'), cOver: q('.c-overlay'), audio: q('audio'), bPlay: q('.b-play'), seek: q('.seek'),
        time: q('.time'), momentsEl: q('.moments'), creditsEl: q('.credits ul'), card: q('.moment-card'),
        nohost: q('.nohost'), lAux: q('.l-aux'), jumbo: q('.jumbo'), listen: q('.listen'), lt: q('.listen .lt'),
      });
      this.prevT = 0;
      this.bPlay.onclick = () => this.toggle();
      q('.b-back').onclick = () => this.seekTo(this.audio.currentTime - 10);
      q('.b-fwd').onclick = () => this.seekTo(this.audio.currentTime + 10);
      this.seek.oninput = () => this.seekTo(this.seek.value / 1000 * this.duration());
      for (const c of [this.cData, this.cOver]) {
        c.addEventListener('pointerdown', e => {
          const r = c.getBoundingClientRect();
          this.seekTo((e.clientX - r.left) / r.width * this.duration());
        });
      }
      this.audio.addEventListener('play', () => { this.bPlay.textContent = '❚❚'; this.bPlay.setAttribute('aria-label', 'Pause'); this.loop(); });
      this.audio.addEventListener('pause', () => { this.bPlay.textContent = '▶'; this.bPlay.setAttribute('aria-label', 'Play'); });
      this.audio.addEventListener('loadedmetadata', () => this.draw());
      this.audio.addEventListener('timeupdate', () => { if (this.audio.paused) this.tick(); });
      this.ro = new ResizeObserver(() => this.draw());
      this.ro.observe(this.cData);
    }

    load(o) {
      // o: {aux, auxKind, tension, stepToSec, songCurve, songT0, audio, moments:[{song_s,label}], credits, nohost}
      this.o = o;
      this.audio.pause();
      if (o.audio) { this.audio.src = o.audio; this.audio.preload = 'metadata'; } else { this.audio.removeAttribute('src'); }
      this.bPlay.disabled = !o.audio;
      this.nohost.hidden = !o.nohost; this.nohost.textContent = o.nohost || '';
      this.lAux.textContent = { price: 'price', mm: 'rain (mm / hour)' }[o.auxKind] || '';
      this.momentsEl.innerHTML = '';
      this.moments = (o.moments || []).slice().sort((a, b) => a.song_s - b.song_s);
      for (const m of this.moments) {
        const li = document.createElement('li');
        li.innerHTML = `<span class="ts">${fmt(m.song_s)}</span><span></span>`;
        li.lastChild.textContent = m.label;
        li.onclick = () => { this.seekTo(Math.max(0, m.song_s - 3)); if (this.audio.paused && o.audio) this.audio.play(); };
        m.el = li;
        this.momentsEl.appendChild(li);
      }
      this.creditsEl.innerHTML = '';
      for (const c of o.credits || []) { const li = document.createElement('li'); li.textContent = c; this.creditsEl.appendChild(li); }
      this.card.hidden = true;
      this.prevT = 0;
      this.jumbo.hidden = !o.board;
      this.lastStep = -1;
      this.renderBoard(0);
      this.draw();
    }

    stepAt(t) {
      const s = this.o.stepToSec; if (!s || !s.length) return 0;
      if (t <= s[0]) return 0;
      let lo = 0, hi = s.length - 1;
      while (hi - lo > 1) { const m = (lo + hi) >> 1; if (s[m] <= t) lo = m; else hi = m; }
      return s[hi] <= t ? hi : lo;
    }

    songEnergyAt(t) {
      const o = this.o, c = o.songCurve; if (!c || !c.length) return 0;
      const k = Math.max(0, Math.min(c.length - 1, Math.round(t - (o.songT0 || 0)))); return c[k];
    }

    renderBoard(t) {
      const o = this.o; if (!o) return;
      const i = this.stepAt(t), b = o.board;
      if (b && i !== this.lastStep) {
        const J = this.jumbo, nm = J.querySelectorAll('.nm'), sc = J.querySelectorAll('.sc'), ex = J.querySelectorAll('.ex');
        const set = (el, v) => { v = String(v); if (el.textContent !== v) el.textContent = v; };
        let wl = 50;
        if (b.kind === 'stock') {
          const p0 = o.aux[0], p = o.aux[i], ch = (p / p0 - 1) * 100, lo = Math.min(...o.aux), hi = Math.max(...o.aux);
          const peak = Math.max(...o.aux.slice(0, i + 1));
          nm[0].textContent = b.name; set(sc[0], p.toLocaleString('en-IN', { maximumFractionDigits: 0 })); ex[0].textContent = 'close';
          nm[1].textContent = 'since start'; set(sc[1], (ch >= 0 ? '+' : '') + ch.toFixed(1) + '%'); ex[1].textContent = 'day ' + (i + 1) + ' of ' + o.aux.length;
          J.querySelector('.clk').textContent = b.labels[i];
          J.querySelector('.sub').textContent = 'down ' + (100 * (1 - p / peak)).toFixed(1) + '% from its high so far';
          wl = 100 * (p - lo) / ((hi - lo) || 1);
        } else if (b.kind === 'rain') {
          const mm = o.aux[i], tot = o.aux.slice(0, i + 1).reduce((a, x) => a + x, 0), mx = Math.max(...o.aux);
          nm[0].textContent = b.name; set(sc[0], mm.toFixed(1)); ex[0].textContent = 'mm this hour';
          nm[1].textContent = 'total so far'; set(sc[1], tot.toFixed(0)); ex[1].textContent = 'mm';
          J.querySelector('.clk').textContent = b.labels[i];
          J.querySelector('.sub').textContent = mm >= 0.6 * mx ? 'downpour' : mm >= 0.25 * mx ? 'heavy rain' : mm > 0.2 ? 'rain' : 'calm';
          wl = 100 * mm / (mx || 1);
        }
        J.querySelector('.bl').style.width = wl + '%'; J.querySelector('.br').style.width = (100 - wl) + '%';
        this.lastStep = i;
      }
      this.jumbo.classList.toggle('on', !this.audio.paused);
      this.renderCue(t, i);
    }

    renderCue(t, i) {
      const ms = this.moments || [], L = this.listen, o = this.o;
      if (!o || !ms.length) return;
      const fmtS = s => s < 60 ? Math.ceil(s) + 's' : fmt(s);
      const short = l => l.replace(/^.*? · /, '').replace(/^\(:?[0-9:]+\) /, '').slice(0, 120).replace(/[.\s]+$/, '');
      const rises = m => this.songEnergyAt(m.song_s) >= this.songEnergyAt(m.song_s - 6);
      const now = ms.find(m => t >= m.song_s - 0.3 && t < m.song_s + 3.5);
      const next = ms.find(m => m.song_s - 0.3 > t);
      L.classList.remove('soon', 'now');
      if (now) {
        L.classList.add('now');
        this.lt.textContent = 'NOW: ' + short(now.label) + '. ' + (rises(now) ? 'Hear the music hit its peak.' : 'Hear the music break.');
      } else if (next) {
        const dt = next.song_s - t;
        if (dt < 12) L.classList.add('soon');
        this.lt.innerHTML = '<span class="cd">in ' + fmtS(dt) + '</span> ';
        this.lt.append(short(next.label) + '. ' + (rises(next) ? 'Listen for the music building up to it.' : 'Listen for the music dropping away as it lands.'));
      } else {
        this.lt.textContent = i > o.tension.length * 0.9 ? 'Final stretch: the music resolves as the story ends.' : 'No more big moments. Follow the red and blue lines moving together.';
      }
    }

    duration() {
      const d = this.audio.duration;
      if (isFinite(d) && d > 0) return d;
      const o = this.o || {};
      const last = o.stepToSec ? o.stepToSec[o.stepToSec.length - 1] : 0;
      return Math.max(last + 2, (o.songT0 || 0) + (o.songCurve ? o.songCurve.length : 0));
    }

    toggle() { if (!this.o || !this.o.audio) return; this.audio.paused ? this.audio.play() : this.audio.pause(); }

    seekTo(t) {
      t = Math.max(0, Math.min(this.duration() - 0.05, t));
      if (this.o && this.o.audio) this.audio.currentTime = t;
      this.prevT = t;
      this.fakeT = t;
      this.tick(true);
    }

    loop() { this.tick(); if (!this.audio.paused) requestAnimationFrame(() => this.loop()); }

    current() { return this.o && this.o.audio ? this.audio.currentTime : (this.fakeT || 0); }

    tick(jump) {
      const t = this.current(), d = this.duration();
      this.seek.value = Math.round(1000 * t / d);
      this.time.textContent = `${fmt(t)} / ${fmt(d)}`;
      if (!jump) {
        for (const m of this.moments || []) if (this.prevT < m.song_s && m.song_s <= t) this.showCard(m);
      }
      for (const m of this.moments || []) m.el.classList.toggle('past', m.song_s <= t);
      this.renderBoard(t);
      this.prevT = t;
      this.draw();
    }

    showCard(m) {
      this.card.textContent = '⚡ ' + m.label;
      this.card.hidden = false;
      this.card.style.animation = 'none'; void this.card.offsetWidth; this.card.style.animation = '';
      clearTimeout(this.cardTimer);
      this.cardTimer = setTimeout(() => { this.card.hidden = true; }, 4500);
    }

    sizeCanvas(c) {
      const dpr = window.devicePixelRatio || 1, w = c.clientWidth || 600, h = c.clientHeight || +c.getAttribute('height');
      if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); }
      const g = c.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0);
      return [g, w, h];
    }

    line(g, xs, ys, w, h, pad, color, width, lo, hi, d) {
      g.beginPath(); g.strokeStyle = color; g.lineWidth = width; g.lineJoin = 'round';
      for (let i = 0; i < xs.length; i++) {
        const x = xs[i] / d * w, y = h - pad - (ys[i] - lo) / (hi - lo) * (h - 2 * pad);
        i ? g.lineTo(x, y) : g.moveTo(x, y);
      }
      g.stroke();
    }

    draw() {
      if (!this.o) return;
      const o = this.o, d = this.duration(), t = this.current();
      const fg = css('--mut'), line = css('--line'), dc = css('--data'), sc = css('--song'), ac = css('--acc2');
      // --- data chart
      let [g, w, h] = this.sizeCanvas(this.cData);
      g.clearRect(0, 0, w, h);
      const pad = 12;
      if (o.aux && o.aux.length) {
        let [lo, hi] = minmax(o.aux);
        const xs = o.aux.map((_, i) => o.stepToSec[Math.min(i, o.stepToSec.length - 1)]);
        // filled area
        g.beginPath();
        for (let i = 0; i < xs.length; i++) {
          const x = xs[i] / d * w, y = h - pad - (o.aux[i] - lo) / (hi - lo) * (h - 2 * pad);
          i ? g.lineTo(x, y) : g.moveTo(x, y);
        }
        g.lineTo(xs[xs.length - 1] / d * w, h); g.lineTo(xs[0] / d * w, h); g.closePath();
        g.fillStyle = fg + '22'; g.fill();
        this.line(g, xs, o.aux, w, h, pad, fg, 1.6, lo, hi, d);
        g.fillStyle = fg; g.font = '11px system-ui';
        const lab = o.auxKind === 'price' ? `${lo.toFixed(0)} – ${hi.toFixed(0)}` : `max ${hi.toFixed(1)} mm/h`;
        g.fillText(lab, 6, 12);
      }
      for (const m of this.moments || []) { g.fillStyle = ac; g.fillRect(m.song_s / d * w - 1, h - 6, 2, 6); }
      this.playhead(g, t / d * w, h);
      // --- overlay
      [g, w, h] = this.sizeCanvas(this.cOver);
      g.clearRect(0, 0, w, h);
      if (o.songCurve && o.songCurve.length) {
        const [lo, hi] = minmax(o.songCurve);
        const xs = o.songCurve.map((_, i) => (o.songT0 || 0) + i);
        this.line(g, xs, o.songCurve, w, h, 10, sc, 2, lo, hi, d);
      }
      if (o.tension && o.tension.length) {
        const [lo, hi] = minmax(o.tension);
        const xs = o.tension.map((_, i) => o.stepToSec[Math.min(i, o.stepToSec.length - 1)]);
        this.line(g, xs, o.tension, w, h, 10, dc, 2, lo, hi, d);
      }
      for (const m of this.moments || []) {
        g.strokeStyle = ac; g.globalAlpha = .55; g.beginPath(); g.moveTo(m.song_s / d * w, 0); g.lineTo(m.song_s / d * w, h); g.stroke(); g.globalAlpha = 1;
      }
      this.playhead(g, t / d * w, h);
    }

    playhead(g, x, h) {
      g.strokeStyle = css('--acc'); g.lineWidth = 2; g.beginPath(); g.moveTo(x, 0); g.lineTo(x, h); g.stroke();
    }
  }
  root.Player = Player;
  root.fmtTime = fmt;
})(window);
