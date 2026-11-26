"""Regenerate the complete dashboards (espana.html, artifact.html, turquia.html, usa.html) from template.html."""
import json
import re
from pathlib import Path

USA_MODELS_STYLE = """<style>
.usa-models{padding-block:28px 64px}
.usa-models .cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin-top:8px}
.usa-models .card{border:1px solid var(--rule);background:#f7f8f8;padding:26px;min-width:0}
.usa-models .card h2{font-family:var(--serif);color:var(--accent);font-size:26px;margin:0 0 4px}
.usa-models .note{color:var(--muted);font-size:13px}
.usa-models .number{color:var(--accent);font-size:48px;font-weight:700;margin:14px 0 4px}
.usa-models .date{font-size:14px;color:var(--muted)}
.usa-models a{color:var(--accent)}
.usa-models .badge{display:inline-block;background:#e4edf9;color:var(--accent);font-size:12px;font-weight:600;padding:4px 8px;border-radius:4px;margin-bottom:8px}
@media(max-width:700px){.usa-models .cards{grid-template-columns:1fr}}
.usa-models .sim-section{margin-top:8px}
.usa-models .sim-section>h2{font-family:var(--serif);color:var(--accent);margin:0 0 8px}
.usa-models .sim-controls{border:1px solid var(--rule);padding:20px;background:#fff;border-radius:8px;margin-top:14px}
.usa-models .sim-controls h3{margin:0 0 10px;color:var(--accent);font-size:15px;text-transform:none;letter-spacing:normal}
.usa-models .scenario-list{display:flex;flex-wrap:wrap;gap:8px 14px}
.usa-models .scenario-list label{display:flex;align-items:center;gap:6px;font-size:13px;color:var(--ink);cursor:pointer}
.usa-models .sim-switch{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
.usa-models .sim-switch button{border:1px solid var(--rule);background:#fff;padding:8px 12px;border-radius:999px;color:var(--muted);cursor:pointer;font:500 13px/1.2 var(--sans)}
.usa-models .sim-switch button[aria-pressed=true]{background:var(--accent);color:#fff;border-color:var(--accent)}
.usa-models .sim-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:20px}
.usa-models .sim-chart{margin:0;padding:clamp(12px,1.7vw,24px);border:1px solid #e2e6ea;border-radius:16px;background:#fff;min-width:0}
.usa-models .sim-chart h3{font:700 clamp(17px,1.8vw,23px)/1.18 var(--serif);color:#060e46;margin:0 0 3px;text-transform:none;letter-spacing:normal}
.usa-models .sim-chart .chart-note{font-size:12px;color:var(--muted);margin:0 0 8px}
.usa-models .sim-chart svg{width:100%;height:auto;display:block}
.usa-models .sim-legend{display:flex;flex-wrap:wrap;gap:8px 15px;color:var(--muted);font-size:12px;margin-top:14px}
.usa-models .sim-legend span{display:inline-flex;align-items:center;gap:6px}
.usa-models .sim-legend i{width:16px;height:3px;display:inline-block}
.usa-models .sim-chart svg text,.usa-models .gdp-gallery svg text{font:11px var(--sans);fill:var(--muted)}
.usa-models .sim-chart svg .axis-title{font-size:10px;fill:var(--muted)}
@media(max-width:700px){.usa-models .sim-grid{grid-template-columns:1fr}}
.usa-models .model-tile{font:inherit;text-align:left;cursor:pointer;color:var(--ink);transition:border-color .15s,background .15s}
.usa-models .model-tile:hover,.usa-models .model-tile:focus-visible{border-color:var(--accent);background:#eef5ff}
.usa-models .model-tile:focus-visible,.usa-models .model-back:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
.usa-models .model-action{display:block;color:var(--accent);font-size:13px;font-weight:600;margin-top:20px}
.usa-models .model-detail{margin-top:8px}
.usa-models .model-back{background:none;border:0;padding:0;color:var(--accent);font:600 13px/1.5 var(--sans);cursor:pointer;margin-bottom:18px}
.usa-models .gdp-detail{max-width:740px}
.usa-models .dsge-headline{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:16px 0 6px}
.usa-models .dsge-headline div{min-width:0}
.usa-models .dsge-headline strong{display:block;font:700 clamp(24px,3vw,34px)/1.1 var(--serif);color:var(--accent)}
.usa-models .dsge-headline span{display:block;font-size:12px;color:var(--muted);margin-top:4px}
.usa-models .dsge-key{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:12px;color:var(--muted);margin:8px 0 0}
.usa-models .dsge-key span{display:inline-flex;align-items:center;gap:6px}
.usa-models .dsge-key i{display:inline-block;width:16px;height:3px;background:var(--accent)}
.usa-models .dsge-key i.band{height:10px;opacity:.16;border-radius:2px}
.usa-models .dsge-key i.prev{background:none;border-top:2px dashed #8a94a6;height:0}
.usa-models .dsge-key i{background:#1464ff}
.usa-models .dsge-key i.hist{background:#060e46}
.usa-models .dsge-key i.band{background:#001391}
.usa-models .dsge-controls{display:flex;flex-wrap:wrap;gap:14px 32px;margin-top:20px}
.usa-models .dsge-controls .sim-switch{margin-top:6px}
.usa-models .dsge-label{display:block;font:500 11px/1.2 var(--mono,ui-monospace,monospace);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.usa-models .dsge-readout{font-size:12px;color:var(--ink);margin:6px 0 0;min-height:2.9em}
.usa-models [data-dsge-hit]{cursor:crosshair}
.usa-models .dsge-key i.scenario{background:#d9541e}
.usa-models .dsge-key i.rate{background:#001391}
.usa-models .dsge-key i.spread{background:none;border-top:3px dashed #0a8f7a;height:0}
.usa-models .dsge-scenario-value{color:#b3420f;font-weight:600}
.usa-models .dsge-top{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px;align-items:stretch}
.usa-models .dsge-top.solo{grid-template-columns:minmax(0,740px)}
.usa-models .dsge-top>.gdp-detail{max-width:none;margin:0}
.usa-models .dsge-sim{border:1px solid #e2e6ea;border-radius:16px;background:#fff;padding:clamp(12px,1.7vw,24px);min-width:0}
.usa-models .dsge-table-host{margin-top:18px;max-width:740px}
.usa-models .dsge-table-host>.card{background:#fff;border-color:#e2e6ea;border-radius:16px;padding:clamp(12px,1.7vw,24px)}
.usa-models .dsge-table-host .card h2{font:700 clamp(17px,1.8vw,23px)/1.18 var(--serif);color:#060e46}
@media(max-width:850px){.usa-models .dsge-top{grid-template-columns:minmax(0,1fr)}}
.usa-models .dsge-sim-head{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.usa-models .dsge-sim-head h3{font:700 clamp(17px,1.8vw,23px)/1.18 var(--serif);color:#060e46;margin:0;text-transform:none;letter-spacing:normal}
.usa-models .dsge-sim-head .model-back{margin:0}
.usa-models .dsge-sliders{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 24px;margin:14px 0}
.usa-models .dsge-slider{display:grid;gap:4px;min-width:0}
.usa-models .dsge-slider-head{display:flex;justify-content:space-between;gap:8px;font-size:13px;font-weight:600;color:var(--ink)}
.usa-models .dsge-slider output{font-variant-numeric:tabular-nums;color:var(--accent);white-space:nowrap}
.usa-models .dsge-slider input{width:100%;accent-color:#001391;margin:0}
.usa-models .dsge-slider-hint{font-size:11.5px;color:var(--muted)}
@media(max-width:520px){.usa-models .dsge-sliders{grid-template-columns:1fr}}
.usa-models .dsge-table{width:100%;border-collapse:collapse;font-size:13px;font-variant-numeric:tabular-nums}
.usa-models .dsge-table th,.usa-models .dsge-table td{padding:7px 8px;border-bottom:1px solid #dce4ed;text-align:right;white-space:nowrap}
.usa-models .dsge-table th:first-child,.usa-models .dsge-table td:first-child{text-align:left;white-space:normal}
.usa-models .dsge-table thead th{background:#f1f5fa;color:#001489;font-size:12px}
.usa-models .dsge-table tbody th{font-weight:600;color:#060e46;padding-top:12px;border-bottom:0}
.usa-models .dsge-table .band{color:var(--muted);font-size:12px}
.usa-models .dsge-scroll{overflow-x:auto}
@media(max-width:600px){.usa-models .dsge-headline{grid-template-columns:1fr}}
.usa-models .sim-section>.model-back{display:block}
.usa-models .gdp-component-table th,.usa-models .gdp-component-table td{padding:10px 12px;border-bottom:1px solid #dce4ed}
.usa-models .gdp-component-table th{background:#f1f5fa;color:#001489;font-size:13px}
.usa-models .gdp-component-table td:nth-child(n+2),.usa-models .gdp-component-table th:nth-child(n+2){text-align:right;white-space:nowrap}
.usa-models .gdp-component-table td{font-size:14px}
.usa-models .gdp-components select{padding:8px;border:1px solid #ccd7e4;background:#fff;color:#001489;border-radius:4px}
.usa-models .gdp-breakdown-legend{display:flex;flex-wrap:wrap;gap:8px 18px;color:#526079;font:12px var(--sans);margin:18px 0}
.usa-models .gdp-breakdown-legend span{display:inline-flex;gap:6px;align-items:center}
.usa-models .gdp-breakdown-legend i{display:inline-block;width:14px;height:10px;border-radius:2px}
.usa-models .gdp-gallery{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:18px}
.usa-models .gdp-gallery>.card{margin-top:0!important;min-width:0;background:#fff;border-color:#e2e6ea;border-radius:16px;padding:clamp(12px,1.7vw,24px)}
.usa-models .gdp-gallery .card h2{font:700 clamp(17px,1.8vw,23px)/1.18 var(--serif);color:#060e46}
.usa-models .gdp-gallery svg{display:block}
@media(max-width:850px){.usa-models .gdp-gallery{grid-template-columns:1fr}}
</style>"""

