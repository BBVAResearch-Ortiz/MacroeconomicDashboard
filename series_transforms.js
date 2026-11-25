/* Resolve published counterparts before calculating on compatible observations. */
const SERIES_TRANSFORMS = (() => {
  const kinds={
    original:['Como está guardada','As stored'], level:['Nivel','Level'],
    mom:['Variación mensual','Month-on-month change'], qoq:['Variación trimestral','Quarter-on-quarter change'],
    yoy:['Variación interanual','Year-on-year change'], pp:['Cambio en puntos','Change in points'],
    sum12:['Acumulado de 12 meses','12-month total'], gdp:['Porcentaje del PIB','Percent of GDP'],
    raw:['Sin ajustar','Unadjusted'], adjusted:['Ajuste estacional','Seasonally adjusted'],
    real:['Real','Real'], nominal:['Nominal','Nominal'],
    trend:['Tendencia de inflación (3 meses)','Inflation trend (3 months)'],
    yoy28:['Interanual de la media de 28 días','28-day average, year-on-year'],
    b100:['Base 100','Base 100'], z:['Estandarizado','Standardised']
  };
  const base={};
  function pair(family,series){
    for(const [id,kind] of Object.entries(series)) base[id]={family,kind};
  }
  pair('PIB real',{pib_qoq:'qoq',pib_yoy:'yoy'});
  for(const id of ['viv_tasado','ocup_epa','paro_reg']) pair(id,{[id]:'level',[id+'_yoy']:'yoy'});
  for(const id of ['viv_visados','viv_compraventas','viv_compr_reg','nop_viv','nop_cons','nop_snf']){
    pair(id,{[id]:'sum12',[id+'_yoy']:'yoy'});
  }
  pair('crédito OSR',{cred_saldo:'level',credito_osr:'yoy'});
  pair('depósitos OSR',{dep_saldo:'level',depositos_osr:'yoy'});
  pair('cuenta corriente',{cc_m:'level',cc_pib:'gdp'});
  pair('bienes y servicios',{bys_m:'level',bys_pib:'gdp'});
  pair('ingresos turismo',{tur_ing_m:'level',tur_ing_12m:'sum12'});
  const monthlyFlows=new Set(['cc_m','bys_m','tur_ing_m']);
  const INE_GENERAL_YOY={family:'IPI:GEN',method:'ine',adjustment:'adjusted',kind:'yoy',aggregate:'mean'};
  const normalize=s=>String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  function profile(id,s,scope){
    const code=s.code||id, block=s.family||s.block, unit=s.unit||'';
    const meta={family:id,kind:'level',adjustment:'',method:'',aggregate:'',flow:false,points:false,canGrow:false,hasMethod:false};
    const shape=(fields)=>({...meta,...fields});
    if(scope==='big'){
      const parts=s.label.split(' · '), price=parts.pop()?.toLowerCase();
      const metric=normalize(parts.pop());
      const yoy28=s.source?.includes('Datos_informe.csv')&&price==='real';
      return shape({family:'big:'+s.group+':'+(s.area||'')+':'+metric,price,kind:yoy28?'yoy':'rate',yoy28,points:true,hasMethod:yoy28});
    }
    let m;
    if(id==='ipi_yoy') return shape({...INE_GENERAL_YOY,hasMethod:true});
    if(block==='INDUSTRIAL_PRODUCTION'&&(m=code.match(/^IPI_(.+?)_(CVEC_INE|CVEC_BBVA|RAW)(?:_(AA|MM))?$/))){
      return shape({family:'IPI:'+m[1],method:{CVEC_INE:'ine',CVEC_BBVA:'bbva',RAW:'raw'}[m[2]],
        adjustment:m[2]==='RAW'?'raw':'adjusted',kind:({AA:'yoy',MM:'mom'})[m[3]]||'level',
        aggregate:'mean',canGrow:!m[3],hasMethod:true});
    }
    if(block==='LARGE_ENTERPRISES'&&(m=code.match(/^(.+)_(NIV|TRIM|AA|MM)$/))){
      const kind=({AA:'yoy',MM:'mom'})[m[2]]||'level';
      return shape({family:m[1],kind,adjustment:'adjusted',method:'bbva',aggregate:'mean',canGrow:kind==='level',hasMethod:true});
    }
    if((block==='SERVICES_ACTIVITY'||block==='TRADE_BALANCE')&&(m=code.match(/^(.+)_(CVEC|RAW|BRUTO)$/))){
      const flow=block==='TRADE_BALANCE';
      return shape({family:m[1],adjustment:m[2]==='CVEC'?'adjusted':'raw',flow,
        aggregate:flow?'sum':'mean',canGrow:!code.startsWith('BC_SALDO'),hasMethod:true});
    }
    if(id.startsWith('drive_tr_')){
      const adjustment=code.includes('_RAW_')?'raw':/_SC?A_/.test(code)?'adjusted':'';
      const isGDP=/^TR_Q_(EXP|PROD)_/.test(code), points=/Rate|%/.test(unit);
      const indexed=/^Index \(base/.test(unit)&&!code.includes('CONFIDENCE');
      return shape({family:isGDP?code.replace(/_(RAW|SCA)_/,'_'):id,adjustment,
        aggregate:indexed?'mean':'',points,canGrow:isGDP&&!/_(S|TAXES_SUBSIDIES)$/.test(code)||indexed||/People/.test(unit),hasMethod:Boolean(adjustment)});
    }
    if(id.startsWith('public_tr_')){
      if(/^(TR_CPI_|TR_TREND_)/.test(code)){
        const key=code.replace(/^TR_(CPI|TREND)_/,'').replace(/^CPI$/,'HEADLINE');
        return shape({family:'TR:CPI:'+key,kind:code.startsWith('TR_CPI_')?'yoy':'trend',hasMethod:true});
      }
      if(/^(TR_BOP_|TR_TRADE_)/.test(code)){
        return shape({family:code.replace(/_12M$/,''),kind:code.endsWith('_12M')?'sum12':'level',flow:true,aggregate:'sum',
          canGrow:!/(BOP_|TRADE_BALANCE)/.test(code),hasMethod:true});
      }
      return shape({points:unit==='%',hasMethod:Boolean(s.transform)});
    }
    const text=String(s.original_name||'').toLowerCase();
    const documented=base[id]||{};
    const kind=documented.kind||(/% a\/a|y\/y|year-on-year/i.test(unit)||/^(yoy|sum12yoy|qavg_yoy)$/.test(s.transform)?'yoy':
      /sum12|suma móvil de 12 meses/.test(s.transform)?'sum12':unit==='% PIB'?'gdp':
      /^Month-on-month/.test(unit)?'mom':'level');
    const adjustment=block==='ESI'||block==='PMI'||id==='afil_sa'?'adjusted':
      /\b(?:sin ajustar|no ajustad)/.test(text)?'raw':/desestacionaliz|ajustad[oa]s? de estacionalidad/.test(text)?'adjusted':'';
    const flow=monthlyFlows.has(id), points=/^(%|% PIB|pp|pb|saldo|Balance \(points\)|Diffusion index)$/.test(unit);
    const measure=['miles','€/m²','M€','mm€','miles €','índice'].includes(unit);
    return shape({...documented,kind,adjustment,flow,points,canGrow:kind==='level'&&measure&&!flow,
      aggregate:flow?'sum':unit==='índice'?'mean':'',hasMethod:Boolean(s.transform||kind!=='level'||adjustment||['ESI','PMI'].includes(block))});
  }
  const numeric=p=>Number.isFinite(p[1]);
  const timestamp=d=>Date.parse(d+'T00:00:00Z');
  const months=d=>+d.slice(0,4)*12+(+d.slice(5,7)-1);
  const monthDate=k=>String(Math.floor(k/12))+'-'+String(k%12+1).padStart(2,'0')+'-01';
  function seriesPeriod(d,freq){
    return freq==='M'?months(d):freq==='Q'?Math.floor(months(d)/3):Math.floor(timestamp(d)/864e5);
  }
  function priorYear(d){
    const prior=String(+d.slice(0,4)-1)+d.slice(4);
    const time=timestamp(prior);
    return Number.isFinite(time)&&new Date(time).toISOString().slice(0,10)===prior?time/864e5:NaN;
  }
  function difference(data,freq,kind,points,scale=1){
    const obs=new Map(data.filter(numeric).map(p=>[seriesPeriod(p[0],freq),p]));
    const lag=kind==='yoy'?({M:12,Q:4,W:364})[freq]:freq==='W'?7:1;
    return data.filter(numeric).flatMap(([day,v,flag])=>{
      const previous=obs.get(kind==='yoy'&&freq==='D'?priorYear(day):seriesPeriod(day,freq)-lag);
      if(!previous||!points&&(previous[1]<=0||v<0)) return [];
      const value=points?(v-previous[1])*scale:100*(v/previous[1]-1);
      return Number.isFinite(value)?[[day,value,flag||previous[2]||0]]:[];
    });
  }
  function quarterly(data,how){
    const byMonth=new Map(data.filter(numeric).map(p=>[months(p[0]),p]));
    return [...byMonth.keys()].filter(k=>k%3===0&&byMonth.has(k+1)&&byMonth.has(k+2)).map(k=>{
      const a=[byMonth.get(k),byMonth.get(k+1),byMonth.get(k+2)];
      return [monthDate(k),a.reduce((sum,p)=>sum+p[1],0)/(how==='mean'?3:1),a.some(p=>p[2])?1:0];
    });
  }
  function annualSum(data,freq){
    const count=freq==='M'?12:freq==='Q'?4:0;
    if(!count) return [];
    const obs=new Map(data.filter(numeric).map(p=>[seriesPeriod(p[0],freq),p]));
    return [...obs].flatMap(([period,p])=>{
      const window=Array.from({length:count},(_,i)=>obs.get(period-i));
      return window.every(Boolean)?[[p[0],window.reduce((sum,o)=>sum+o[1],0),window.some(o=>o[2])?1:0]]:[];
    });
  }
  function seasonal(data,freq){
    const period=freq==='M'?12:freq==='Q'?4:0;
    if(!period) return [];
    const obs=new Map(data.filter(numeric).map(p=>[seriesPeriod(p[0],freq),p]));
    const half=period/2, factors=Array.from({length:period},()=>[]);
    for(const [k,p] of obs){
      const window=Array.from({length:period+1},(_,i)=>obs.get(k-half+i));
      if(window.every(Boolean)){
        const trend=window.reduce((sum,o,i)=>sum+o[1]*(i===0||i===period?0.5:1),0)/period;
        factors[k%period].push(p[1]-trend);
      }
    }
    if(factors.some(a=>a.length<2)) return [];
    const means=factors.map(a=>a.reduce((sum,x)=>sum+x,0)/a.length);
    const center=means.reduce((sum,x)=>sum+x,0)/period;
    return [...obs].map(([k,p])=>[p[0],p[1]-means[k%period]+center,p[2]||0]);
  }
  const names=(kind,en)=>kinds[kind]?.[Number(en)]||kind;
  function catalogue(entries,scope){
    const byId=new Map(), byFamily=new Map();
    for(const [id,s] of entries){
      if(!Array.isArray(s.data)||!s.data.length) continue;
      const row={id,series:s,p:profile(id,s,scope)};
      byId.set(id,row);
      if(!byFamily.has(row.p.family)) byFamily.set(row.p.family,[]);
      byFamily.get(row.p.family).push(row);
    }
    return {byId,byFamily,scope};
  }
  function compatible(row,variant){
    return row.p.adjustment===variant.p.adjustment&&(!row.p.method||!variant.p.method||row.p.method===variant.p.method);
  }
  function resolve(id,kind,cat,start,end,en){
    const row=cat.byId.get(id);
    const t=(es,english)=>en?english:es;
    const unavailable=reason=>({status:'unavailable',reason});
    if(!row) return unavailable(t('Sin datos de origen.','No source observations.'));
    const {p,series:s}=row, family=cat.byFamily.get(p.family), big=cat.scope==='big';
    const stored=(variant,status='documented')=>({status,series:variant.series,percentScale:big,origin:variant.id});
    if(kind==='original') return stored(row,p.hasMethod?'documented':'original');
    const raw=family.filter(v=>compatible(row,v));
    const desiredFreq=kind==='mom'?'M':kind==='qoq'?'Q':s.freq;
    let candidate;
    if(kind==='adjusted'||kind==='raw'){
      candidate=family.find(v=>v.p.adjustment===kind&&v.p.kind===p.kind&&v.series.freq===s.freq&&compatible(row,v))
        ||family.find(v=>v.p.adjustment===kind&&v.p.kind===p.kind&&v.series.freq===s.freq);
    }else if(kind==='real'||kind==='nominal'){
      candidate=family.find(v=>v.p.price===kind&&v.series.freq===s.freq);
    }else if(kind==='yoy28'){
      candidate=family.find(v=>v.p.yoy28&&v.p.price===p.price);
    }else if(!['b100','z','pp'].includes(kind)){
      const matches=v=>v.p.kind===kind&&v.series.freq===desiredFreq&&(!big||v.p.price===p.price);
      candidate=matches(row)?row:raw.find(matches);
      if(!candidate&&kind==='level'&&s.transform==='sum12yoy'){
        candidate=raw.find(v=>v.p.kind==='sum12'&&v.series.freq===s.freq);
      }
    }
    if(candidate) return stored(candidate);
    const calc=(from,data,unit,freq,note)=>data.length?{
      status:'calculated',percentScale:false,origin:from.id,reason:note,
      series:{...from.series,unit,freq,data,label:from.series.label+' · '+names(kind,false)}
    }:unavailable(t('Faltan observaciones comparables para calcularla.','Comparable observations are missing.'));
    if(kind==='z'||kind==='b100'){
      const data=s.data.filter(o=>numeric(o)&&timestamp(o[0])>=start&&timestamp(o[0])<=end);
      if(kind==='b100'){
        const base=data[0]?.[1];
        if(!(base>0)) return unavailable(t('La primera observación visible debe ser positiva.','The first visible observation must be positive.'));
        return calc(row,data.map(([d,v,f])=>[d,100*v/base,f]),'índice',s.freq,t('Primera observación visible = 100.','First visible observation = 100.'));
      }
      if(data.length<2) return unavailable(t('Se necesitan al menos dos observaciones visibles.','At least two visible observations are required.'));
      const mean=data.reduce((sum,o)=>sum+o[1],0)/data.length;
      const sd=Math.sqrt(data.reduce((sum,o)=>sum+(o[1]-mean)**2,0)/(data.length-1))||1;
      return calc(row,data.map(([d,v,f])=>[d,(v-mean)/sd,f]),'σ',s.freq,t('Media y desviación típica del periodo visible.','Mean and standard deviation over the visible period.'));
    }
    if(kind==='adjusted'&&p.kind==='level'&&p.adjustment==='raw'){
      return calc(row,seasonal(s.data,s.freq),s.unit,s.freq,t('Ajuste estacional aproximado, sin corrección de calendario.','Approximate seasonal adjustment without calendar correction.'));
    }
    if(kind==='sum12'){
      const flow=raw.find(v=>v.p.kind==='level'&&v.p.flow&&v.series.freq===s.freq);
      if(flow) return calc(flow,annualSum(flow.series.data,s.freq),flow.series.unit,s.freq,t('Suma de periodos consecutivos.','Sum of consecutive periods.'));
    }
    if(['mom','qoq','yoy','pp'].includes(kind)){
      const comparable=v=>kind==='pp'?v.id===row.id&&(v.p.points||/^%/.test(v.series.unit)):
        v.p.kind==='level'&&v.p.canGrow;
      let level=raw.find(v=>comparable(v)&&v.series.freq===desiredFreq)
        ||raw.find(v=>kind==='yoy'&&p.kind==='yoy'&&v.p.kind==='sum12'&&v.series.freq===s.freq);
      let aggregated=false;
      if(!level&&kind==='qoq'){
        level=raw.find(v=>comparable(v)&&v.series.freq==='M'&&v.p.aggregate);
        aggregated=Boolean(level);
      }
      if(level){
        const l=level.series, data=aggregated?quarterly(l.data,level.p.aggregate):l.data;
        const pts=kind==='pp', scale=pts&&(big||l.unit==='Rate (fraction of 1)')?100:1;
        const unit=pts?(big||/^(%|Rate)/.test(l.unit)?'pp':l.unit):'% '+({mom:'m/m',qoq:'t/t',yoy:'a/a'})[kind];
        const note=aggregated
          ? (level.p.aggregate==='sum'?t('Suma de los tres meses de cada trimestre.','Sum of the three months in each quarter.'):t('Media de los tres meses de cada trimestre.','Average of the three months in each quarter.'))
          : t('Comparación con el periodo correspondiente, sin rellenar huecos.','Comparison with the corresponding period, with no gap filling.');
        return calc(level,difference(data,desiredFreq,kind,pts,scale),unit,desiredFreq,note);
      }
    }
    const missing=['raw','real','nominal','gdp','adjusted','trend','yoy28'].includes(kind)
      ? t('No hay una variante compatible ni los insumos necesarios para reproducirla.','No compatible variant or the necessary inputs to reproduce it.')
      : t('No está disponible el nivel de origen compatible con esta operación.','A compatible underlying level is not available for this operation.');
    return unavailable(missing);
  }
  return {names,kinds,catalogue,resolve};
})();
