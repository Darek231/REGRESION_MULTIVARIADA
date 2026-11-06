/* Mini-librería de gráficos en <canvas>: puntos = triángulos outline (guiño a la constelación).
   Todos con fondo negro para que el PNG descargado se vea igual que en pantalla. */
const Charts = (function () {
  const C = { violet: '#8052ff', amber: '#ffb829', teal: '#2cc4a4', magenta: '#ff4fd8', blue: '#4f8bff' };
  const SPECTRUM = [C.violet, C.amber, C.teal, C.magenta, C.blue];
  const FONT = "Inter, system-ui, sans-serif";
  const registry = [];
  const tip = () => document.getElementById('tip');

  function niceNum(r, round) {
    const e = Math.floor(Math.log10(r)), f = r / 10 ** e;
    const nf = round ? (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) : (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10);
    return nf * 10 ** e;
  }
  function ticks(min, max, n = 5) {
    if (min === max) { min -= 1; max += 1; }
    const step = niceNum(niceNum(max - min, false) / (n - 1), true);
    const lo = Math.floor(min / step) * step, hi = Math.ceil(max / step) * step, out = [];
    for (let v = lo; v <= hi + step / 2; v += step) out.push(+v.toPrecision(12));
    return out;
  }
  const fmt = v => (Math.abs(v) >= 10000 || (Math.abs(v) < 0.01 && v !== 0)) ? v.toExponential(1)
    : (+v.toPrecision(4)).toString();

  function tri(ctx, x, y, s, rot = -Math.PI / 2) {
    ctx.moveTo(x + Math.cos(rot) * s, y + Math.sin(rot) * s);
    ctx.lineTo(x + Math.cos(rot + 2.0944) * s, y + Math.sin(rot + 2.0944) * s);
    ctx.lineTo(x + Math.cos(rot + 4.1888) * s, y + Math.sin(rot + 4.1888) * s);
    ctx.closePath();
  }

  class Chart {
    constructor(host, { title, sub, xLabel, yLabel, file, ratio = 0.68 }) {
      this.o = { title, xLabel, yLabel, ratio }; this.file = file;
      this.root = document.createElement('div'); this.root.className = 'plot reveal';
      this.root.innerHTML = `<div class="plot-bar"><span class="plot-title">${title}<small>${sub || ''}</small></span>
        <button class="ghost" type="button">PNG ↓</button></div>`;
      this.canvas = document.createElement('canvas');
      this.root.appendChild(this.canvas);
      this.root.querySelector('button').onclick = () => this.download();
      host.appendChild(this.root);
      requestAnimationFrame(() => this.root.classList.add('in'));
      this.hover = -1; this.pts = [];
      this.canvas.addEventListener('mousemove', e => this.onMove(e));
      this.canvas.addEventListener('mouseleave', () => { this.hover = -1; this.render(); tip().classList.remove('show'); });
      registry.push(this);
    }
    size() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.W = this.root.clientWidth || 480; this.H = Math.round(this.W * this.o.ratio);
      this.canvas.width = this.W * dpr; this.canvas.height = this.H * dpr;
      this.canvas.style.height = this.H + 'px';
      this.ctx = this.canvas.getContext('2d'); this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    frame(xr, yr, xt, yt) {
      const { ctx, W, H } = this;
      const m = { l: 62, r: 18, t: 16, b: 52 };
      this.m = m;
      ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, H);
      this.sx = v => m.l + (v - xr[0]) / (xr[1] - xr[0]) * (W - m.l - m.r);
      this.sy = v => H - m.b - (v - yr[0]) / (yr[1] - yr[0]) * (H - m.t - m.b);
      ctx.font = `400 11px ${FONT}`; ctx.fillStyle = '#9a9a9a'; ctx.strokeStyle = 'rgba(255,255,255,.07)'; ctx.lineWidth = 1;
      ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
      yt.forEach(v => { const y = this.sy(v); ctx.beginPath(); ctx.moveTo(m.l, y); ctx.lineTo(W - m.r, y); ctx.stroke(); ctx.fillText(fmt(v), m.l - 8, y); });
      ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      xt.forEach(v => { const x = this.sx(v); ctx.beginPath(); ctx.moveTo(x, m.t); ctx.lineTo(x, H - m.b); ctx.stroke(); ctx.fillText(fmt(v), x, H - m.b + 8); });
      ctx.fillStyle = '#bdbdbd'; ctx.font = `600 11px ${FONT}`;
      ctx.fillText(this.o.xLabel.toUpperCase(), m.l + (W - m.l - m.r) / 2, H - 18);
      ctx.save(); ctx.translate(14, m.t + (H - m.t - m.b) / 2); ctx.rotate(-Math.PI / 2);
      ctx.textBaseline = 'middle'; ctx.fillText(this.o.yLabel.toUpperCase(), 0, 0); ctx.restore();
    }
    dots(points, colorFn, sizeFn) {
      const { ctx } = this; this.pts = [];
      const byColor = {};
      points.forEach((p, i) => {
        const px = this.sx(p.x), py = this.sy(p.y), col = colorFn(p, i);
        this.pts.push({ px, py, p });
        (byColor[col] || (byColor[col] = [])).push([px, py, i]);
      });
      ctx.lineWidth = 1.2; ctx.globalAlpha = .85;
      for (const col in byColor) {
        ctx.beginPath(); ctx.strokeStyle = col;
        byColor[col].forEach(([x, y]) => tri(ctx, x, y, 4.2));
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
      if (this.hover >= 0 && this.pts[this.hover]) {
        const h = this.pts[this.hover]; ctx.beginPath(); tri(ctx, h.px, h.py, 8);
        ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
      }
    }
    line(x1, y1, x2, y2, color = '#fff', dash = [], w = 1.6) {
      const { ctx } = this; ctx.save(); ctx.beginPath(); ctx.setLineDash(dash); ctx.strokeStyle = color; ctx.lineWidth = w;
      ctx.beginPath(); ctx.moveTo(this.sx(x1), this.sy(y1)); ctx.lineTo(this.sx(x2), this.sy(y2)); ctx.stroke(); ctx.restore();
    }
    onMove(e) {
      const b = this.canvas.getBoundingClientRect(), x = e.clientX - b.left, y = e.clientY - b.top;
      let best = -1, bd = 14;
      this.pts.forEach((q, i) => { const d = Math.hypot(q.px - x, q.py - y); if (d < bd) { bd = d; best = i; } });
      if (best !== this.hover) { this.hover = best; this.render(); }
      const t = tip();
      if (best >= 0) { t.innerHTML = this.pts[best].p.tip; t.style.left = e.clientX + 'px'; t.style.top = e.clientY + 'px'; t.classList.add('show'); }
      else t.classList.remove('show');
    }
    render() { this.size && this.draw(); }
    download() {
      this.hover = -1; this.draw();
      this.canvas.toBlob(blob => {
        const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = this.file + '.png';
        document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 1500);
      });
    }
  }

  /* 5.1 Dispersión Xi vs Y */
  function scatter(host, s, yName, idx) {
    const ch = new Chart(host, { title: `${s.name} vs ${yName}`, sub: `r = ${s.r.toFixed(3)}`, xLabel: s.name, yLabel: yName, file: `dispersion_${s.name}` });
    const col = SPECTRUM[idx % SPECTRUM.length];
    const pts = s.x.map((x, i) => ({ x, y: s.y[i], tip: `${s.name}: <b>${fmt(x)}</b> · ${yName}: <b>${fmt(s.y[i])}</b>` }));
    const xmin = Math.min(...s.x), xmax = Math.max(...s.x), ymin = Math.min(...s.y), ymax = Math.max(...s.y);
    const xt = ticks(xmin, xmax), yt = ticks(ymin, ymax);
    ch.draw = function () {
      this.size(); this.frame([xt[0], xt.at(-1)], [yt[0], yt.at(-1)], xt, yt);
      this.line(xt[0], s.intercept + s.slope * xt[0], xt.at(-1), s.intercept + s.slope * xt.at(-1), '#fff', [], 1.6);
      this.dots(pts, () => col);
    };
    ch.draw(); return ch;
  }

  /* 5.2 Histograma de residuos + curva normal */
  function histogram(host, h) {
    const ch = new Chart(host, { title: 'Histograma de residuos', sub: 'curva normal en ámbar', xLabel: 'Residuo', yLabel: 'Frecuencia', file: 'histograma_residuos' });
    const e = h.edges, w = e[1] - e[0];
    const ymax = Math.max(...h.counts) * 1.15;
    const xt = ticks(e[0], e.at(-1)), yt = ticks(0, ymax);
    const bars = []; const mx = ch.hoverBar = -1;
    ch.draw = function () {
      this.size(); this.frame([Math.min(xt[0], e[0]), Math.max(xt.at(-1), e.at(-1))], [0, yt.at(-1)], xt, yt);
      const { ctx } = this; this.pts = [];
      h.counts.forEach((c, i) => {
        const x0 = this.sx(e[i]), x1 = this.sx(e[i + 1]), y = this.sy(c);
        ctx.fillStyle = this.hover === i ? '#ffffff' : 'rgba(128,82,255,.78)';
        ctx.fillRect(x0 + 1, y, Math.max(1, x1 - x0 - 2), this.sy(0) - y);
        this.pts.push({ px: (x0 + x1) / 2, py: y, p: { tip: `[${fmt(e[i])}, ${fmt(e[i + 1])}) · <b>${c}</b> obs.` } });
      });
      ctx.beginPath(); ctx.strokeStyle = C.amber; ctx.lineWidth = 2;
      for (let i = 0; i <= 120; i++) {
        const x = e[0] + (e.at(-1) - e[0]) * i / 120;
        const pdf = Math.exp(-0.5 * ((x - h.mean) / h.std) ** 2) / (h.std * Math.sqrt(2 * Math.PI));
        const px = this.sx(x), py = this.sy(pdf * h.n * w);
        i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
      }
      ctx.stroke();
    };
    ch.draw(); return ch;
  }

  /* 5.3 Q-Q */
  function qq(host, q) {
    const ch = new Chart(host, { title: 'Gráfico Q-Q', sub: 'residuos vs normal teórica', xLabel: 'Cuantiles teóricos', yLabel: 'Cuantiles de la muestra', file: 'qq_residuos' });
    const pts = q.theoretical.map((t, i) => ({ x: t, y: q.sample[i], tip: `Teórico: <b>${fmt(t)}</b> · Muestra: <b>${fmt(q.sample[i])}</b>` }));
    const lo = Math.min(...q.theoretical, ...q.sample), hi = Math.max(...q.theoretical, ...q.sample);
    const t = ticks(lo, hi);
    ch.draw = function () {
      this.size(); this.frame([t[0], t.at(-1)], [t[0], t.at(-1)], t, t);
      this.line(t[0], t[0], t.at(-1), t.at(-1), '#fff', [6, 5], 1.3);
      this.dots(pts, () => C.teal);
    };
    ch.draw(); return ch;
  }

  /* 5.4 Residuos estándar vs ajustados */
  function residFit(host, r) {
    const ch = new Chart(host, { title: 'Residuos estándar vs ajustados', sub: '|z| > 2 en ámbar', xLabel: 'Valores ajustados', yLabel: 'Residuo estándar', file: 'residuos_vs_ajustados' });
    const pts = r.fitted.map((f, i) => ({ x: f, y: r.std_resid[i], tip: `Ajustado: <b>${fmt(f)}</b> · Resid. est.: <b>${fmt(r.std_resid[i])}</b>` }));
    const ylo = Math.min(-3, ...r.std_resid), yhi = Math.max(3, ...r.std_resid);
    const xt = ticks(Math.min(...r.fitted), Math.max(...r.fitted)), yt = ticks(ylo, yhi);
    ch.draw = function () {
      this.size(); this.frame([xt[0], xt.at(-1)], [yt[0], yt.at(-1)], xt, yt);
      this.line(xt[0], 0, xt.at(-1), 0, '#fff', [], 1.3);
      [-2, 2].forEach(v => this.line(xt[0], v, xt.at(-1), v, 'rgba(255,184,41,.55)', [5, 5], 1));
      this.dots(pts, p => Math.abs(p.y) > 2 ? C.amber : C.violet);
    };
    ch.draw(); return ch;
  }

  let rz; window.addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => registry.forEach(c => c.isConnected() && c.draw()), 150); });
  Chart.prototype.isConnected = function () { return this.root.isConnected; };

  return { scatter, histogram, qq, residFit, all: () => registry.filter(c => c.isConnected()), clear: () => { registry.length = 0; } };
})();