USA_MODELS_HTML = """<section class="wrap usa-models" id="usa-models-host" hidden>
<div class="sechead" id="models-heading"><h2 data-es="Modelos de seguimiento y simulación" data-en="Tracking and simulation models">Modelos de seguimiento y simulación</h2></div>
<div class="cards" id="model-tiles"><button type="button" class="card model-tile" data-open-model="gdpnow" aria-controls="model-gdpnow"><span class="badge">FEDERAL RESERVE BANK OF ATLANTA</span><h2>GDPNow</h2><p class="note" data-es="Estimación del crecimiento del PIB real." data-en="Real GDP growth estimate.">Estimación del crecimiento del PIB real.</p><span class="model-action" data-es="Abrir modelo →" data-en="Open model →">Abrir modelo →</span></button><button type="button" class="card model-tile" data-open-model="frbus" aria-controls="model-frbus"><span class="badge">FEDERAL RESERVE BOARD</span><h2>FRB/US</h2><p class="note" data-es="Comparar escenarios macroeconómicos precalculados." data-en="Compare precomputed macroeconomic scenarios.">Comparar escenarios macroeconómicos precalculados.</p><span class="model-action" data-es="Abrir modelo →" data-en="Open model →">Abrir modelo →</span></button><button type="button" class="card model-tile" data-open-model="dsge" aria-controls="model-dsge"><span class="badge">FEDERAL RESERVE BANK OF NEW YORK</span><h2>DSGE FRB-NY</h2><p class="note" data-es="Previsiones publicadas del modelo DSGE de la Fed de Nueva York." data-en="Published forecasts from the New York Fed DSGE model.">Previsiones publicadas del modelo DSGE de la Fed de Nueva York.</p><span class="model-action" data-es="Abrir modelo →" data-en="Open model →">Abrir modelo →</span></button></div>
<section class="model-detail" id="model-dsge" hidden><button type="button" class="model-back" data-close-model data-es="← Volver a modelos" data-en="← Back to models">← Volver a modelos</button><div class="dsge-top" id="dsge-top"><article class="card gdp-detail"><span class="badge">FEDERAL RESERVE BANK OF NEW YORK</span><h2>DSGE FRB-NY</h2><p class="note" data-es="Previsión del modelo de equilibrio general dinámico y estocástico (DSGE) de la Fed de Nueva York." data-en="Forecast from the New York Fed dynamic stochastic general equilibrium (DSGE) model.">Previsión del modelo de equilibrio general dinámico y estocástico (DSGE) de la Fed de Nueva York.</p><div class="dsge-headline" id="dsge-headline"></div><p class="note" id="dsge-stamp"></p><p class="note" data-es="Cifras publicadas por la Fed de Nueva York, actualizadas automáticamente con cada publicación; aquí no se ejecuta el modelo. No es una previsión oficial de la Fed de Nueva York, sino un insumo de su proceso de previsión." data-en="Figures published by the New York Fed, updated automatically with each release; the model is not run here. It is not an official New York Fed forecast, only an input to its forecasting process.">Cifras publicadas por la Fed de Nueva York, actualizadas automáticamente con cada publicación; aquí no se ejecuta el modelo. No es una previsión oficial de la Fed de Nueva York, sino un insumo de su proceso de previsión.</p><a id="dsge-source" href="#" target="_blank" rel="noopener" data-es="Fuente: Fed de Nueva York, gráficos interactivos ↗" data-en="Source: New York Fed interactive charts ↗">Fuente: Fed de Nueva York, gráficos interactivos ↗</a> · <a id="dsge-posts" href="#" target="_blank" rel="noopener" data-es="Notas de Liberty Street Economics ↗" data-en="Liberty Street Economics posts ↗">Notas de Liberty Street Economics ↗</a></article><section class="dsge-sim" id="dsge-sim" hidden></section></div><div class="dsge-controls" id="dsge-controls"></div><div class="gdp-gallery" id="dsge-gallery"></div><div class="dsge-table-host" id="dsge-table-host"></div></section>
<section class="model-detail" id="model-gdpnow" hidden><button type="button" class="model-back" data-close-model data-es="← Volver a modelos" data-en="← Back to models">← Volver a modelos</button><article class="card gdp-detail"><span class="badge">FEDERAL RESERVE BANK OF ATLANTA</span><h2>GDPNow</h2><p class="note" data-es="Estimación del crecimiento trimestral anualizado del PIB real." data-en="Model estimate of annualized quarterly real GDP growth.">Estimación del crecimiento trimestral anualizado del PIB real.</p><div class="number" id="value">—</div><div class="date" id="period"></div><p class="note" id="gdp-stamp"></p><p class="note" data-es="Estimación mecánica del modelo; no es una previsión oficial del FOMC." data-en="A model estimate, not an official FOMC forecast.">Estimación mecánica del modelo; no es una previsión oficial del FOMC.</p><a href="https://www.atlantafed.org/research-and-data/data/gdpnow" target="_blank" rel="noopener" data-es="Fuente y metodología ↗" data-en="Source and methodology ↗">Fuente y metodología ↗</a><p><button type="button" class="model-back" onclick="document.getElementById('gdp-breakdown-chart').scrollIntoView({behavior:'smooth',block:'center'})" data-es="Ver gráficos de componentes ↓" data-en="View component charts ↓">Ver gráficos de componentes ↓</button></p></article><div class="gdp-gallery"><article class="card" style="margin-top:18px"><h2 data-es="Evolución de la estimación" data-en="Estimate over time">Evolución de la estimación</h2><p class="note" data-es="Crecimiento trimestral anualizado del PIB real. Sitúa el cursor sobre cada punto para ver la fecha y la publicación asociada." data-en="Annualized quarterly real GDP growth. Hover over a point to see its date and associated release.">Crecimiento trimestral anualizado del PIB real. Sitúa el cursor sobre cada punto para ver la fecha y la publicación asociada.</p><p class="note" id="gdp-tracking-note"></p><div id="gdp-tracking-chart" style="width:100%"></div><p class="note">Federal Reserve Bank of Atlanta · <a href="https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/research-and-data/data/gdpnow/GDPTrackingModelDataAndForecasts.xlsx" target="_blank" rel="noopener" data-es="Libro oficial de datos ↗" data-en="Official data workbook ↗">Libro oficial de datos ↗</a></p></article><article class="card" style="margin-top:18px"><h2 data-es="Contribuciones de los componentes al crecimiento del PIB" data-en="Component contributions to GDP growth">Contribuciones de los componentes al crecimiento del PIB</h2><p class="note" data-es="Cada barra muestra las aportaciones al crecimiento trimestral anualizado. La línea muestra la estimación GDPNow." data-en="Each bar shows contributions to annualized quarterly growth. The line shows the GDPNow estimate.">Cada barra muestra las aportaciones al crecimiento trimestral anualizado. La línea muestra la estimación GDPNow.</p><div class="gdp-breakdown-legend"></div><div id="gdp-breakdown-chart"></div><p class="note" data-es="Barras: puntos porcentuales. Línea: crecimiento en %. Fuente: Fed de Atlanta." data-en="Bars: percentage points. Line: growth in %. Source: Atlanta Fed.">Barras: puntos porcentuales. Línea: crecimiento en %. Fuente: Fed de Atlanta.</p></article><article class="card" style="margin-top:18px"><h2 data-es="Revisiones de las contribuciones" data-en="Changes in component contributions">Revisiones de las contribuciones</h2><p class="note" data-es="Variación entre cada publicación y la anterior. La línea representa la revisión total de GDPNow." data-en="Change between each release and the previous one. The line shows the total revision to GDPNow.">Variación entre cada publicación y la anterior. La línea representa la revisión total de GDPNow.</p><div class="gdp-breakdown-legend"></div><div id="gdp-breakdown-change"></div><p class="note" data-es="Revisiones en puntos porcentuales. Fuente: Fed de Atlanta." data-en="Revisions in percentage points. Source: Atlanta Fed.">Revisiones en puntos porcentuales. Fuente: Fed de Atlanta.</p></article><article class="card"><h2 data-es="Crecimiento de los componentes" data-en="Component growth">Crecimiento de los componentes</h2><p class="note" data-es="Crecimiento trimestral anualizado de los componentes principales. La fecha seleccionada se cambia en la tabla inferior." data-en="Annualized quarterly growth of main components. Change the selected date in the table below.">Crecimiento trimestral anualizado de los componentes principales. La fecha seleccionada se cambia en la tabla inferior.</p><p class="note" id="gdp-growth-date"></p><div id="gdp-growth-chart"></div><p class="note" data-es="Porcentaje trimestral anualizado. Fuente: Fed de Atlanta." data-en="Annualized quarterly percent. Source: Atlanta Fed.">Porcentaje trimestral anualizado. Fuente: Fed de Atlanta.</p></article></div><article class="card gdp-components" style="margin-top:18px"><h2 data-es="Componentes del PIB" data-en="GDP components">Componentes del PIB</h2><p class="note" data-es="Estimaciones del trimestre. Selecciona una fecha de publicación para consultar los componentes." data-en="Quarterly estimates. Select a release date to inspect the components.">Estimaciones del trimestre. Selecciona una fecha de publicación para consultar los componentes.</p><label for="gdp-component-date" data-es="Fecha de la estimación" data-en="Estimate date">Fecha de la estimación</label> <select id="gdp-component-date"></select><div style="overflow-x:auto;margin-top:14px"><table style="width:100%;border-collapse:collapse;text-align:left" class="gdp-component-table"><thead><tr><th data-es="Componente" data-en="Component">Componente</th><th data-es="Crecimiento anualizado" data-en="Annualized growth">Crecimiento anualizado</th><th data-es="Contribución al PIB" data-en="Contribution to GDP">Contribución al PIB</th></tr></thead><tbody id="gdp-component-body"></tbody></table></div><p class="note" data-es="Crecimiento en % intertrimestral anualizado; contribuciones en puntos porcentuales (pp). Las filas con sangría forman parte de los agregados superiores y no deben sumarse de nuevo. La inversión privada incluye existencias; las importaciones restan al PIB." data-en="Growth is annualized quarter-on-quarter, in %; contributions are in percentage points (pp). Indented rows are included in their parent aggregates and should not be added again. Private investment includes inventories; imports subtract from GDP.">Crecimiento en % intertrimestral anualizado; contribuciones en puntos porcentuales (pp). Las filas con sangría forman parte de los agregados superiores y no deben sumarse de nuevo. La inversión privada incluye existencias; las importaciones restan al PIB.</p><p class="note">Fuente / Source: Federal Reserve Bank of Atlanta · GDPNow</p></article></section>
<section class="sim-section" id="model-frbus" aria-label="FRB/US" hidden><button type="button" class="model-back" data-close-model data-es="← Volver a modelos" data-en="← Back to models">← Volver a modelos</button><h2 data-es="FRB/US: escenarios ilustrativos" data-en="FRB/US: illustrative scenarios">FRB/US: escenarios ilustrativos</h2><p class="note" data-es="Simulaciones calculadas con el modelo FRB/US y la trayectoria pública LONGBASE; 2040T1–2045T4. No son previsiones oficiales de la Reserva Federal. Los shocks de consumo y vivienda modifican residuos de ecuaciones. El shock de tipos durante cuatro trimestres se aplica repetidamente a la ecuación de política: no fija la trayectoria del tipo." data-en="Simulations computed with FRB/US and the public LONGBASE baseline; 2040Q1–2045Q4. These are not official Federal Reserve forecasts. Consumption and housing shocks change equation residuals. The four-quarter rate shock is repeatedly applied to the policy equation; it does not fix the path of the rate.">Simulaciones calculadas con el modelo FRB/US y la trayectoria pública LONGBASE; 2040T1–2045T4. No son previsiones oficiales de la Reserva Federal. Los shocks de consumo y vivienda modifican residuos de ecuaciones. El shock de tipos durante cuatro trimestres se aplica repetidamente a la ecuación de política: no fija la trayectoria del tipo.</p><div class="sim-controls"><h3 data-es="Seleccionar escenarios" data-en="Select scenarios">Seleccionar escenarios</h3><div class="scenario-list" id="scenario-list"></div><div class="sim-switch" role="group" aria-label="Visualización / Display"><button type="button" data-sim-mode="levels" aria-pressed="true" data-es="Trayectorias" data-en="Paths">Trayectorias</button><button type="button" data-sim-mode="delta" aria-pressed="false" data-es="Diferencia respecto a la base" data-en="Difference from baseline">Diferencia respecto a la base</button></div></div><div id="sim-legend" class="sim-legend"></div><div class="sim-grid" id="sim-grid"></div><p class="note" data-es="Datos precalculados en el Mac del usuario. Cambiar la selección no ejecuta de nuevo el modelo. Fuente: Federal Reserve Board, modelo FRB/US; cálculos de escenarios propios." data-en="Precomputed on the user's Mac. Changing the selection does not rerun the model. Source: Federal Reserve Board, FRB/US model; scenario calculations by the user.">Datos precalculados en el Mac del usuario. Cambiar la selección no ejecuta de nuevo el modelo. Fuente: Federal Reserve Board, modelo FRB/US; cálculos de escenarios propios.</p></section>
</section>"""

