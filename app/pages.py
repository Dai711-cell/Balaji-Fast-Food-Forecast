BUSINESS_HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Balaji Fast Food | Prevision de ventas</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #0f172a;
      --muted: #475569;
      --line: #cbd5e1;
      --panel: #ffffff;
      --soft: #eff6ff;
      --brand: #2563eb;
      --brand-2: #0ea5e9;
      --danger: #b42318;
      --shadow: 0 18px 45px rgba(18, 38, 63, .12);
    }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; font-family: Inter, Segoe UI, Arial, sans-serif; color: var(--ink); background-color: #dbeafe; background-image: linear-gradient(135deg, rgba(96,165,250,.68) 0%, rgba(239,246,255,.96) 27%, rgba(255,255,255,.98) 46%, rgba(125,211,252,.70) 70%, rgba(219,234,254,.96) 100%); background-size: 160% 160%; background-attachment: fixed; animation: backdropDrift 24s ease-in-out infinite alternate; }
    body::before { content: ""; position: fixed; inset: -5%; z-index: 0; pointer-events: none; background-image: radial-gradient(circle at 8% 16%, rgba(255,255,255,.92) 0 2px, transparent 3px), radial-gradient(circle at 29% 72%, rgba(255,255,255,.70) 0 1.5px, transparent 2.5px), radial-gradient(circle at 47% 24%, rgba(255,255,255,.84) 0 2px, transparent 3px), radial-gradient(circle at 68% 84%, rgba(255,255,255,.78) 0 1.5px, transparent 2.5px), radial-gradient(circle at 83% 35%, rgba(255,255,255,.92) 0 2px, transparent 3px), radial-gradient(circle at 94% 67%, rgba(255,255,255,.66) 0 1.5px, transparent 2.5px); animation: starDrift 18s ease-in-out infinite alternate, starPulse 7s ease-in-out infinite alternate; }
    @keyframes backdropDrift { from { background-position: 0% 20%; } to { background-position: 100% 80%; } }
    @keyframes starDrift { from { transform: translate3d(-5px, -3px, 0); } to { transform: translate3d(12px, 8px, 0); } }
    @keyframes starPulse { from { opacity: .55; } to { opacity: .92; } }
    @media (prefers-reduced-motion: reduce) { body, body::before { animation: none; } }
    .shell { min-height: 100vh; display: grid; grid-template-rows: auto 1fr; }
    header { padding: 18px 28px; border-bottom: 1px solid rgba(37,99,235,.16); display: flex; justify-content: space-between; gap: 16px; align-items: center; background: rgba(255,255,255,.86); backdrop-filter: blur(14px); position: sticky; top: 0; z-index: 2; }
    .brand { display: flex; align-items: center; gap: 12px; font-weight: 800; letter-spacing: 0; }
    .mark { width: 38px; height: 38px; border-radius: 8px; display: grid; place-items: center; background: #0f172a; color: #fff; font-size: 19px; }
    .nav { display: flex; align-items: center; gap: 10px; color: var(--muted); font-size: 14px; }
    .nav a { color: var(--brand); text-decoration: none; font-weight: 700; }
    main { width: min(1180px, calc(100vw - 32px)); margin: 0 auto; padding: 34px 0 44px; }
    .hero { display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(320px, .92fr); gap: 28px; align-items: start; }
    .intro h1 { margin: 0 0 14px; font-size: clamp(32px, 4.8vw, 58px); line-height: 1.02; letter-spacing: 0; max-width: 780px; }
    .intro p { margin: 0 0 22px; color: var(--muted); font-size: 18px; line-height: 1.55; max-width: 720px; }
    .panel { background: rgba(255,255,255,.94); border: 1px solid rgba(148,163,184,.55); border-radius: 8px; box-shadow: var(--shadow); backdrop-filter: blur(10px); }
    .forecast-box { padding: 22px; }
    label { display: block; color: #354454; font-weight: 700; margin-bottom: 8px; }
    .controls { display: grid; grid-template-columns: 1fr auto; gap: 10px; align-items: end; }
    input, select { width: 100%; border: 1px solid #cbd5df; border-radius: 8px; padding: 12px 13px; font: inherit; background: #fff; color: var(--ink); }
    button { border: 0; border-radius: 8px; padding: 12px 16px; background: var(--brand); color: #fff; font-weight: 800; cursor: pointer; min-height: 46px; }
    button.secondary { background: #0f172a; }
    button:disabled { opacity: .55; cursor: wait; }
    .hint { margin-top: 10px; color: var(--muted); font-size: 13px; line-height: 1.45; }
    .result { margin-top: 18px; display: none; }
    .result.visible { display: block; }
    .big-number { font-size: clamp(36px, 7vw, 72px); font-weight: 900; letter-spacing: 0; margin: 4px 0 8px; color: #1d4ed8; }
    .summary-line { color: var(--muted); line-height: 1.45; }
    .intervals { margin-top: 18px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .interval { border: 1px solid var(--line); border-radius: 8px; padding: 14px; background: var(--soft); }
    .interval strong { display: block; font-size: 13px; color: var(--muted); margin-bottom: 8px; }
    .range { font-size: 18px; font-weight: 850; }
    .grid { margin-top: 28px; display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
    .section { padding: 20px; }
    .section h2 { margin: 0 0 12px; font-size: 22px; letter-spacing: 0; }
    .kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .kpi { background: var(--soft); border: 1px solid var(--line); border-radius: 8px; padding: 12px; }
    .kpi span { display: block; color: var(--muted); font-size: 12px; font-weight: 700; }
    .kpi b { display: block; margin-top: 4px; font-size: 20px; }
    .bars { display: grid; gap: 10px; margin-top: 8px; }
    .bar-row { display: grid; grid-template-columns: 84px 1fr 76px; gap: 10px; align-items: center; font-size: 13px; color: #334155; }
    .bar-track { height: 12px; border-radius: 999px; background: #e5eaf0; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #1d4ed8, #38bdf8); width: 0%; transition: width .5s ease; }
    .path { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
    .path th, .path td { border-bottom: 1px solid var(--line); padding: 8px; text-align: left; }
    .path th { color: var(--muted); font-size: 12px; }
    .error { color: var(--danger); margin-top: 12px; font-weight: 700; }
    @media (max-width: 860px) { .hero, .grid { grid-template-columns: 1fr; } .intervals, .kpis { grid-template-columns: 1fr; } header { padding: 14px 16px; align-items: flex-start; } .nav { flex-wrap: wrap; justify-content: flex-end; } .controls { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div class="brand"><div class="mark">🤖</div><div>Balaji Fast Food Forecast</div></div>
      <div class="nav"><span>Herramienta interna</span><a href="/admin">Panel de datos</a></div>
    </header>
    <main>
      <section class="hero">
        <div class="intro">
          <h1>Prevision diaria de ingresos para decidir con mas seguridad.</h1>
          <p>Selecciona un dia futuro y el modelo estima la venta esperada, junto con tres rangos practicos de confianza. La idea es ayudar a planificar compras, personal y caja sin depender solo de intuicion.</p>
          <div class="panel section">
            <h2>Como leer el resultado</h2>
            <div class="kpis">
              <div class="kpi"><span>Estimacion</span><b id="kpiPrediction">--</b></div>
              <div class="kpi"><span>Ultimo dato</span><b id="kpiLastDate">--</b></div>
              <div class="kpi"><span>Datos usados</span><b id="kpiRows">--</b></div>
            </div>
            <p class="hint">Los rangos 50%, 60% y 70% no son promesas exactas: son bandas basadas en el error historico del modelo. Para negocio son mas faciles de usar que rangos demasiado amplios.</p>
          </div>
        </div>
        <div class="panel forecast-box">
          <label for="forecastDate">Dia a predecir</label>
          <div class="controls">
            <input id="forecastDate" type="date" />
            <button id="predictBtn" type="button">Predecir</button>
          </div>
          <div id="dateHint" class="hint">Cargando disponibilidad...</div>
          <div id="error" class="error"></div>
          <div id="result" class="result">
            <div class="summary-line">Venta esperada para <b id="resultDate"></b></div>
            <div class="big-number" id="prediction">--</div>
            <div class="summary-line" id="modelLine"></div>
            <div class="intervals">
              <div class="interval"><strong>Rango 50%</strong><div class="range" id="i50">--</div></div>
              <div class="interval"><strong>Rango 60%</strong><div class="range" id="i60">--</div></div>
              <div class="interval"><strong>Rango 70%</strong><div class="range" id="i70">--</div></div>
            </div>
          </div>
        </div>
      </section>
      <section class="grid">
        <div class="panel section">
          <h2>Camino previsto</h2>
          <p class="hint">Si eliges una fecha alejada, el sistema calcula dia a dia hasta llegar al objetivo.</p>
          <div class="bars" id="pathBars"></div>
        </div>
        <div class="panel section">
          <h2>Ultimos dias calculados</h2>
          <table class="path"><thead><tr><th>Fecha</th><th>Prediccion</th></tr></thead><tbody id="pathTable"><tr><td colspan="2">Haz una prediccion para ver el detalle.</td></tr></tbody></table>
        </div>
      </section>
    </main>
  </div>
<script>
const money = new Intl.NumberFormat('es-ES', { maximumFractionDigits: 0 });
const els = {
  date: document.getElementById('forecastDate'), btn: document.getElementById('predictBtn'), hint: document.getElementById('dateHint'), error: document.getElementById('error'), result: document.getElementById('result'),
  prediction: document.getElementById('prediction'), resultDate: document.getElementById('resultDate'), modelLine: document.getElementById('modelLine'), i50: document.getElementById('i50'), i60: document.getElementById('i60'), i70: document.getElementById('i70'),
  kpiPrediction: document.getElementById('kpiPrediction'), kpiLastDate: document.getElementById('kpiLastDate'), kpiRows: document.getElementById('kpiRows'), pathBars: document.getElementById('pathBars'), pathTable: document.getElementById('pathTable')
};
function formatMoney(v) { return money.format(v); }
function addOneDay(dateText) { const p = dateText.split('-').map(Number); return new Date(Date.UTC(p[0], p[1]-1, p[2]+1)).toISOString().slice(0,10); }
async function loadHealth() {
  const r = await fetch('/api/health'); const data = await r.json();
  const firstDate = data.first_predictable_date || addOneDay(data.model.last_observed_date);
  els.date.min = firstDate; els.date.value = firstDate;
  els.hint.textContent = `Primer dia predecible: ${firstDate}. Ultimo dia con datos: ${data.model.last_observed_date}.`;
  els.kpiLastDate.textContent = data.model.last_observed_date;
  els.kpiRows.textContent = data.data.rows || '--';
}
function renderPath(path) {
  const last = path.slice(-8); const max = Math.max(...last.map(x => x.prediction), 1);
  els.pathBars.innerHTML = last.map(x => `<div class="bar-row"><span>${x.date.slice(5)}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.max(4, x.prediction / max * 100)}%"></div></div><b>${formatMoney(x.prediction)}</b></div>`).join('');
  els.pathTable.innerHTML = last.slice().reverse().map(x => `<tr><td>${x.date}</td><td>${formatMoney(x.prediction)}</td></tr>`).join('');
}
async function predict() {
  els.btn.disabled = true; els.error.textContent = '';
  try {
    const r = await fetch(`/api/predict?date=${encodeURIComponent(els.date.value)}`); const data = await r.json();
    if (!r.ok) throw new Error(data.detail || 'No se pudo calcular la prediccion');
    els.result.classList.add('visible'); els.resultDate.textContent = data.requested_date;
    els.prediction.textContent = formatMoney(data.prediction); els.kpiPrediction.textContent = formatMoney(data.prediction);
    els.modelLine.textContent = `${data.days_ahead} dias por delante. Modelo ${data.model.name}, entrenado con ${data.model.training_rows} dias modelables.`;
    els.i50.textContent = `${formatMoney(data.intervals['50'].lower)} - ${formatMoney(data.intervals['50'].upper)}`;
    els.i60.textContent = `${formatMoney(data.intervals['60'].lower)} - ${formatMoney(data.intervals['60'].upper)}`;
    els.i70.textContent = `${formatMoney(data.intervals['70'].lower)} - ${formatMoney(data.intervals['70'].upper)}`;
    renderPath(data.forecast_path);
  } catch (e) { els.error.textContent = e.message; }
  finally { els.btn.disabled = false; }
}
els.btn.addEventListener('click', predict);
loadHealth().then(predict).catch(e => { els.hint.textContent = 'No se pudo cargar el estado inicial.'; els.error.textContent = e.message; });
</script>
</body>
</html>
"""

ADMIN_HTML = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Balaji Fast Food | Panel de datos</title>
  <style>
    :root { --ink:#0f172a; --muted:#475569; --line:#cbd5e1; --soft:#eff6ff; --brand:#2563eb; --dark:#0f172a; --danger:#b42318; --warn:#a16207; --warn-bg:#fff7ed; --ok-bg:#dbeafe; }
    * { box-sizing:border-box; } body { margin:0; min-height:100vh; font-family:Inter, Segoe UI, Arial, sans-serif; color:var(--ink); background-color:#dbeafe; background-image:linear-gradient(135deg, rgba(96,165,250,.64) 0%, rgba(239,246,255,.96) 29%, rgba(255,255,255,.98) 47%, rgba(125,211,252,.66) 71%, rgba(219,234,254,.96) 100%); background-size:160% 160%; background-attachment:fixed; animation:backdropDrift 24s ease-in-out infinite alternate; }
    body::before { content:""; position:fixed; inset:-5%; z-index:0; pointer-events:none; background-image:radial-gradient(circle at 8% 16%, rgba(255,255,255,.92) 0 2px, transparent 3px), radial-gradient(circle at 29% 72%, rgba(255,255,255,.70) 0 1.5px, transparent 2.5px), radial-gradient(circle at 47% 24%, rgba(255,255,255,.84) 0 2px, transparent 3px), radial-gradient(circle at 68% 84%, rgba(255,255,255,.78) 0 1.5px, transparent 2.5px), radial-gradient(circle at 83% 35%, rgba(255,255,255,.92) 0 2px, transparent 3px), radial-gradient(circle at 94% 67%, rgba(255,255,255,.66) 0 1.5px, transparent 2.5px); animation:starDrift 18s ease-in-out infinite alternate, starPulse 7s ease-in-out infinite alternate; }
    body > header, body > main { position:relative; z-index:1; }
    @keyframes backdropDrift { from { background-position:0% 20%; } to { background-position:100% 80%; } }
    @keyframes starDrift { from { transform:translate3d(-5px,-3px,0); } to { transform:translate3d(12px,8px,0); } }
    @keyframes starPulse { from { opacity:.55; } to { opacity:.92; } }
    @media (prefers-reduced-motion:reduce) { body, body::before { animation:none; } }
    header { padding:18px 28px; background:#ffffff; border-bottom:1px solid #bfdbfe; display:flex; justify-content:space-between; gap:16px; align-items:center; position:sticky; top:0; z-index:2; }
    a { color:var(--brand); font-weight:800; text-decoration:none; } main { width:min(1220px, calc(100vw - 32px)); margin:0 auto; padding:28px 0 44px; }
    h1 { margin:0 0 8px; font-size:34px; letter-spacing:0; } h2 { margin:0 0 10px; font-size:22px; } h3 { margin:16px 0 8px; font-size:16px; } p { color:var(--muted); line-height:1.5; }
    .grid { display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:20px; } .panel { background:rgba(255,255,255,.94); border:1px solid rgba(148,163,184,.55); border-radius:8px; padding:20px; box-shadow:0 16px 38px rgba(30,64,175,.10); backdrop-filter:blur(10px); }
    label { display:block; font-weight:800; margin:12px 0 6px; } input, select { width:100%; border:1px solid #cbd5df; border-radius:8px; padding:11px; font:inherit; background:#fff; }
    button { border:0; border-radius:8px; padding:12px 16px; background:var(--brand); color:#fff; font-weight:850; cursor:pointer; min-height:44px; margin-top:12px; } button.secondary { background:var(--dark); } button.ghost { background:#dbeafe; color:var(--ink); }
    .kpis { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; margin-top:18px; } .kpi { background:var(--soft); border:1px solid var(--line); border-radius:8px; padding:12px; min-width:0; } .kpi span { display:block; color:var(--muted); font-size:12px; font-weight:800; } .kpi b { display:block; margin-top:4px; font-size:19px; overflow-wrap:anywhere; }
    .notice { display:none; margin-top:16px; padding:14px 16px; border-radius:8px; border:1px solid #fed7aa; background:var(--warn-bg); color:#7c2d12; font-weight:800; line-height:1.45; }
    .notice.ok { display:block; border-color:#93c5fd; background:var(--ok-bg); color:#1d4ed8; }
    .notice.warn { display:block; }
    table { width:100%; border-collapse:collapse; font-size:13px; } th,td { border-bottom:1px solid var(--line); text-align:left; padding:8px; vertical-align:top; } th { color:var(--muted); font-size:12px; white-space:nowrap; }
    .table-wrap { overflow:auto; border:1px solid var(--line); border-radius:8px; margin-top:10px; max-height:360px; background:#fff; }
    .msg { margin-top:10px; font-weight:800; } .error { color:var(--danger); } .ok-text { color:var(--brand); } .api-key { display:grid; grid-template-columns:1fr auto; gap:10px; align-items:end; margin-top:14px; }
    .actions { display:flex; gap:10px; flex-wrap:wrap; } .actions button { margin-top:12px; } .compare { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:12px; } .compare .kpis { grid-template-columns:repeat(2,1fr); margin-top:0; }
    .chips { display:flex; gap:8px; flex-wrap:wrap; margin-top:8px; } .chip { border:1px solid var(--line); background:var(--soft); border-radius:999px; padding:5px 9px; font-size:12px; color:#334155; }
    .muted { color:var(--muted); font-size:13px; } .hidden { display:none; }
    @media (max-width:900px) { .grid, .compare, .kpis, .api-key { grid-template-columns:1fr; } header { align-items:flex-start; } }
  </style>
</head>
<body>
<header><strong>🤖 Balaji Forecast Admin</strong><nav><a href="/">Prevision</a> · <a href="/docs">Documentacion tecnica</a></nav></header>
<main>
  <h1>Panel privado de datos y mantenimiento</h1>
  <p>Antes de insertar un CSV puedes ver como queda tras la limpieza automatica y compararlo con el historico actual. Despues de insertar, reentrena para que el modelo use los datos nuevos.</p>
  <section class="panel">
    <div class="api-key"><div><label for="apiKey">Clave interna opcional</label><input id="apiKey" type="password" placeholder="Solo si BALAJI_API_KEY esta configurada" /></div><button class="secondary" id="refreshBtn">Actualizar estado</button></div>
    <div id="pendingBox" class="notice">Comprobando si el modelo esta actualizado...</div>
    <div class="kpis"><div class="kpi"><span>Filas</span><b id="rows">--</b></div><div class="kpi"><span>Primer dato</span><b id="first">--</b></div><div class="kpi"><span>Ultimo dato base</span><b id="dataLast">--</b></div><div class="kpi"><span>Ultimo dato modelo</span><b id="modelLast">--</b></div><div class="kpi"><span>Primer dia predecible</span><b id="next">--</b></div></div>
  </section>
  <section class="grid">
    <div class="panel"><h2>CSV nuevo</h2><p>Primero previsualiza. Si la tabla limpia y las categorias concuerdan, entonces insertalo.</p><input id="csv" type="file" accept=".csv" /><div class="actions"><button class="ghost" id="previewBtn">Previsualizar limpieza</button><button id="uploadBtn">Insertar CSV</button></div><div id="uploadMsg" class="msg"></div></div>
    <div class="panel"><h2>Reentrenar modelo</h2><p>Recalcula el modelo usando todo el historico disponible en SQLite. Hazlo despues de insertar datos nuevos.</p><button id="retrainBtn">Reentrenar ahora</button><div id="trainMsg" class="msg"></div></div>
  </section>
  <section id="previewPanel" class="panel hidden" style="margin-top:18px"><h2>Resultado de la limpieza automatica</h2><p class="muted" id="previewName"></p><div class="compare"><div><h3>Historico actual</h3><div class="kpis" id="historicalSummary"></div></div><div><h3>CSV limpio</h3><div class="kpis" id="uploadSummary"></div></div></div><h3>Alertas de compatibilidad</h3><div id="compatibility" class="chips"></div><h3>Categorias nuevas detectadas</h3><div id="newCategories" class="chips"></div><h3>Primeras filas despues de limpiar</h3><div class="table-wrap"><table id="cleanTable"></table></div><h3>Primeras filas originales</h3><div class="table-wrap"><table id="rawTable"></table></div></section>
  <section class="panel" style="margin-top:18px"><h2>Registrar venta manual</h2><div class="grid"><div><label>Order ID</label><input id="order_id" type="number" value="999999" /><label>Fecha</label><input id="date" type="date" /><label>Producto</label><input id="item_name" value="Sandwich" /><label>Tipo producto</label><select id="item_type"><option>Fastfood</option><option>Beverages</option></select><label>Precio unidad</label><input id="item_price" type="number" step="0.01" value="40" /></div><div><label>Cantidad</label><input id="quantity" type="number" step="1" value="1" /><label>Importe</label><input id="transaction_amount" type="number" step="0.01" value="40" /><label>Pago</label><select id="transaction_type"><option>Cash</option><option>Online</option><option>Unknown</option></select><label>Recibido por</label><select id="received_by"><option>Mr.</option><option>Mrs.</option></select><label>Momento</label><select id="time_of_sale"><option>Morning</option><option>Afternoon</option><option>Evening</option><option>Night</option><option>Midnight</option></select></div></div><button id="saleBtn">Guardar venta</button><div id="saleMsg" class="msg"></div></section>
  <section class="panel" style="margin-top:18px"><h2>Ultimas ventas cargadas</h2><table><thead><tr><th>Fecha</th><th>Producto</th><th>Cantidad</th><th>Importe</th><th>Fuente</th></tr></thead><tbody id="recent"><tr><td colspan="5">Cargando...</td></tr></tbody></table></section>
</main>
<script>
const apiKey = () => document.getElementById('apiKey').value.trim();
const headers = () => apiKey() ? {'x-api-key': apiKey()} : {};
const money = new Intl.NumberFormat('es-ES', {maximumFractionDigits: 0});
function setMsg(id, text, ok=true) { const el = document.getElementById(id); el.textContent = text; el.className = ok ? 'msg ok-text' : 'msg error'; }
async function jsonFetch(url, opts={}) { opts.headers = {...(opts.headers || {}), ...headers()}; const r = await fetch(url, opts); const data = await r.json(); if (!r.ok) throw new Error(data.detail || 'Operacion no completada'); return data; }
function fmt(v) { return v === null || v === undefined ? '--' : v; }
function kpiHtml(label, value) { return `<div class="kpi"><span>${label}</span><b>${fmt(value)}</b></div>`; }
function renderSummary(target, s) { document.getElementById(target).innerHTML = kpiHtml('Filas', s.rows) + kpiHtml('Dias', s.distinct_days) + kpiHtml('Fecha inicio', s.first_date) + kpiHtml('Fecha fin', s.last_date) + kpiHtml('Ventas', money.format(s.total_sales || 0)) + kpiHtml('Ticket medio', money.format(s.avg_transaction_amount || 0)); }
function renderTable(id, rows) { const table = document.getElementById(id); if (!rows || !rows.length) { table.innerHTML = '<tbody><tr><td>Sin filas</td></tr></tbody>'; return; } const cols = Object.keys(rows[0]); table.innerHTML = `<thead><tr>${cols.map(c => `<th>${c}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${cols.map(c => `<td>${fmt(r[c])}</td>`).join('')}</tr>`).join('')}</tbody>`; }
function renderChips(id, items, emptyText) { const el = document.getElementById(id); el.innerHTML = items.length ? items.map(x => `<span class="chip">${x}</span>`).join('') : `<span class="chip">${emptyText}</span>`; }
async function refresh() { const data = await jsonFetch('/api/health'); rows.textContent=data.data.rows||0; first.textContent=data.data.first_date||'--'; dataLast.textContent=data.data.last_date||'--'; modelLast.textContent=data.model.last_observed_date; next.textContent=data.first_predictable_date; const pending = data.pending_retraining || {}; if (pending.needs_retraining) { pendingBox.className = 'notice warn'; pendingBox.textContent = `Hay datos en la base que el modelo todavia no usa. Filas insertadas despues del ultimo entrenamiento: ${pending.rows_inserted_after_training || 0}. Filas con fecha posterior al ultimo dia del modelo: ${pending.rows_after_model_last_date || 0}. Pulsa Reentrenar ahora para actualizar predicciones.`; } else { pendingBox.className = 'notice ok'; pendingBox.textContent = 'Modelo actualizado con todos los datos cargados en la base.'; } const recentData = await jsonFetch('/api/sales/recent?limit=15'); recent.innerHTML = recentData.items.map(x => `<tr><td>${x.date}</td><td>${x.item_name}</td><td>${x.quantity}</td><td>${x.transaction_amount}</td><td>${x.source}</td></tr>`).join(''); }
async function previewCsv() { const f = csv.files[0]; if (!f) throw new Error('Selecciona un CSV'); const fd = new FormData(); fd.append('file', f); const r = await fetch('/api/data/preview-csv', {method:'POST', body:fd, headers:headers()}); const data = await r.json(); if (!r.ok) throw new Error(data.detail); previewPanel.classList.remove('hidden'); previewName.textContent = `Archivo: ${data.filename}. Columnas extra ignoradas: ${data.raw_extra_columns.length ? data.raw_extra_columns.join(', ') : 'ninguna'}.`; renderSummary('historicalSummary', data.historical_summary); renderSummary('uploadSummary', data.upload_summary); const compatibility = []; compatibility.push(`Filas con fechas dentro del rango historico: ${data.overlap_rows_with_existing_date_range}`); compatibility.push(`Columnas requeridas detectadas: ${data.required_columns.length - data.raw_missing_required.length}/${data.required_columns.length}`); if (data.raw_extra_columns.length) compatibility.push(`Columnas extra ignoradas: ${data.raw_extra_columns.join(', ')}`); const nullColumns = Object.entries(data.raw_nulls).filter(([k,v]) => v > 0).map(([k,v]) => `${k}: ${v} nulos`); compatibility.push(nullColumns.length ? `Nulos originales: ${nullColumns.join(' | ')}` : 'Sin nulos originales detectados'); renderChips('compatibility', compatibility, 'Sin alertas'); const cats = []; Object.entries(data.new_categories).forEach(([col, values]) => values.forEach(v => cats.push(`${col}: ${v}`))); renderChips('newCategories', cats, 'No hay categorias nuevas frente al historico'); renderTable('cleanTable', data.clean_preview); renderTable('rawTable', data.raw_preview); }
refreshBtn.onclick = refresh;
previewBtn.onclick = async () => { try { setMsg('uploadMsg', 'Previsualizando limpieza...'); await previewCsv(); setMsg('uploadMsg', 'Previsualizacion lista. Revisa la tabla limpia antes de insertar.'); } catch(e) { setMsg('uploadMsg', e.message, false); } };
uploadBtn.onclick = async () => { try { const f = csv.files[0]; if (!f) throw new Error('Selecciona un CSV'); const fd = new FormData(); fd.append('file', f); const r = await fetch('/api/data/upload-csv', {method:'POST', body:fd, headers:headers()}); const data = await r.json(); if (!r.ok) throw new Error(data.detail); setMsg('uploadMsg', `CSV insertado: ${data.inserted_rows} filas. Ahora falta reentrenar para que el modelo las use.`); await refresh(); } catch(e) { setMsg('uploadMsg', e.message, false); } };
retrainBtn.onclick = async () => { try { setMsg('trainMsg', 'Entrenando...'); const data = await jsonFetch('/api/model/retrain', {method:'POST'}); setMsg('trainMsg', `Modelo reentrenado. MAE validacion: ${data.validation_mae.toFixed(2)}.`); await refresh(); } catch(e) { setMsg('trainMsg', e.message, false); } };
saleBtn.onclick = async () => { try { const payload = {}; ['order_id','date','item_name','item_type','item_price','quantity','transaction_amount','transaction_type','received_by','time_of_sale'].forEach(id => payload[id] = document.getElementById(id).value); payload.order_id=Number(payload.order_id); payload.item_price=Number(payload.item_price); payload.quantity=Number(payload.quantity); payload.transaction_amount=Number(payload.transaction_amount); const data = await jsonFetch('/api/sales', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)}); setMsg('saleMsg', `Venta guardada: ${data.inserted_rows} fila. Falta reentrenar para que el modelo la use.`); await refresh(); } catch(e) { setMsg('saleMsg', e.message, false); } };
date.value = new Date().toISOString().slice(0,10); refresh().catch(e => setMsg('trainMsg', e.message, false));
</script>
</body>
</html>
"""



