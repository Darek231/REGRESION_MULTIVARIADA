/* Lógica de la interfaz: flujo 01 Datos → 06 Gráficos */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const S = {
    token: null, numeric: [], columns: [], types: {},
    y: null, x: new Set(), fit: null,
    opt: { missing: 'mean', outliers: 'none', method: 'iqr', normality: 'all', hetero: 'all' },
  };

  /* ───────── utilidades ───────── */
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const num = (v, d = 4) => v === null || v === undefined ? '—' :
    (Math.abs(v) >= 1e6 || (Math.abs(v) < 1e-4 && v !== 0)) ? v.toExponential(2) : (+v.toFixed(d)).toLocaleString('en-US', { maximumFractionDigits: d });
  const pv = p => p === null || p === undefined ? '—' : p < 0.0001 ? '<0.0001' : p.toFixed(4);
  const stars = p => p < .001 ? '***' : p < .01 ? '**' : p < .05 ? '*' : p < .1 ? '·' : '';

  let toastT;
  function toast(msg, good) {
    const t = $('#toast'); t.textContent = msg; t.className = 'toast show' + (good ? ' ok' : '');
    clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('show'), 4200);
  }
  async function api(path, body) {
    const opt = body instanceof FormData ? { method: 'POST', body }
      : body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {};
    const r = await fetch(path, opt);
    let data = {}; try { data = await r.json(); } catch (_) { /* respuesta no JSON */ }
    if (!r.ok) throw new Error(data.error || `Error ${r.status}`);
    return data;
  }
  async function busy(btn, label, fn) {
    const old = btn.textContent; btn.disabled = true; btn.textContent = label;
    try { await fn(); } catch (e) { toast(e.message); } finally { btn.disabled = false; btn.textContent = old; }
  }
  const unlock = (...ids) => ids.forEach(i => $('#paso-' + i).classList.remove('locked'));
  const lock = (...ids) => ids.forEach(i => $('#paso-' + i).classList.add('locked'));
  const goto = id => $(id).scrollIntoView({ behavior: 'smooth', block: 'start' });
  const metric = (v, l, hl) => `<div class="metric${hl ? ' hl' : ''}"><b>${v}</b><span>${l}</span></div>`;

  /* ───────── chips genéricos (grupos data-group) ───────── */
  $$('.chips[data-group]').forEach(g => g.addEventListener('click', e => {
    const b = e.target.closest('.chip'); if (!b) return;
    $$('.chip', g).forEach(c => c.classList.toggle('on', c === b));
    S.opt[g.dataset.group] = b.dataset.v;
  }));

  /* ───────── 01 · Carga ───────── */
  const drop = $('#drop'), file = $('#file');
  drop.addEventListener('click', () => file.click());
  drop.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); file.click(); } });
  ['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('over'); }));
  ['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove('over'); }));
  drop.addEventListener('drop', e => e.dataTransfer.files[0] && upload(e.dataTransfer.files[0]));
  file.addEventListener('change', () => file.files[0] && upload(file.files[0]));
  $('#btn-sample').addEventListener('click', e => busy(e.target, 'Cargando…', async () => onDataset(await api('/api/sample'), true)));

  async function upload(f) {
    const fd = new FormData(); fd.append('file', f);
    try { onDataset(await api('/api/upload', fd), true); } catch (e) { toast(e.message); }
  }

  function onDataset(d, fresh) {
    S.token = d.token; S.numeric = d.numeric; S.columns = d.columns;
    if (fresh) {
      S.types = {}; S.fit = null; resetDownstream();
      S.y = d.numeric[0] || null;
      S.x = new Set(d.numeric.filter(c => c !== S.y));
    } else {
      S.x = new Set([...S.x].filter(c => d.numeric.includes(c)));
      if (!d.numeric.includes(S.y)) S.y = d.numeric[0] || null;
    }
    // 01
    $('#load-info').classList.remove('hidden');
    $('#load-metrics').innerHTML = metric(d.rows.toLocaleString(), 'Filas') + metric(d.cols, 'Variables') +
      metric(d.numeric.length, 'Numéricas') + metric(esc(d.delimiter).replace(' (', '<br>('), 'Delimitador', true);
    $('#rename-note').innerHTML = d.renamed.length
      ? `Nombres normalizados: ${d.renamed.map(r => `<span class="warn">${esc(r.old)}</span> → ${esc(r.new)}`).join(' · ')}`
      : `✓ ${esc(d.filename)} — nombres de variables válidos.`;
    $('#preview-table').innerHTML = `<thead><tr>${d.columns.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>` +
      d.preview.map(r => `<tr>${r.map(v => v === null ? '<td class="null">NA</td>' : `<td>${typeof v === 'number' ? num(v, 3) : esc(v)}</td>`).join('')}</tr>`).join('') + '</tbody>';
    // 02
    renderQuality(d);
    $('#clean-log').innerHTML = (d.log || []).map(l => `<li>${esc(l)}</li>`).join('');
    // 03
    $('#describe-table').innerHTML = `<thead><tr><th>Variable</th><th>n</th><th>Media</th><th>Varianza</th><th>Mín</th><th>Q1</th><th>Mediana</th><th>Q3</th><th>Máx</th></tr></thead><tbody>` +
      d.describe.map(r => `<tr><td class="name">${esc(r.column)}</td><td class="dim">${r.n}</td><td>${num(r.mean)}</td><td>${num(r.variance)}</td><td>${num(r.min)}</td><td>${num(r.q1)}</td><td>${num(r.median)}</td><td>${num(r.q3)}</td><td>${num(r.max)}</td></tr>`).join('') + '</tbody>';
    renderVars();
    unlock(2, 3, 4);
    if (fresh) { toast(`Datos cargados: ${d.rows} filas × ${d.cols} variables`, true); setTimeout(() => goto('#paso-2'), 650); }
    else toast('Limpieza aplicada', true);
    if (S.numeric.length < 2) toast('Se necesitan al menos 2 columnas numéricas (convierte tipos en el paso 02).');
  }

  function resetDownstream() {
    S.fit = null; lock(5, 6);
    ['#fit-out', '#tests-out', '#plots-out', '#btn-dl-all'].forEach(s => $(s).classList.add('hidden'));
    Charts.clear();
  }

  /* ───────── 02 · Limpieza ───────── */
  function renderQuality(d) {
    $('#quality-table').innerHTML = `<thead><tr><th>Columna</th><th>Tipo</th><th>Convertir a</th><th>Faltantes</th><th>% falt.</th><th>Atípicos</th></tr></thead><tbody>` +
      d.quality.map(q => `<tr>
        <td class="name">${esc(q.column)}</td><td class="dim">${q.dtype}</td>
        <td><select data-col="${esc(q.column)}"><option value="">sin cambio</option><option value="numeric"${S.types[q.column] === 'numeric' ? ' selected' : ''}>numérico</option><option value="text"${S.types[q.column] === 'text' ? ' selected' : ''}>texto</option></select></td>
        <td class="${q.missing ? 'warn' : 'dim'}">${q.missing}</td><td class="dim">${q.missing_pct}%</td>
        <td class="${q.outliers ? 'warn' : 'dim'}">${q.is_numeric ? q.outliers : '—'}</td></tr>`).join('') + '</tbody>';
    $$('#quality-table select').forEach(s => s.addEventListener('change', () => { s.value ? S.types[s.dataset.col] = s.value : delete S.types[s.dataset.col]; }));
  }
  async function runClean(reset) {
    const body = reset
      ? { token: S.token, missing: 'none', outliers: 'none', method: 'iqr', types: {} }
      : { token: S.token, missing: S.opt.missing, outliers: S.opt.outliers, method: S.opt.method, types: S.types };
    if (reset) S.types = {};
    const d = await api('/api/clean', body);
    resetDownstream();
    onDataset(d, false);
    if (reset) toast('Datos originales restaurados', true);
  }
  $('#btn-clean').addEventListener('click', e => busy(e.target, 'Limpiando…', () => runClean(false)));
  $('#btn-reset').addEventListener('click', e => busy(e.target, 'Restableciendo…', () => runClean(true)));

  /* ───────── 04 · Selección de variables y modelo ───────── */
  function renderVars() {
    const yBox = $('#y-chips'), xBox = $('#x-chips');
    yBox.innerHTML = S.columns.map(c => {
      const isNum = S.numeric.includes(c);
      return `<button class="chip y${S.y === c ? ' on' : ''}${isNum ? '' : ' off'}" data-c="${esc(c)}">${esc(c)}</button>`;
    }).join('');
    xBox.innerHTML = S.columns.map(c => {
      const isNum = S.numeric.includes(c), dis = !isNum || c === S.y;
      return `<button class="chip${S.x.has(c) && !dis ? ' on' : ''}${dis ? ' off' : ''}" data-c="${esc(c)}">${esc(c)}</button>`;
    }).join('');
    const xs = [...S.x].filter(c => c !== S.y);
    $('#formula-preview').textContent = S.y
      ? `${S.y} = β₀${xs.map((c, i) => ` + β${i + 1}·${c}`).join('')} + ε` : '';
  }
  $('#y-chips').addEventListener('click', e => {
    const b = e.target.closest('.chip'); if (!b) return;
    S.y = b.dataset.c; S.x.delete(S.y); renderVars();
  });
  $('#x-chips').addEventListener('click', e => {
    const b = e.target.closest('.chip'); if (!b) return;
    const c = b.dataset.c; S.x.has(c) ? S.x.delete(c) : S.x.add(c); renderVars();
  });
  $('#x-all').addEventListener('click', () => { S.x = new Set(S.numeric.filter(c => c !== S.y)); renderVars(); });
  $('#x-none').addEventListener('click', () => { S.x = new Set(); renderVars(); });

  $('#btn-fit').addEventListener('click', e => busy(e.target, 'Estimando…', async () => {
    const xs = [...S.x].filter(c => c !== S.y);
    const f = await api('/api/fit', { token: S.token, y: S.y, x: xs });
    S.fit = f;
    $('#tests-out').classList.add('hidden'); $('#plots-out').classList.add('hidden'); $('#btn-dl-all').classList.add('hidden'); Charts.clear();
    $('#fit-out').classList.remove('hidden');
    $('#fit-metrics').innerHTML = metric(f.r2.toFixed(4), 'R²', true) + metric(f.r2_adj.toFixed(4), 'R² ajustado') +
      metric(num(f.f_stat, 2), 'Estadístico F') + metric(pv(f.f_p), 'p-valor (F)') + metric(num(f.sigma, 3), 'σ residual') + metric(f.n, 'Observaciones');
    $('#fit-equation').textContent = f.equation;
    $('#coef-table').innerHTML = `<thead><tr><th>Variable</th><th>β estimado</th><th>Error est.</th><th>t</th><th>p-valor</th><th>IC 95 %</th><th></th></tr></thead><tbody>` +
      f.coefficients.map(c => `<tr><td class="name">${esc(c.name)}</td><td>${num(c.beta)}</td><td>${num(c.se)}</td><td>${num(c.t, 3)}</td>
        <td class="${c.p < .05 ? 'sig' : 'dim'}">${pv(c.p)}</td><td class="dim">[${num(c.ci_low, 3)}, ${num(c.ci_high, 3)}]</td><td class="sig">${stars(c.p)}</td></tr>`).join('') + '</tbody>';
    const sig = f.coefficients.slice(1).filter(c => c.p < .05).map(c => c.name);
    $('#fit-note').innerHTML = `Significativas al 5 %: <b>${sig.length ? esc(sig.join(', ')) : 'ninguna'}</b> · *** p&lt;0.001 · ** p&lt;0.01 · * p&lt;0.05 · · p&lt;0.1` +
      (f.dropped_rows ? `<br><span class="warn">${f.dropped_rows} fila(s) con valores faltantes se excluyeron del ajuste.</span>` : '');
    unlock(5, 6);
    toast('Modelo estimado', true);
    setTimeout(() => $('#fit-out').scrollIntoView({ behavior: 'smooth', block: 'start' }), 300);
  }));

  $('#btn-csv').addEventListener('click', () => {
    if (!S.fit) return;
    const rows = [['variable', 'beta', 'error_estandar', 't', 'p_valor', 'ic95_inf', 'ic95_sup']]
      .concat(S.fit.coefficients.map(c => [c.name, c.beta, c.se, c.t, c.p, c.ci_low, c.ci_high]));
    const blob = new Blob([rows.map(r => r.join(',')).join('\n')], { type: 'text/csv' });
    const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'coeficientes.csv' });
    document.body.appendChild(a); a.click(); a.remove();
  });

  /* ───────── 05 · Validación ───────── */
  $('#btn-tests').addEventListener('click', e => busy(e.target, 'Ejecutando…', async () => {
    const t = await api('/api/tests', { token: S.token, normality: S.opt.normality, hetero: S.opt.hetero });
    $('#tests-out').classList.remove('hidden');
    const blocks = [
      ['4.1 · Normalidad', t.normality], ['4.2 · Autocorrelación', [t.autocorrelation]], ['4.3 · Homocedasticidad', t.homoscedasticity],
    ];
    $('#tests-list').innerHTML = blocks.map(([cat, list]) => list.map(r => `
      <div class="test"><div class="t-head"><span class="dot${r.passed ? '' : ' bad'}"></span>${cat}</div>
        <h4>${esc(r.name)}</h4>
        <div class="vals"><i>${r.key === 'dw' ? 'd' : r.key === 'shapiro' ? 'W' : r.key === 'ks' ? 'D' : r.key === 'jb' ? 'JB' : 'LM'} =</i> ${num(r.statistic, 4)}${r.p_value !== null ? ` &nbsp;·&nbsp; <i>p =</i> ${pv(r.p_value)}` : ''}</div>
        <p><b>${esc(r.conclusion)}</b></p><p class="n">H₀: ${esc(r.h0)}<br>${esc(r.note)}</p></div>`).join('')).join('');

    const maxV = Math.max(10, ...t.vif.map(v => Math.min(v.vif ?? 1e9, 40)));
    $('#vif-list').innerHTML = t.vif.map(v => {
      const val = v.vif === null ? '∞' : v.vif.toFixed(2);
      return `<div class="vif-row${v.high ? ' high' : ''}"><span>${esc(v.name)}</span>
        <div class="bar"><i data-w="${Math.min(100, ((v.vif ?? 40) / maxV) * 100)}"></i></div>
        <span class="v">${val}${v.high ? '<span class="flag">ALTO</span>' : ''}</span></div>`;
    }).join('') + `<p class="note">VIF &gt; 10 = multicolinealidad severa (en ámbar). Considera quitar o combinar variables redundantes.</p>`;
    requestAnimationFrame(() => requestAnimationFrame(() => $$('#vif-list .bar i').forEach(i => i.style.width = i.dataset.w + '%')));

    const all = [...t.normality, t.autocorrelation, ...t.homoscedasticity];
    const bad = all.filter(r => !r.passed).map(r => r.name), hi = t.vif.filter(v => v.high).map(v => v.name);
    $('#verdict').innerHTML = (bad.length || hi.length)
      ? `<span class="warn">${bad.length + (hi.length ? 1 : 0)} supuesto(s) con alertas.</span><small>${bad.length ? 'Pruebas con rechazo de H₀: ' + esc(bad.join(', ')) + '. ' : ''}${hi.length ? 'VIF alto en: ' + esc(hi.join(', ')) + '.' : ''}</small>`
      : `Todos los supuestos se cumplen.<small>No hay evidencia contra normalidad, autocorrelación ni heterocedasticidad; VIF ≤ 10 en todas las variables.</small>`;
    toast('Pruebas ejecutadas', true);
  }));

  /* ───────── 06 · Gráficos ───────── */
  $('#btn-plots').addEventListener('click', e => busy(e.target, 'Dibujando…', async () => {
    const p = await api('/api/plots', { token: S.token });
    Charts.clear();
    const a = $('#plots-scatter'), b = $('#plots-resid'); a.innerHTML = ''; b.innerHTML = '';
    $('#plots-out').classList.remove('hidden');
    p.scatter.forEach((s, i) => Charts.scatter(a, s, p.y, i));
    Charts.histogram(b, p.histogram); Charts.qq(b, p.qq); Charts.residFit(b, p.resid_vs_fitted);
    $('#btn-dl-all').classList.remove('hidden');
    toast(`${Charts.all().length} gráficos generados`, true);
  }));
  $('#btn-dl-all').addEventListener('click', () => Charts.all().forEach((c, i) => setTimeout(() => c.download(), i * 350)));

  /* ───────── nav activa + aparición suave ───────── */
  const links = $$('.nav-links a');
  const io = new IntersectionObserver(es => es.forEach(en => {
    if (en.isIntersecting) links.forEach(l => l.classList.toggle('active', l.getAttribute('href') === '#' + en.target.id));
  }), { rootMargin: '-45% 0px -50% 0px' });
  $$('.step').forEach(s => io.observe(s));
})();