USA_MODELS_SCRIPTS = """<script id="frbus-embedded" type="application/json">__FRBUS__</script>
<script id="dsge-frbny-data" type="application/json">__DSGE_FRBNY__</script>
<script id="dsge-irf-data" type="application/json">__DSGE_IRF__</script>
<script id="gdpnow-tracking-data" type="application/json">__GDPNOW_TRACKING__</script>
<script>
(function(){
  const host=document.getElementById('usa-models-host');
  if(!host)return;
  const snapshot=__GDPNOW_SNAPSHOT__;
  let gdp=snapshot;
  const getLang=()=>document.documentElement.lang==='en'?'en':'es';
  function renderGdpCard(){
    const lang=getLang();
    host.querySelectorAll('[data-es][data-en]').forEach(el=>{el.textContent=el.dataset[lang];});
    document.getElementById('value').textContent=typeof gdp.value==='number'?gdp.value.toLocaleString(lang==='es'?'es-ES':'en-US',{minimumFractionDigits:1,maximumFractionDigits:1})+' %':'—';
    document.getElementById('period').textContent=(lang==='es'?'Trimestre: ':'Quarter: ')+(gdp.quarter||'—');
    document.getElementById('gdp-stamp').textContent=(lang==='es'?'Última actualización publicada: ':'Last published update: ')+(gdp.updated_at||'—').slice(0,10);
  }
  function fetchGdpNow(){
    if(location.protocol==='file:')return;
    fetch('gdpnow.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(x=>{if(typeof x.value==='number'&&x.quarter&&x.updated_at){gdp=x;renderGdpCard();}}).catch(()=>{});
  }
  window.addEventListener('mme-lang-change',renderGdpCard);
  window.addEventListener('mme-usa-refresh',fetchGdpNow);
  renderGdpCard();
  fetchGdpNow();

  const results=JSON.parse(document.getElementById('frbus-embedded').textContent);
  const selected=new Set(['tipos_mas_25','tipos_mas_50','tipos_mas_100']);let mode='levels';
  const colors=['#1168E8','#D87600','#008F7B','#7B5CD6','#B4387A','#678131','#8C6D00','#5B7C9A'];
  const english={'tipos_mas_25':'Rates +25 bp, one quarter','tipos_mas_50':'Rates +50 bp, one quarter','tipos_mas_100':'Rates +100 bp, one quarter','tipos_menos_100':'Rates −100 bp, one quarter','tipos_mas_100_persistente':'Policy-equation shock +100 bp for four quarters','prima_credito_mas_100':'BBB premium +100 bp, one quarter','consumo_shock':'Negative consumption-equation shock','vivienda_shock':'Negative housing-equation shock'};
  const safeLabels={'tipos_mas_100_persistente':'Shock en ecuación de política +100 pb durante cuatro trimestres'};
  const vars=[{id:'pib',es:'Crecimiento del PIB real',en:'Real GDP growth',unit:'% a/a',unitEn:'% y/y'},{id:'paro',es:'Tasa de desempleo',en:'Unemployment rate',unit:'%',unitEn:'%'},{id:'inflacion',es:'Inflación PCE subyacente',en:'Core PCE inflation',unit:'% a/a',unitEn:'% y/y'},{id:'tipos',es:'Tipo de los fondos federales',en:'Federal funds rate',unit:'%',unitEn:'%'}];
  const e=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const label=s=>getLang()==='en'?(english[s.id]||s.label):(safeLabels[s.id]||s.label);
  const lookup=new Map(results.datos.map(r=>[r.escenario+'|'+r.indicador+'|'+r.trimestre,r]));
  const quarters=[...new Set(results.datos.map(r=>r.trimestre))].sort();
  const choose=()=>results.escenarios.filter(s=>selected.has(s.id));
  const local=(x,d=2)=>Number(x).toLocaleString(getLang()==='es'?'es-ES':'en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
  function seriesFor(metric,scenario){return quarters.map(q=>{const r=lookup.get(scenario.id+'|'+metric+'|'+q);return r?{q,base:r.base,val:mode==='levels'?r.simulacion:r.diferencia}:null;});}
  function makeChart(metric){
    const lang=getLang(),chosen=choose(),ref=results.escenarios[0],base=seriesFor(metric.id,ref);
    let lines=chosen.map(s=>({id:s.id,name:label(s),color:colors[results.escenarios.findIndex(a=>a.id===s.id)%colors.length],points:seriesFor(metric.id,s)}));
    if(mode==='levels')lines=[{id:'base',name:lang==='en'?'Baseline':'Base',color:'#001391',points:base.map(r=>r?{q:r.q,val:r.base}:null)},...lines];
    else lines=[{id:'base',name:lang==='en'?'Baseline':'Base',color:'#001391',points:quarters.map(q=>({q,val:0}))},...lines];
    const vals=lines.flatMap(l=>l.points.filter(p=>p&&typeof p.val==='number'&&Number.isFinite(p.val)).map(p=>p.val));if(!vals.length)return '<p class="note">Sin datos</p>';
    let lo=Math.min(...vals),hi=Math.max(...vals);if(hi===lo){lo-=.05;hi+=.05}else{const p=(hi-lo)*.12;lo-=p;hi+=p}const W=560,H=265,L=62,R=16,T=14,B=36,w=W-L-R,h=H-T-B;
    const X=i=>L+i*w/Math.max(1,quarters.length-1),Y=v=>T+(hi-v)*h/(hi-lo),dec=(hi-lo)<.1?3:2;
    let svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${e(lang==='en'?metric.en:metric.es)}">`;
    for(let k=0;k<=4;k++){const v=lo+(hi-lo)*k/4,y=Y(v);svg+=`<line x1="${L}" x2="${W-R}" y1="${y}" y2="${y}" stroke="#e2e6ea"/><text x="${L-8}" y="${y+4}" text-anchor="end">${local(v,dec)}</text>`;}
    for(let i=0;i<quarters.length;i+=4)svg+=`<text x="${X(i)}" y="${H-10}" text-anchor="middle">${e(quarters[i])}</text>`;
    lines.forEach(line=>{let d='';line.points.forEach((p,i)=>{if(p&&Number.isFinite(p.val))d+=(d?'L':'M')+X(i).toFixed(2)+','+Y(p.val).toFixed(2);});svg+=`<path d="${d}" fill="none" stroke="${line.color}" stroke-width="${line.id==='base'?2.5:1.8}" stroke-linejoin="round"/>`;line.points.forEach((p,i)=>{if(!p||!Number.isFinite(p.val))return;svg+=`<circle cx="${X(i).toFixed(2)}" cy="${Y(p.val).toFixed(2)}" r="3" fill="${line.color}" opacity="0.65"><title>${e(line.name)} · ${e(p.q)}: ${local(p.val,3)} ${mode==='delta'?'pp':'%'}</title></circle>`;});});return svg+'</svg>';
  }
  function renderSimulation(){
    const lang=getLang(),list=document.getElementById('scenario-list');
    list.innerHTML=results.escenarios.map(s=>`<label><input type="checkbox" data-scenario="${e(s.id)}" ${selected.has(s.id)?'checked':''}><span>${e(label(s))}</span></label>`).join('');
    list.querySelectorAll('input').forEach(box=>box.addEventListener('change',()=>{box.checked?selected.add(box.dataset.scenario):selected.delete(box.dataset.scenario);renderSimulation();}));
    host.querySelectorAll('[data-sim-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.simMode===mode)));
    const legend=[{name:lang==='en'?'Baseline':'Base',color:'#001391'},...choose().map(s=>({name:label(s),color:colors[results.escenarios.findIndex(a=>a.id===s.id)%colors.length]}))];
    document.getElementById('sim-legend').innerHTML=legend.map(l=>`<span><i style="background:${l.color}"></i>${e(l.name)}</span>`).join('');
    document.getElementById('sim-grid').innerHTML=vars.map(v=>`<figure class="sim-chart"><h3>${e(lang==='en'?v.en:v.es)}</h3><p class="chart-note">${mode==='levels'?(lang==='en'?v.unitEn:v.unit):(lang==='en'?'Difference from baseline, percentage points':'Diferencia respecto a la base, puntos porcentuales')}</p>${makeChart(v)}</figure>`).join('');
  }
  host.querySelectorAll('[data-sim-mode]').forEach(b=>b.addEventListener('click',()=>{mode=b.dataset.simMode;renderSimulation();}));
  window.addEventListener('mme-lang-change',renderSimulation);
  renderSimulation();

  const tiles=document.getElementById('model-tiles');
  // DSGE FRB-NY: previsiones publicadas por la Fed de Nueva York (no se ejecuta el modelo).
  let dsge=null;try{dsge=JSON.parse(document.getElementById('dsge-frbny-data').textContent);}catch(err){}
  const dsgeTile=host.querySelector('[data-open-model="dsge"]');
  let dsgeIrf=null;try{dsgeIrf=JSON.parse(document.getElementById('dsge-irf-data').textContent);}catch(err){}
  const dsgeState={bands:new Set([50,68,90]),span:'recent',shocks:{}};
  const DSGE_VARS=[['gdp','Crecimiento del PIB','GDP growth'],['core_pce','Inflación PCE subyacente','Core PCE inflation'],['rstar','Tipo de interés natural real','Real natural rate of interest']];
  const dsgeValid=d=>!!(d&&d.table&&d.table.current&&d.table.current.rows&&d.fans&&DSGE_VARS.every(([k])=>d.fans[k]&&Array.isArray(d.fans[k].dates)&&d.fans[k].dates.length));
  function renderDsge(keepSimulator){
    if(!dsgeValid(dsge)){dsgeTile.hidden=true;return;}
    dsgeTile.hidden=false;
    const lang=getLang(), es=lang==='es', locale=es?'es-ES':'en-US';
    const n=v=>v==null?'—':v.toLocaleString(locale,{minimumFractionDigits:1,maximumFractionDigits:1});
    const esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
    const day=d=>new Date(d.slice(0,10)+'T00:00:00').toLocaleDateString(es?'es-ES':'en-GB',{day:'numeric',month:'long',year:'numeric'});
    const vintage=d=>new Date(d+'T00:00:00').toLocaleDateString(es?'es-ES':'en-GB',{month:'short',year:'numeric'});
    const quarter=d=>(es?'T':'Q')+Math.ceil(+d.slice(5,7)/3)+' '+d.slice(0,4);
    const name=k=>{const v=DSGE_VARS.find(x=>x[0]===k);return es?v[1]:v[2];};
    const pct=b=>b+(es?' %':'%');
    const table=dsge.table, cur=table.current, prev=table.previous, years=cur.years;
    const curLabel=vintage(cur.release), prevLabel=prev&&prev.release?vintage(prev.release):'';
    document.getElementById('dsge-source').href=dsge.source_url;
    document.getElementById('dsge-posts').href=dsge.posts_url;
    document.getElementById('dsge-headline').innerHTML=DSGE_VARS.map(([k])=>`<div><strong>${n(cur.rows[k][0][0])} %</strong><span>${esc(name(k))} · ${es?'4T ':'Q4 '}${years[0]}</span></div>`).join('');
    document.getElementById('dsge-stamp').textContent=(es?'Última publicación de la Fed de Nueva York: ':'Latest New York Fed release: ')+day(dsge.release)+(dsge.fetched_at?(es?' · comprobado el ':' · checked on ')+day(dsge.fetched_at):'');
    const pills=(items,attr,on)=>items.map(([value,label])=>`<button type="button" ${attr}="${value}" aria-pressed="${on(value)}">${label}</button>`).join('');
    document.getElementById('dsge-controls').innerHTML=`<div><span class="dsge-label">${es?'Bandas de probabilidad':'Probability bands'}</span><div class="sim-switch" role="group" aria-label="${es?'Bandas de probabilidad':'Probability bands'}">${pills(dsge.bands.map(b=>[b,pct(b)]),'data-dsge-band-toggle',b=>dsgeState.bands.has(b))}</div></div>
      <div><span class="dsge-label">${es?'Periodo':'Period'}</span><div class="sim-switch" role="group" aria-label="${es?'Periodo':'Period'}">${pills([['recent',es?'Últimos 3 años y previsión':'Last 3 years and forecast'],['all',es?'Desde 2021':'Since 2021']],'data-dsge-span',v=>dsgeState.span===v)}</div></div>`;
    const W=520,H=260,pl=44,pr=14,pt=14,pb=30;
    const frame=(dates,values,draw)=>{
      const finite=values.filter(v=>v!=null);
      let lo=Math.min(...finite,0), hi=Math.max(...finite);
      const span=hi-lo, step=span>40?10:span>16?4:span>8?2:1;
      lo=Math.floor(lo/step)*step; hi=Math.ceil(hi/step)*step; if(hi===lo) hi=lo+step;
      const x=i=>pl+i*(W-pl-pr)/Math.max(1,dates.length-1), y=v=>pt+(hi-v)/(hi-lo)*(H-pt-pb);
      let g='';
      for(let t=lo;t<=hi+1e-9;t+=step) g+=`<line x1="${pl}" x2="${W-pr}" y1="${y(t)}" y2="${y(t)}" stroke="${t===0?'#8a94a6':'#e2e6ea'}"/><text x="${pl-8}" y="${y(t)+4}" text-anchor="end">${t.toLocaleString(locale)}</text>`;
      dates.forEach((d,i)=>{if(d.slice(5,7)==='03') g+=`<line x1="${x(i)}" x2="${x(i)}" y1="${H-pb}" y2="${H-pb+4}" stroke="#8a94a6"/><text x="${x(i)}" y="${H-8}" text-anchor="middle">${d.slice(0,4)}</text>`;});
      return g+draw(x,y);
    };
    const path=(values,x,y)=>{let d='',open=false;values.forEach((v,i)=>{if(v==null){open=false;return;}d+=(open?'L':'M')+x(i).toFixed(1)+','+y(v).toFixed(1);open=true;});return d;};
    const svg=(label,inner)=>`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(label)}" style="width:100%;height:auto">${inner}<line data-dsge-cursor x1="0" x2="0" y1="${pt}" y2="${H-pb}" stroke="#8a94a6" stroke-dasharray="3 3" visibility="hidden"/><rect data-dsge-hit x="${pl}" y="${pt}" width="${W-pl-pr}" height="${H-pt-pb}" fill="transparent"/></svg>`;
    const first=series=>series.forecast.findIndex(v=>v!=null);
    const from=(series,start)=>dsgeState.span==='all'?0:Math.max(0,start-12);
    // Simulador: el modelo es lineal, así que cada respuesta se escala con su deslizador y se suman.
    const sim=dsgeIrf&&dsgeIrf.shocks&&Object.keys(dsgeIrf.shocks).length?dsgeIrf:null;
    const sizes=sim?Object.keys(sim.shocks).filter(k=>dsgeState.shocks[k]).map(k=>[sim.shocks[k].responses,dsgeState.shocks[k]]):[];
    const simulating=sizes.length>0;
    const releaseQuarter=dsge.release.slice(0,4)+'-'+['03-31','06-30','09-30','12-31'][Math.ceil(+dsge.release.slice(5,7)/3)-1];
    const shockIndex=dates=>dates.findIndex(d=>d>releaseQuarter);
    const quarterly=(series,h)=>h<0?0:sizes.reduce((sum,[responses,size])=>sum+size*(responses[series][h]||0),0);
    const annualized=(series,h)=>4*quarterly(series,h);
    const fourQuarter=(series,h)=>quarterly(series,h)+quarterly(series,h-1)+quarterly(series,h-2)+quarterly(series,h-3);
    const scenario=(dates,base,effect)=>{const at=shockIndex(dates); return base.map((v,i)=>!simulating||at<0||v==null||i<at-1?null:v+(i<at?0:effect(i-at)));};
    const scenarioPath=(values,x,y)=>simulating?`<path data-dsge-scenario d="${path(values,x,y)}" fill="none" stroke="#d9541e" stroke-width="2.4" stroke-linejoin="round"/>`:'';
    const scenarioKey=simulating?`<span><i class="scenario"></i>${es?'Escenario':'Scenario'}</span>`:'';
    const hint=es?'Pasa el cursor por el gráfico para ver los valores de cada trimestre.':'Hover over the chart to see the values for each quarter.';
    const charts={};
    const fanCard=k=>{
      const fan=dsge.fans[k], start=first(fan), a=from(fan,start), shown=[...dsgeState.bands].sort((p,q)=>q-p);
      const dates=fan.dates.slice(a), history=fan.history.slice(a), forecast=fan.forecast.slice(a);
      const bands=shown.map(b=>[b,fan.bands[String(b)].slice(a)]);
      const effect=k==='rstar'?h=>annualized('rstar_q',h):h=>fourQuarter(k+'_q',h);
      const scen=scenario(dates,forecast,effect), at=shockIndex(dates);
      const values=[...history,...forecast,...scen,...bands.flatMap(([,rows])=>rows.flat())];
      const inner=frame(dates,values,(x,y)=>{
        let g=bands.map(([b,rows])=>`<path data-dsge-band="${b}" d="${rows.map((r,i)=>(i?'L':'M')+x(i).toFixed(1)+','+y(r[1]).toFixed(1)).join(' ')} ${rows.map((r,i)=>'L'+x(i).toFixed(1)+','+y(r[0]).toFixed(1)).reverse().join(' ')} Z" fill="#001391" opacity="0.11"/>`).join('');
        g+=`<line x1="${x(start-a)}" x2="${x(start-a)}" y1="${pt}" y2="${H-pb}" stroke="#8a94a6" stroke-dasharray="4 4"/>`;
        g+=`<path data-dsge-history d="${path(history,x,y)}" fill="none" stroke="#060e46" stroke-width="2.2" stroke-linejoin="round"/><path data-dsge-mean d="${path(forecast,x,y)}" fill="none" stroke="#1464ff" stroke-width="2.4" stroke-linejoin="round"/>`+scenarioPath(scen,x,y);
        return g;
      });
      charts[k]={dates,read:i=>{const mean=forecast[i]!=null?forecast[i]:history[i];
        return `<b>${quarter(dates[i])}</b> · ${forecast[i]!=null&&i>start-a?(es?'previsión':'forecast'):(es?'dato':'actual')} ${n(mean)}`+(simulating&&at>=0&&i>=at&&scen[i]!=null?` · <span class="dsge-scenario-value">${es?'escenario':'scenario'} ${n(scen[i])}</span>`:'')+(i>start-a?bands.slice().reverse().map(([b,rows])=>` · ${pct(b)}: ${n(rows[i][0])} ${es?'a':'to'} ${n(rows[i][1])}`).join(''):'');}};
      const unit=k==='rstar'?(es?'Porcentaje.':'Percent.'):(es?'Variación en cuatro trimestres, %.':'Four-quarter percent change.');
      return `<article class="card" data-dsge-chart="${k}"><h2>${esc(name(k))}</h2><p class="note">${unit} ${es?'Media y bandas de probabilidad.':'Mean and probability bands.'}</p>${svg(name(k),inner)}<p class="dsge-readout" data-dsge-readout>${hint}</p><p class="dsge-key"><span><i class="hist"></i>${es?'Dato':'Actual'}</span><span><i></i>${es?'Previsión (media)':'Forecast (mean)'}</span>${shown.length?`<span><i class="band"></i>${es?'Bandas ':'Bands '}${shown.slice().reverse().map(pct).join(', ')}</span>`:''}${scenarioKey}</p></article>`;
    };
    const revisionCard=k=>{
      const rev=dsge.revisions&&dsge.revisions[k]; if(!rev||!Array.isArray(rev.dates)) return '';
      const start=rev.current.findIndex(v=>v!=null), a=from(rev,start);
      const dates=rev.dates.slice(a), history=rev.history.slice(a), now=rev.current.slice(a), before=rev.previous.slice(a);
      const scen=scenario(dates,now,h=>annualized(k+'_q',h)), at=shockIndex(dates);
      const inner=frame(dates,[...history,...now,...before,...scen],(x,y)=>`<path data-dsge-history d="${path(history,x,y)}" fill="none" stroke="#060e46" stroke-width="2.2" stroke-linejoin="round"/><path data-dsge-previous d="${path(before,x,y)}" fill="none" stroke="#8a94a6" stroke-width="1.8" stroke-dasharray="5 4"/><path data-dsge-mean d="${path(now,x,y)}" fill="none" stroke="#1464ff" stroke-width="2.4" stroke-linejoin="round"/>`+scenarioPath(scen,x,y));
      const id='rev-'+k;
      charts[id]={dates,read:i=>`<b>${quarter(dates[i])}</b>`+(history[i]!=null?` · ${es?'dato':'actual'} ${n(history[i])}`:'')+(now[i]!=null?` · ${es?'previsión actual':'current forecast'} ${n(now[i])}`:'')+(before[i]!=null?` · ${es?'anterior':'previous'} ${n(before[i])}`:'')+(simulating&&at>=0&&i>=at&&scen[i]!=null?` · <span class="dsge-scenario-value">${es?'escenario':'scenario'} ${n(scen[i])}</span>`:'')};
      return `<article class="card" data-dsge-chart="${id}"><h2>${esc(name(k))}: ${es?'revisión de la previsión':'forecast revision'}</h2><p class="note">${es?'Variación trimestral anualizada, %. Previsión actual frente a la anterior.':'Quarter-to-quarter percent change, annualized. Current versus previous forecast.'}</p>${svg(name(k),inner)}<p class="dsge-readout" data-dsge-readout>${hint}</p><p class="dsge-key"><span><i class="hist"></i>${es?'Dato':'Actual'}</span><span><i></i>${es?'Previsión actual':'Current forecast'}</span><span><i class="prev"></i>${es?'Previsión anterior':'Previous forecast'}</span>${scenarioKey}</p></article>`;
    };
    const effectCard=()=>{
      if(!sim) return '';
      const fan=dsge.fans.gdp, at=shockIndex(fan.dates); if(at<0) return '';
      const dates=fan.dates.slice(Math.max(0,at-1)), offset=at>0?1:0;
      const line=series=>dates.map((d,i)=>annualized(series,i-offset));
      const rate=line('ffr_q'), spread=line('spread_q');
      const inner=frame(dates,[...rate,...spread,-0.5,0.5],(x,y)=>`<path data-dsge-effect="ffr" d="${path(rate,x,y)}" fill="none" stroke="#001391" stroke-width="2.4" stroke-linejoin="round"/><path data-dsge-effect="spread" d="${path(spread,x,y)}" fill="none" stroke="#0a8f7a" stroke-width="2.4" stroke-linejoin="round" stroke-dasharray="6 3"/>`);
      charts.effect={dates,read:i=>`<b>${quarter(dates[i])}</b> · ${es?'tipo oficial':'policy rate'} ${n(rate[i])} pp · ${es?'diferencial':'spread'} ${n(spread[i])} pp`};
      return `<article class="card" data-dsge-chart="effect"><h2>${es?'Efecto del escenario sobre los tipos':'Scenario effect on rates'}</h2><p class="note">${es?'Desviación respecto a la previsión, en puntos porcentuales (anualizado).':'Deviation from the forecast, in percentage points (annualized).'}</p>${svg(es?'Efecto sobre los tipos':'Effect on rates',inner)}<p class="dsge-readout" data-dsge-readout>${simulating?hint:(es?'Mueve los deslizadores para ver el efecto.':'Move the sliders to see the effect.')}</p><p class="dsge-key"><span><i class="rate"></i>${es?'Tipo de los fondos federales':'Federal funds rate'}</span><span><i class="spread"></i>${es?'Diferencial de crédito (Baa–Tesoro)':'Credit spread (Baa–Treasury)'}</span></p></article>`;
    };
    if(!keepSimulator){
      const simHost=document.getElementById('dsge-sim');
      document.getElementById('dsge-top').classList.toggle('solo',!sim||shockIndex(dsge.fans.gdp.dates)<0);
      if(!sim||shockIndex(dsge.fans.gdp.dates)<0){simHost.hidden=true;simHost.innerHTML='';}
      else{
        simHost.hidden=false;
        const when=quarter(dsge.fans.gdp.dates[shockIndex(dsge.fans.gdp.dates)]);
        const impact=shock=>{const v=shock.responses[shock.own][0]*4*(shock.own_unit==='bp'?100:1); const what={ffr_q:es?'en el tipo oficial':'on the policy rate',spread_q:es?'en el diferencial de crédito':'on the credit spread',gdp_q:es?'en el crecimiento trimestral anualizado del PIB':'on annualized quarterly GDP growth',core_pce_q:es?'en la inflación trimestral anualizada':'on annualized quarterly inflation'}[shock.own];
          return `+1 ${es?'d. t.':'s.d.'} ≈ ${v>=0?'+':'−'}${shock.own_unit==='bp'?Math.round(Math.abs(v)).toLocaleString(locale)+(es?' pb':' bp'):n(Math.abs(v))+' pp'} ${what}`;};
        simHost.innerHTML=`<div class="dsge-sim-head"><h3>${es?'Simulador de shocks':'Shock simulator'}</h3><button type="button" class="model-back" data-dsge-reset>${es?'Restablecer':'Reset'}</button></div>
          <p class="note">${es?`Escenario = previsión publicada + respuesta del modelo a los shocks elegidos, que ocurren en ${when}. Tamaño en desviaciones típicas (d. t.).`:`Scenario = published forecast + the model response to the chosen shocks, which hit in ${when}. Size in standard deviations (s.d.).`}</p>
          <div class="dsge-sliders">${Object.entries(sim.shocks).map(([id,shock])=>`<label class="dsge-slider"><span class="dsge-slider-head"><span>${esc(shock[lang])}</span><output data-dsge-size="${id}"></output></span><input type="range" min="-3" max="3" step="0.25" value="${dsgeState.shocks[id]||0}" data-dsge-shock="${id}"><span class="dsge-slider-hint">${impact(shock)}</span></label>`).join('')}</div>
          <p class="note">${es?`Cálculo propio con ${esc(sim.model)} (especificación ${esc(sim.subspec)}) de ${esc(sim.package)}, el paquete público de la Fed de Nueva York, con sus parámetros por defecto, que no tienen por qué coincidir con la estimación actual de la Fed. No es una previsión ni un escenario de la Fed de Nueva York. Las bandas son las de la previsión publicada y no se recalculan.`:`Own calculation with ${esc(sim.model)} (specification ${esc(sim.subspec)}) from ${esc(sim.package)}, the New York Fed public package, with its default parameters, which need not match the Fed current estimate. It is not a New York Fed forecast or scenario. Bands are those of the published forecast and are not recomputed.`}</p>`;
      }
    }
    document.querySelectorAll('#dsge-sim [data-dsge-size]').forEach(out=>{const v=dsgeState.shocks[out.dataset.dsgeSize]||0; out.textContent=(v>0?'+':v<0?'−':'')+Math.abs(v).toLocaleString(locale,{minimumFractionDigits:2,maximumFractionDigits:2})+(es?' d. t.':' s.d.');});
    const cell=r=>r?`${n(r[0])} <span class="band">(${n(r[1])}; ${n(r[2])})</span>`:'—';
    const tableCard=`<article class="card" data-dsge-chart="table"><h2>${es?'Comparación de previsiones':'Forecast comparison'}</h2><p class="note">${es?'4T/4T (tipo natural: 4T). Media y, entre paréntesis, banda del ':'Q4/Q4 (natural rate: Q4). Mean and, in parentheses, the '}${pct(table.band)}${es?'.':' band.'}</p><div class="dsge-scroll"><table class="dsge-table"><thead><tr><th>${es?'Año':'Year'}</th><th>${curLabel}</th>${prev?`<th>${prevLabel}</th>`:''}</tr></thead><tbody>${DSGE_VARS.map(([k])=>`<tr class="group"><th scope="rowgroup" colspan="${prev?3:2}">${esc(name(k))}</th></tr>`+years.map((yr,i)=>{const old=prev&&prev.rows&&prev.rows[k]&&prev.years?prev.rows[k][prev.years.indexOf(yr)]:null;return `<tr data-dsge-row="${k}-${yr}"><td>${yr}</td><td>${cell(cur.rows[k][i])}</td>${prev?`<td>${cell(old)}</td>`:''}</tr>`;}).join('')).join('')}</tbody></table></div></article>`;
    const gallery=document.getElementById('dsge-gallery');
    // Primero los dos gráficos comparativos; después los abanicos y el efecto sobre los tipos (galería de 2 × 3).
    gallery.innerHTML=revisionCard('gdp')+revisionCard('core_pce')+DSGE_VARS.map(([k])=>fanCard(k)).join('')+effectCard();
    document.getElementById('dsge-table-host').innerHTML=tableCard;
    gallery.querySelectorAll('[data-dsge-hit]').forEach(hit=>{
      const card=hit.closest('[data-dsge-chart]'), info=charts[card.dataset.dsgeChart], cursor=card.querySelector('[data-dsge-cursor]'), readout=card.querySelector('[data-dsge-readout]');
      const move=event=>{const box=hit.getBoundingClientRect(); const i=Math.max(0,Math.min(info.dates.length-1,Math.round((event.clientX-box.left)/box.width*(info.dates.length-1))));
        const px=pl+i*(W-pl-pr)/Math.max(1,info.dates.length-1); cursor.setAttribute('x1',px); cursor.setAttribute('x2',px); cursor.setAttribute('visibility','visible'); readout.innerHTML=info.read(i);};
      hit.addEventListener('pointermove',move); hit.addEventListener('pointerdown',move);
      hit.addEventListener('pointerleave',()=>{cursor.setAttribute('visibility','hidden'); readout.textContent=hint;});
    });
  }
  document.getElementById('dsge-controls').addEventListener('click',event=>{
    const button=event.target.closest('button'); if(!button) return;
    if(button.dataset.dsgeBandToggle){const b=+button.dataset.dsgeBandToggle; dsgeState.bands.has(b)?dsgeState.bands.delete(b):dsgeState.bands.add(b);}
    else if(button.dataset.dsgeSpan) dsgeState.span=button.dataset.dsgeSpan; else return;
    const selector=button.dataset.dsgeBandToggle?`[data-dsge-band-toggle="${button.dataset.dsgeBandToggle}"]`:`[data-dsge-span="${button.dataset.dsgeSpan}"]`;
    renderDsge(true); document.querySelector('#dsge-controls '+selector)?.focus();
  });
  const dsgeSim=document.getElementById('dsge-sim');
  dsgeSim.addEventListener('input',event=>{const id=event.target.dataset.dsgeShock; if(!id) return; dsgeState.shocks[id]=+event.target.value; renderDsge(true);});
  dsgeSim.addEventListener('click',event=>{if(!event.target.closest('[data-dsge-reset]')) return; dsgeState.shocks={}; renderDsge(); dsgeSim.querySelector('[data-dsge-reset]')?.focus();});
  function fetchDsge(){
    if(location.protocol==='file:')return;
    fetch('dsge_frbny.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(x=>{if(dsgeValid(x)&&(!dsgeValid(dsge)||x.release>=dsge.release)){dsge=x;renderDsge();}}).catch(()=>{});
  }
  window.addEventListener('mme-lang-change',()=>renderDsge());
  window.addEventListener('mme-usa-refresh',fetchDsge);
  renderDsge();
  fetchDsge();

  const models={gdpnow:document.getElementById('model-gdpnow'),frbus:document.getElementById('model-frbus'),dsge:document.getElementById('model-dsge')};
  function showModel(key,changeURL){
    const active=Object.hasOwn(models,key)?key:'';
    tiles.hidden=!!active;
    document.getElementById('models-heading').hidden=!!active;   // dentro de un modelo sobra el título de la sección
    Object.entries(models).forEach(([id,el])=>{el.hidden=id!==active;});
    if(changeURL){
      const nextHash=active?'#'+active:'#modelos';
      try{history.pushState(null,'',nextHash);}catch(err){location.hash=nextHash;}
    }
    if(active||changeURL)window.scrollTo({top:0,behavior:'auto'});
  }
  host.querySelectorAll('[data-open-model]').forEach(b=>b.addEventListener('click',()=>showModel(b.dataset.openModel,true)));
  host.querySelectorAll('[data-close-model]').forEach(b=>b.addEventListener('click',()=>showModel('',true)));
  window.addEventListener('popstate',()=>showModel(location.hash.slice(1),false));
  window.addEventListener('hashchange',()=>showModel(location.hash.slice(1),false));
  showModel(location.hash.slice(1),false);

  const inline=document.getElementById('gdpnow-tracking-data');let data;try{data=JSON.parse(inline.textContent);}catch(err){return;}
  const categories=[
    ['consumption','Consumo privado','Consumer spending','#1168e8'],
    ['business','Inversión no residencial','Nonresidential investment','#49a5a6'],
    ['residential','Inversión residencial','Residential investment','#f8cd51'],
    ['inventories','Variación de existencias','Change in inventories','#5bbecc'],
    ['net_exports','Exportaciones netas','Net exports','#d87600'],
    ['government','Gasto público','Government spending','#a63a83']
  ];
  const labels=[
    ['Consumo privado','Personal consumption',0],['Bienes','Goods',1],['Servicios','Services',1],
    ['Inversión privada bruta','Gross private domestic investment',0],['Inversión fija','Fixed investment',1],['Inversión no residencial','Nonresidential investment',2],['Equipos','Equipment',3],['Propiedad intelectual','Intellectual property products',3],['Estructuras','Structures',3],['Inversión residencial','Residential investment',2],
    ['Gasto público','Government expenditure',0],['Gobierno federal','Federal government',1],['Gobiernos estatales y locales','State and local governments',1],
    ['Importaciones','Imports',0],['Bienes','Goods',1],['Servicios','Services',1],['Exportaciones','Exports',0],['Bienes','Goods',1],['Servicios','Services',1]
  ];
  const selector=document.getElementById('gdp-component-date');
  function drawBreakdown(){
    const es=getLang()!=='en',b=data.breakdown||{},dates=data.component_dates||[],obs=new Map((data.observations||[]).map(p=>[p.date,p.value]));
    const available=dates.filter(d=>categories.every(c=>typeof (b[c[0]]||{})[d]==='number')&&obs.has(d));
    if(!available.length)return;
    const legend=categories.map(c=>`<span><i style="background:${c[3]}"></i>${c[es?1:2]}</span>`).join('')+`<span><i style="background:#001391;height:3px"></i>${es?'GDPNow':'GDPNow forecast'}</span>`;
    host.querySelectorAll('.gdp-breakdown-legend').forEach(el=>{el.innerHTML=legend;});
    function chart(target,change){
      const ds=change?available.slice(1):available;
      const rows=ds.map((d,i)=>{const prev=change?available[i]:null;return {date:d,values:categories.map(c=>b[c[0]][d]-(prev?b[c[0]][prev]:0)),line:obs.get(d)-(prev?obs.get(prev):0)};});
      if(!rows.length){document.getElementById(target).textContent=es?'No hay revisiones disponibles.':'No revisions available.';return;}
      let low=Math.min(0,...rows.map(r=>r.values.filter(v=>v<0).reduce((a,v)=>a+v,0)),...rows.map(r=>r.line));
      let high=Math.max(0,...rows.map(r=>r.values.filter(v=>v>0).reduce((a,v)=>a+v,0)),...rows.map(r=>r.line));
      const pad=Math.max(.05,(high-low)*.12);low-=pad;high+=pad;const Y=v=>250-(v-low)/(high-low)*200;
      const left=58,right=795,w=(right-left)/rows.length,fmt=v=>v.toLocaleString(es?'es-ES':'en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
      const grid=Array.from({length:5},(_,i)=>{const v=low+(high-low)*i/4,y=Y(v);return `<line x1="${left}" x2="${right}" y1="${y}" y2="${y}" stroke="#e2e6ea"/><text x="50" y="${y+4}" text-anchor="end">${fmt(v)}</text>`;}).join('');
      const bars=rows.map((r,i)=>{let pos=0,neg=0,x=left+i*w+w*.2;return r.values.map((v,j)=>{const a=v>=0?pos:neg,z=a+v;if(v>=0)pos=z;else neg=z;const y=Math.min(Y(a),Y(z)),h=Math.abs(Y(a)-Y(z));return `<rect x="${x}" y="${y}" width="${w*.6}" height="${h}" fill="${categories[j][3]}"><title>${r.date} · ${categories[j][es?1:2]}: ${fmt(v)} pp</title></rect>`;}).join('');}).join('');
      const line=rows.map((r,i)=>`${i?'L':'M'}${left+i*w+w/2},${Y(r.line)}`).join(' ');
      const dots=rows.map((r,i)=>`<circle cx="${left+i*w+w/2}" cy="${Y(r.line)}" r="3" fill="#001391"><title>${r.date} · GDPNow: ${fmt(r.line)} ${change?'pp':'%'}</title></circle>`).join('');
      const ticks=rows.map((r,i)=>`<text x="${left+i*w+w/2}" y="274" text-anchor="middle">${r.date.slice(5)}</text>`).join('');
      document.getElementById(target).innerHTML=`<svg viewBox="0 0 820 290" style="width:100%;height:auto" role="img" aria-label="${es?'Contribuciones de los componentes':'Component contributions'}"><g fill="#526079" font-family="system-ui,sans-serif" font-size="11">${grid}${ticks}</g><line x1="${left}" x2="${right}" y1="${Y(0)}" y2="${Y(0)}" stroke="#adb8c2"/>${bars}<path d="${line}" fill="none" stroke="#001391" stroke-width="2.5"/>${dots}</svg>`;
    }
    chart('gdp-breakdown-chart',false);chart('gdp-breakdown-change',true);
  }
  function drawGrowth(date,es){
    const chosen=[1,4,6,10,11,17,14],fmt=v=>v.toLocaleString(es?'es-ES':'en-US',{minimumFractionDigits:1,maximumFractionDigits:1});
    const rows=chosen.map(id=>{const c=(data.components||[]).find(item=>item.id===id);return c&&typeof c.growth[date]==='number'?{label:labels[id-1][es?0:1],v:c.growth[date]}:null;}).filter(Boolean);
    const target=document.getElementById('gdp-growth-chart');document.getElementById('gdp-growth-date').textContent=(es?'Fecha: ':'Date: ')+date;
    if(!rows.length){target.textContent=es?'Sin datos para esta fecha.':'No data for this date.';return;}
    const lo=Math.min(0,...rows.map(r=>r.v)),hi=Math.max(0,...rows.map(r=>r.v)),pad=Math.max(.5,(hi-lo)*.1),low=lo-pad,high=hi+pad;
    const x=v=>245+(v-low)/(high-low)*500,zero=x(0),height=rows.length*40+55;
    const bars=rows.map((r,i)=>{const y=20+i*40,end=x(r.v),left=Math.min(zero,end),width=Math.abs(end-zero),labelX=r.v>=0?end+6:end-6;return `<text x="234" y="${y+15}" text-anchor="end">${r.label}</text><rect x="${left}" y="${y}" width="${width}" height="20" fill="${r.v<0?'#d87600':'#1168e8'}"><title>${r.label}: ${fmt(r.v)} %</title></rect><text x="${labelX}" y="${y+15}" text-anchor="${r.v<0?'end':'start'}">${fmt(r.v)}%</text>`;}).join('');
    target.innerHTML=`<svg viewBox="0 0 820 ${height}" style="width:100%;height:auto" role="img" aria-label="${es?'Crecimiento de los componentes':'Component growth'}"><g fill="#526079" font-family="system-ui,sans-serif" font-size="12"><line x1="${zero}" x2="${zero}" y1="10" y2="${height-30}" stroke="#8a9bae"/>${bars}</g></svg>`;
  }
  function drawComponents(){
    const es=getLang()!=='en',dates=data.component_dates||[],prevSelected=selector.value;
    selector.innerHTML=dates.slice().reverse().map(d=>`<option value="${d}">${d}</option>`).join('');
    if(dates.includes(prevSelected))selector.value=prevSelected;
    const date=selector.value,fmt=v=>typeof v==='number'?v.toLocaleString(es?'es-ES':'en-US',{minimumFractionDigits:2,maximumFractionDigits:2}):'—';
    document.getElementById('gdp-component-body').innerHTML=(data.components||[]).map(c=>{const lbl=labels[c.id-1];if(!lbl)return '';return `<tr><td style="padding-left:${12+lbl[2]*18}px">${lbl[es?0:1]}</td><td>${fmt(c.growth[date])}${typeof c.growth[date]==='number'?' %':''}</td><td>${fmt(c.contribution[date])}${typeof c.contribution[date]==='number'?' pp':''}</td></tr>`;}).join('');
    drawGrowth(date,es);
  }
  function drawTracking(){
    const es=getLang()!=='en',chart=document.getElementById('gdp-tracking-chart'),note=document.getElementById('gdp-tracking-note'),points=data.observations||[];if(!points.length)return;
    const min=Math.min(...points.map(p=>p.value)),max=Math.max(...points.map(p=>p.value)),pad=Math.max(.15,(max-min)*.25),low=min-pad,high=max+pad;
    const start=Date.parse(points[0].date+'T00:00:00Z'),end=Date.parse(points[points.length-1].date+'T00:00:00Z');
    const x=p=>58+(Date.parse(p.date+'T00:00:00Z')-start)/Math.max(end-start,1)*720,y=p=>205-(p.value-low)/(high-low)*170;
    const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const grid=Array.from({length:5},(_,i)=>{const v=low+(high-low)*i/4,yy=205-(v-low)/(high-low)*170;return `<line x1="58" x2="778" y1="${yy}" y2="${yy}" stroke="#e2e6ea"/><text x="48" y="${yy+4}" text-anchor="end">${v.toFixed(1)}%</text>`;}).join('');
    const path=points.map((p,i)=>`${i?'L':'M'}${x(p).toFixed(1)},${y(p).toFixed(1)}`).join(' ');
    const dots=points.map(p=>`<circle cx="${x(p)}" cy="${y(p)}" r="5" fill="#1168e8"><title>${esc(p.date)} · ${p.value.toFixed(2)}% · ${esc(p.release)}</title></circle>`).join('');
    const ticks=[points[0],points[points.length-1]].map(p=>`<text x="${x(p)}" y="228" text-anchor="middle">${p.date}</text>`).join('');
    chart.innerHTML=`<svg viewBox="0 0 820 250" style="width:100%;height:auto" role="img" aria-label="${es?'Evolución del crecimiento estimado del PIB':'Evolution of estimated GDP growth'}"><g fill="#526079" font-family="system-ui,sans-serif" font-size="12">${grid}${ticks}</g><path d="${path}" fill="none" stroke="#1168e8" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>${dots}</svg>`;
    drawComponents();
    drawBreakdown();
    note.textContent=(es?'Trimestre: ':'Quarter: ')+data.quarter+' · '+(es?'última observación del libro: ':'latest workbook observation: ')+data.updated_at;
  }
  function fetchTracking(){
    if(location.protocol==='file:')return;
    fetch('gdpnow_tracking.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{if(d.quarter&&Array.isArray(d.observations)&&d.observations.length&&d.updated_at>=data.updated_at){data=d;drawTracking();}}).catch(()=>{});
  }
  selector.addEventListener('change',drawComponents);
  window.addEventListener('mme-lang-change',drawTracking);
  window.addEventListener('mme-usa-refresh',fetchTracking);
  drawTracking();
  fetchTracking();
})();
</script>"""

