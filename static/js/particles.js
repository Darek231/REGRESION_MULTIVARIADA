/* Constelación: miles de triángulos outline formando un cerebro. Reacciona al cursor. */
(function () {
  const canvas = document.getElementById('constellation');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const COLORS = ['#8052ff', '#ffb829', '#2cc4a4', '#ff4fd8', '#4f8bff'];
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const mobile = window.innerWidth < 700;
  const BRAIN = mobile ? 900 : 1700, AMBIENT = mobile ? 90 : 220;
  let W = 0, H = 0, dpr = 1, visible = true;
  const mouse = { x: -9999, y: -9999 };
  const P = [];

  const inEllipse = (x, y, cx, cy, rx, ry) => ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1;
  function inBrain(x, y) {
    if (Math.abs(x - 0.02) < 0.014 && y < 0.15) return false;              // fisura central
    return inEllipse(x, y, -0.02, -0.1, 0.82, 0.58) ||                       // cerebro
           inEllipse(x, y, -0.34, 0.3, 0.4, 0.27) ||                         // lóbulo temporal
           inEllipse(x, y, 0.5, 0.42, 0.27, 0.19) ||                         // cerebelo
           inEllipse(x, y, 0.12, 0.45, 0.14, 0.36);                          // tronco
  }
  function build() {
    P.length = 0;
    while (P.filter(p => !p.amb).length < BRAIN) {
      const x = Math.random() * 2 - 1, y = Math.random() * 2 - 1;
      if (!inBrain(x, y)) continue;
      const folds = 0.5 + 0.5 * Math.sin(x * 14) * Math.sin(y * 12 + x * 3);   // surcos
      if (Math.random() > 0.35 + 0.65 * folds) continue;
      P.push(mk(x, y, false));
    }
    for (let i = 0; i < AMBIENT; i++) P.push(mk(Math.random() * 2.6 - 1.3, Math.random() * 2.2 - 1.1, true));
  }
  function mk(bx, by, amb) {
    return { bx, by, x: 0, y: 0, ox: 0, oy: 0, amb,
      s: amb ? 3 + Math.random() * 5 : 2.2 + Math.random() * 3.6,
      r: Math.random() * 6.28, vr: (Math.random() - .5) * (amb ? .01 : .02),
      ph: Math.random() * 6.28, c: Math.floor(Math.random() * COLORS.length) };
  }
  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    const b = canvas.getBoundingClientRect();
    W = b.width; H = b.height;
    canvas.width = W * dpr; canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  function draw(t) {
    ctx.clearRect(0, 0, W, H);
    const sc = Math.min(W, H * 1.25) * 0.5 * (1 + 0.012 * Math.sin(t / 1400));
    const cx = W / 2, cy = H / 2;
    const groups = {};
    for (const p of P) {
      const wob = p.amb ? 10 : 4;
      const tx = cx + p.bx * sc + Math.sin(t / 1600 + p.ph) * wob;
      const ty = cy + p.by * sc + Math.cos(t / 1900 + p.ph) * wob;
      const dx = tx - mouse.x, dy = ty - mouse.y, d = Math.hypot(dx, dy);
      let fx = 0, fy = 0;
      if (d < 120) { const f = (1 - d / 120) ** 2 * 46; fx = (dx / (d || 1)) * f; fy = (dy / (d || 1)) * f; }
      p.ox += (fx - p.ox) * 0.09; p.oy += (fy - p.oy) * 0.09;
      p.x = tx + p.ox; p.y = ty + p.oy; p.r += p.vr;
      const key = (p.amb ? 'a' : 'b') + p.c;
      (groups[key] || (groups[key] = [])).push(p);
    }
    for (const key in groups) {
      ctx.beginPath();
      for (const p of groups[key]) {
        for (let k = 0; k < 3; k++) {
          const a = p.r + k * 2.0944, px = p.x + Math.cos(a) * p.s, py = p.y + Math.sin(a) * p.s;
          k ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
        }
        ctx.closePath();
      }
      ctx.strokeStyle = COLORS[+key.slice(1)];
      ctx.globalAlpha = key[0] === 'a' ? 0.28 : 0.9;
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }
  function loop(t) { if (visible) draw(t); requestAnimationFrame(loop); }

  window.addEventListener('mousemove', e => {
    const b = canvas.getBoundingClientRect();
    mouse.x = e.clientX - b.left; mouse.y = e.clientY - b.top;
  }, { passive: true });
  window.addEventListener('mouseleave', () => { mouse.x = mouse.y = -9999; });
  window.addEventListener('resize', resize);
  new IntersectionObserver(es => { visible = es[0].isIntersecting; }).observe(canvas);

  resize(); build();
  if (reduce) draw(0); else requestAnimationFrame(loop);
})();
