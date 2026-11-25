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
<div class="sechead"><h2 data-es="Modelos de seguimiento y simulación" data-en="Tracking and simulation models">Modelos de seguimiento y simulación</h2></div>
<div class="cards" id="model-tiles"><button type="button" class="card model-tile" data-open-model="gdpnow" aria-controls="model-gdpnow"><span class="badge">FEDERAL RESERVE BANK OF ATLANTA</span><h2>GDPNow</h2><p class="note" data-es="Estimación del crecimiento del PIB real." data-en="Real GDP growth estimate.">Estimación del crecimiento del PIB real.</p><span class="model-action" data-es="Abrir modelo →" data-en="Open model →">Abrir modelo →</span></button><button type="button" class="card model-tile" data-open-model="frbus" aria-controls="model-frbus"><span class="badge">FEDERAL RESERVE BOARD</span><h2>FRB/US</h2><p class="note" data-es="Comparar escenarios macroeconómicos precalculados." data-en="Compare precomputed macroeconomic scenarios.">Comparar escenarios macroeconómicos precalculados.</p><span class="model-action" data-es="Abrir modelo →" data-en="Open model →">Abrir modelo →</span></button></div>
<section class="model-detail" id="model-gdpnow" hidden><button type="button" class="model-back" data-close-model data-es="← Volver a modelos" data-en="← Back to models">← Volver a modelos</button><article class="card gdp-detail"><span class="badge">FEDERAL RESERVE BANK OF ATLANTA</span><h2>GDPNow</h2><p class="note" data-es="Estimación del crecimiento trimestral anualizado del PIB real." data-en="Model estimate of annualized quarterly real GDP growth.">Estimación del crecimiento trimestral anualizado del PIB real.</p><div class="number" id="value">—</div><div class="date" id="period"></div><p class="note" id="gdp-stamp"></p><p class="note" data-es="Estimación mecánica del modelo; no es una previsión oficial del FOMC." data-en="A model estimate, not an official FOMC forecast.">Estimación mecánica del modelo; no es una previsión oficial del FOMC.</p><a href="https://www.atlantafed.org/research-and-data/data/gdpnow" target="_blank" rel="noopener" data-es="Fuente y metodología ↗" data-en="Source and methodology ↗">Fuente y metodología ↗</a><p><button type="button" class="model-back" onclick="document.getElementById('gdp-breakdown-chart').scrollIntoView({behavior:'smooth',block:'center'})" data-es="Ver gráficos de componentes ↓" data-en="View component charts ↓">Ver gráficos de componentes ↓</button></p></article><div class="gdp-gallery"><article class="card" style="margin-top:18px"><h2 data-es="Evolución de la estimación" data-en="Estimate over time">Evolución de la estimación</h2><p class="note" data-es="Crecimiento trimestral anualizado del PIB real. Sitúa el cursor sobre cada punto para ver la fecha y la publicación asociada." data-en="Annualized quarterly real GDP growth. Hover over a point to see its date and associated release.">Crecimiento trimestral anualizado del PIB real. Sitúa el cursor sobre cada punto para ver la fecha y la publicación asociada.</p><p class="note" id="gdp-tracking-note"></p><div id="gdp-tracking-chart" style="width:100%"></div><p class="note">Federal Reserve Bank of Atlanta · <a href="https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/research-and-data/data/gdpnow/GDPTrackingModelDataAndForecasts.xlsx" target="_blank" rel="noopener" data-es="Libro oficial de datos ↗" data-en="Official data workbook ↗">Libro oficial de datos ↗</a></p></article><article class="card" style="margin-top:18px"><h2 data-es="Contribuciones de los componentes al crecimiento del PIB" data-en="Component contributions to GDP growth">Contribuciones de los componentes al crecimiento del PIB</h2><p class="note" data-es="Cada barra muestra las aportaciones al crecimiento trimestral anualizado. La línea muestra la estimación GDPNow." data-en="Each bar shows contributions to annualized quarterly growth. The line shows the GDPNow estimate.">Cada barra muestra las aportaciones al crecimiento trimestral anualizado. La línea muestra la estimación GDPNow.</p><div class="gdp-breakdown-legend"></div><div id="gdp-breakdown-chart"></div><p class="note" data-es="Barras: puntos porcentuales. Línea: crecimiento en %. Fuente: Fed de Atlanta." data-en="Bars: percentage points. Line: growth in %. Source: Atlanta Fed.">Barras: puntos porcentuales. Línea: crecimiento en %. Fuente: Fed de Atlanta.</p></article><article class="card" style="margin-top:18px"><h2 data-es="Revisiones de las contribuciones" data-en="Changes in component contributions">Revisiones de las contribuciones</h2><p class="note" data-es="Variación entre cada publicación y la anterior. La línea representa la revisión total de GDPNow." data-en="Change between each release and the previous one. The line shows the total revision to GDPNow.">Variación entre cada publicación y la anterior. La línea representa la revisión total de GDPNow.</p><div class="gdp-breakdown-legend"></div><div id="gdp-breakdown-change"></div><p class="note" data-es="Revisiones en puntos porcentuales. Fuente: Fed de Atlanta." data-en="Revisions in percentage points. Source: Atlanta Fed.">Revisiones en puntos porcentuales. Fuente: Fed de Atlanta.</p></article><article class="card"><h2 data-es="Crecimiento de los componentes" data-en="Component growth">Crecimiento de los componentes</h2><p class="note" data-es="Crecimiento trimestral anualizado de los componentes principales. La fecha seleccionada se cambia en la tabla inferior." data-en="Annualized quarterly growth of main components. Change the selected date in the table below.">Crecimiento trimestral anualizado de los componentes principales. La fecha seleccionada se cambia en la tabla inferior.</p><p class="note" id="gdp-growth-date"></p><div id="gdp-growth-chart"></div><p class="note" data-es="Porcentaje trimestral anualizado. Fuente: Fed de Atlanta." data-en="Annualized quarterly percent. Source: Atlanta Fed.">Porcentaje trimestral anualizado. Fuente: Fed de Atlanta.</p></article></div><article class="card gdp-components" style="margin-top:18px"><h2 data-es="Componentes del PIB" data-en="GDP components">Componentes del PIB</h2><p class="note" data-es="Estimaciones del trimestre. Selecciona una fecha de publicación para consultar los componentes." data-en="Quarterly estimates. Select a release date to inspect the components.">Estimaciones del trimestre. Selecciona una fecha de publicación para consultar los componentes.</p><label for="gdp-component-date" data-es="Fecha de la estimación" data-en="Estimate date">Fecha de la estimación</label> <select id="gdp-component-date"></select><div style="overflow-x:auto;margin-top:14px"><table style="width:100%;border-collapse:collapse;text-align:left" class="gdp-component-table"><thead><tr><th data-es="Componente" data-en="Component">Componente</th><th data-es="Crecimiento anualizado" data-en="Annualized growth">Crecimiento anualizado</th><th data-es="Contribución al PIB" data-en="Contribution to GDP">Contribución al PIB</th></tr></thead><tbody id="gdp-component-body"></tbody></table></div><p class="note" data-es="Crecimiento en % intertrimestral anualizado; contribuciones en puntos porcentuales (pp). Las filas con sangría forman parte de los agregados superiores y no deben sumarse de nuevo. La inversión privada incluye existencias; las importaciones restan al PIB." data-en="Growth is annualized quarter-on-quarter, in %; contributions are in percentage points (pp). Indented rows are included in their parent aggregates and should not be added again. Private investment includes inventories; imports subtract from GDP.">Crecimiento en % intertrimestral anualizado; contribuciones en puntos porcentuales (pp). Las filas con sangría forman parte de los agregados superiores y no deben sumarse de nuevo. La inversión privada incluye existencias; las importaciones restan al PIB.</p><p class="note">Fuente / Source: Federal Reserve Bank of Atlanta · GDPNow</p></article></section>
<section class="sim-section" id="model-frbus" aria-label="FRB/US" hidden><button type="button" class="model-back" data-close-model data-es="← Volver a modelos" data-en="← Back to models">← Volver a modelos</button><h2 data-es="FRB/US: escenarios ilustrativos" data-en="FRB/US: illustrative scenarios">FRB/US: escenarios ilustrativos</h2><p class="note" data-es="Simulaciones calculadas con el modelo FRB/US y la trayectoria pública LONGBASE; 2040T1–2045T4. No son previsiones oficiales de la Reserva Federal. Los shocks de consumo y vivienda modifican residuos de ecuaciones. El shock de tipos durante cuatro trimestres se aplica repetidamente a la ecuación de política: no fija la trayectoria del tipo." data-en="Simulations computed with FRB/US and the public LONGBASE baseline; 2040Q1–2045Q4. These are not official Federal Reserve forecasts. Consumption and housing shocks change equation residuals. The four-quarter rate shock is repeatedly applied to the policy equation; it does not fix the path of the rate.">Simulaciones calculadas con el modelo FRB/US y la trayectoria pública LONGBASE; 2040T1–2045T4. No son previsiones oficiales de la Reserva Federal. Los shocks de consumo y vivienda modifican residuos de ecuaciones. El shock de tipos durante cuatro trimestres se aplica repetidamente a la ecuación de política: no fija la trayectoria del tipo.</p><div class="sim-controls"><h3 data-es="Seleccionar escenarios" data-en="Select scenarios">Seleccionar escenarios</h3><div class="scenario-list" id="scenario-list"></div><div class="sim-switch" role="group" aria-label="Visualización / Display"><button type="button" data-sim-mode="levels" aria-pressed="true" data-es="Trayectorias" data-en="Paths">Trayectorias</button><button type="button" data-sim-mode="delta" aria-pressed="false" data-es="Diferencia respecto a la base" data-en="Difference from baseline">Diferencia respecto a la base</button></div></div><div id="sim-legend" class="sim-legend"></div><div class="sim-grid" id="sim-grid"></div><p class="note" data-es="Datos precalculados en el Mac del usuario. Cambiar la selección no ejecuta de nuevo el modelo. Fuente: Federal Reserve Board, modelo FRB/US; cálculos de escenarios propios." data-en="Precomputed on the user's Mac. Changing the selection does not rerun the model. Source: Federal Reserve Board, FRB/US model; scenario calculations by the user.">Datos precalculados en el Mac del usuario. Cambiar la selección no ejecuta de nuevo el modelo. Fuente: Federal Reserve Board, modelo FRB/US; cálculos de escenarios propios.</p></section>
</section>"""

USA_MODELS_SCRIPTS = """<script id="frbus-embedded" type="application/json">__FRBUS__</script>
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
  const models={gdpnow:document.getElementById('model-gdpnow'),frbus:document.getElementById('model-frbus')};
  function showModel(key,changeURL){
    const active=Object.hasOwn(models,key)?key:'';
    tiles.hidden=!!active;
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
               .replace("__GDPNOW_TRACKING__", tracking_raw)
               .replace("__GDPNOW_SNAPSHOT__", gdp_snap))
    usa = usa.replace('</body></html>', scripts + '\n</body></html>', 1)
    Path("usa.html").write_text(usa, encoding="utf-8")

print("espana.html, artifact.html, turquia.html and usa.html regenerated")