tpl = Path("template.html").read_text(encoding="utf-8")
if tpl.count("__DATA__") != 1:
    raise ValueError("The template must contain exactly one __DATA__ placeholder")
data = json.loads(Path("data.json").read_text(encoding="utf-8"))
forecast = Path("forecasts.json")
if forecast.exists():
    data["forecasts"] = json.loads(forecast.read_text(encoding="utf-8"))
encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
bigdata_file = Path("bigdata.json")
bigdata = json.loads(bigdata_file.read_text(encoding="utf-8")) if bigdata_file.exists() else {"series": []}
big_encoded = json.dumps(bigdata, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
page = tpl.replace("__DATA__", encoded).replace("__BIGDATA__", big_encoded)
Path("espana.html").write_text(page, encoding="utf-8")
Path("artifact.html").write_text(page, encoding="utf-8")

empty_data = json.dumps({"series": {}, "meta": {"refreshed": "", "n_series": 0}}, separators=(",", ":"))
turkey = tpl.replace("__DATA__", empty_data).replace("__BIGDATA__", '{"series":[]}')
turkey = turkey.replace('<html lang="es">', '<html lang="es" data-monitor="turkey">', 1)
turkey = turkey.replace('<title>BBVA Research Monitor Macro España</title>',
                        '<title>BBVA Research Monitor Macro Turquía</title>', 1)
turkey = turkey.replace('<h1>BBVA Research Monitor Macro España</h1>',
                        '<h1>BBVA Research Monitor Macro Turquía</h1>', 1)
turkey = re.sub(r'<p class="lede">[^<]*</p>',
                '<p class="lede">Indicadores macroeconómicos y financieros de Turquía.</p>', turkey, count=1)
Path("turquia.html").write_text(turkey, encoding="utf-8")

frbus_file = Path("frbus_resultados.json")
gdpnow_file = Path("gdpnow.json")
tracking_file = Path("gdpnow_tracking.json")
if frbus_file.exists() and gdpnow_file.exists() and tracking_file.exists():
    frbus_raw = json.dumps(json.loads(frbus_file.read_text(encoding="utf-8")), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    tracking_raw = json.dumps(json.loads(tracking_file.read_text(encoding="utf-8")), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    gdp_raw = json.loads(gdpnow_file.read_text(encoding="utf-8"))
    dsge_file = Path("dsge_frbny.json")
    dsge_raw = (json.dumps(json.loads(dsge_file.read_text(encoding="utf-8")), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
                if dsge_file.exists() else "null")
    dsge_irf_file = Path("dsge_irf.json")
    dsge_irf_raw = (json.dumps(json.loads(dsge_irf_file.read_text(encoding="utf-8")), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
                    if dsge_irf_file.exists() else "null")
    gdp_snap = json.dumps({
        "value": gdp_raw.get("value"),
        "quarter": gdp_raw.get("quarter"),
        "updated_at": gdp_raw.get("updated_at"),
    }, ensure_ascii=False, separators=(",", ":"))
    usa = tpl.replace("__DATA__", empty_data).replace("__BIGDATA__", '{"series":[]}')
    usa = usa.replace('<html lang="es">', '<html lang="es" data-monitor="usa">', 1)
    usa = usa.replace('<title>BBVA Research Monitor Macro España</title>',
                      '<title>BBVA Research Monitor Macro Estados Unidos</title>', 1)
    usa = usa.replace('<h1>BBVA Research Monitor Macro España</h1>',
                      '<h1>BBVA Research Monitor Macro Estados Unidos</h1>', 1)
    usa = re.sub(r'<p class="lede">[^<]*</p>',
                 '<p class="lede">Indicadores macroeconómicos y modelos de seguimiento y simulación de Estados Unidos.</p>', usa, count=1)
    usa = usa.replace('</head>', USA_MODELS_STYLE + '</head>', 1)
    usa = usa.replace('<main><div class="wrap" id="panel" role="tabpanel"></div></main>',
                      '<main><div class=\"wrap\" id=\"panel\" role=\"tabpanel\"></div></main>\n' + USA_MODELS_HTML, 1)
    scripts = (USA_MODELS_SCRIPTS
               .replace("__FRBUS__", frbus_raw)
               .replace("__DSGE_FRBNY__", dsge_raw)
               .replace("__DSGE_IRF__", dsge_irf_raw)
               .replace("__GDPNOW_TRACKING__", tracking_raw)
               .replace("__GDPNOW_SNAPSHOT__", gdp_snap))
    usa = usa.replace('</body></html>', scripts + '\n</body></html>', 1)
    Path("usa.html").write_text(usa, encoding="utf-8")

print("espana.html, artifact.html, turquia.html and usa.html regenerated")
