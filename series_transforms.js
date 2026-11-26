/* Resolve published counterparts before calculating on compatible observations. */
const SERIES_TRANSFORMS = (() => {
  const kinds={
    original:['Original','Raw'],
    mom:['Variación mensual','Month-on-month change'], qoq:['Variación trimestral','Quarter-on-quarter change'],
    yoy:['Variación interanual','Year-on-year change'],
    b100:['Base 100','Base 100'], z:['Estandarizado','Standardised']
  };
  const adjustments={raw:['Sin desestacionalizar','Not seasonally adjusted'],
    adjusted:['Desestacionalizada','Seasonally adjusted']};
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
  function documentedAdjustment(code,series){
    const original=series.originalText||series;
    const text=[series.adjustment,original.label,original.original_name,series.transform].filter(Boolean).join(' ');
    if(/(?:^|[_ .-])(?:nsa|raw)(?:[_ .-]|$)/i.test(code)) return 'raw';
    if(/(?:^|[_ .-])(?:sa|sca|cvec)(?:[_ .-]|$)/i.test(code)) return 'adjusted';
    if(/sin (?:ajustar|ajuste estacional|desestacionalizar)|no ajustad|unadjusted|not seasonally adjusted|without seasonal|no seasonal adjustment/i.test(text)) return 'raw';
    if(/\bcvec\b|desestacionaliz|ajustad[oa]s? (?:estacionalmente|de estacionalidad)|corregid[oa]s? de (?:efectos estacionales|estacionalidad)|seasonally (?:and calendar[- ]?)?adjusted|adjusted for seasonality/i.test(text)) return 'adjusted';
    return '';
  }
  function profile(id,s,scope){
    const code=s.code||id, unit=s.unit||'';
    const block=s.family||s.block;
    const adjustment=documentedAdjustment(code,s);
    const meta={family:id,kind:'level',adjustment:adjustment||'raw',method:'',aggregate:'',canGrow:false,hasMethod:false};
    const shape=(fields)=>({...meta,...fields});
    if(scope==='big'){
      const parts=s.label.split(' · '), price=parts.pop()?.toLowerCase();
      const metric=normalize(parts.pop());
      const yoy28=s.source?.includes('Datos_informe.csv')&&price==='real';
      return shape({family:'big:'+s.group+':'+(s.area||'')+':'+metric,price,kind:yoy28?'yoy':'rate',hasMethod:yoy28});
    }
    let m;
    if(id==='ipi_yoy') return shape({...INE_GENERAL_YOY,hasMethod:true});
    if((block==='INDUSTRIAL_PRODUCTION'||block==='IPI')&&(m=code.match(/^IPI_(.+?)_(CVEC_INE|CVEC_BBVA|RAW)(?:_(AA|MM))?$/))){
      return shape({family:'IPI:'+m[1],method:{CVEC_INE:'ine',CVEC_BBVA:'bbva',RAW:'raw'}[m[2]],
        adjustment:m[2]==='RAW'?'raw':'adjusted',kind:({AA:'yoy',MM:'mom'})[m[3]]||'level',
        aggregate:'mean',canGrow:!m[3],hasMethod:true});
    }
    if((block==='LARGE_ENTERPRISES'||block==='GGEE')&&(m=code.match(/^(.+)_(NIV|TRIM|AA|MM)$/))){
      const kind=({AA:'yoy',MM:'mom'})[m[2]]||'level';
      return shape({family:m[1],kind,method:adjustment==='adjusted'?'bbva':'',aggregate:'mean',canGrow:kind==='level',hasMethod:true});
    }
    const flow=block==='TRADE_BALANCE'||block==='BAL_COM';
    if((block==='SERVICES_ACTIVITY'||block==='IASS'||flow)&&(m=code.match(/^(.+)_(CVEC|RAW|BRUTO)$/))){
      return shape({family:m[1],adjustment:m[2]==='CVEC'?'adjusted':'raw',
        aggregate:flow?'sum':'mean',canGrow:!code.startsWith('BC_SALDO'),hasMethod:true});
    }
    if(id.startsWith('drive_us_')){
      const kind=/% y\/y|% a\/a|year-on-year/i.test(unit)?'yoy':/% q\/q|% t\/t|quarter-on-quarter/i.test(unit)?'qoq':/% m\/m|month-on-month/i.test(unit)?'mom':'level';
      const canGrow=kind==='level'&&(/index|usd|dollar|billion|million|thousand|people|person|level|índice|miles|millones/i.test(unit))&&!/balance|saldo|rate|spread|%/i.test(unit);
      return shape({kind,aggregate:/index|índice/i.test(unit)?'mean':'',canGrow,hasMethod:Boolean(adjustment||s.transform)});
    }
    if(id.startsWith('drive_tr_')){
      const isGDP=/^TR_Q_(EXP|PROD)_/.test(code);
      const indexed=/^Index \(base/.test(unit)&&!code.includes('CONFIDENCE');
      return shape({family:isGDP?code.replace(/_(RAW|SCA|SA)_/,'_'):id,
        aggregate:indexed?'mean':'',canGrow:isGDP&&!/_(S|TAXES_SUBSIDIES)$/.test(code)||indexed||/People/.test(unit),hasMethod:Boolean(adjustment)});
    }
    if(id.startsWith('public_tr_')){
      if(/^(TR_CPI_|TR_TREND_)/.test(code)){
        const key=code.replace(/^TR_(CPI|TREND)_/,'').replace(/^CPI$/,'HEADLINE');
        return shape({family:'TR:CPI:'+key,kind:code.startsWith('TR_CPI_')?'yoy':'trend',hasMethod:true});
      }
      if(/^(TR_BOP_|TR_TRADE_)/.test(code)){
        return shape({family:code.replace(/_12M$/,''),kind:code.endsWith('_12M')?'sum12':'level',aggregate:'sum',
          canGrow:!/(BOP_|TRADE_BALANCE)/.test(code),hasMethod:true});
      }
      return shape({hasMethod:Boolean(s.transform)});
    }
    const documented=base[id]||{};
    const kind=documented.kind||(/% a\/a|y\/y|year-on-year/i.test(unit)||/^(yoy|sum12yoy|qavg_yoy)$/.test(s.transform)?'yoy':
      /sum12|suma móvil de 12 meses/.test(s.transform)?'sum12':unit==='% PIB'?'gdp':
      /^Month-on-month/.test(unit)?'mom':'level');
    const monthlyFlow=monthlyFlows.has(id);
    const measure=['miles','€/m²','M€','mm€','miles €','índice'].includes(unit);
    return shape({...documented,kind,canGrow:kind==='level'&&measure&&!monthlyFlow,
      aggregate:monthlyFlow?'sum':unit==='índice'?'mean':'',hasMethod:Boolean(s.transform||kind!=='level'||adjustment||['ESI','PMI'].includes(block))});
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
  function growth(data,freq,kind){
    const obs=new Map(data.filter(numeric).map(p=>[seriesPeriod(p[0],freq),p]));
    const lag=kind==='yoy'?({M:12,Q:4,W:364})[freq]:freq==='W'?7:1;
    return data.filter(numeric).flatMap(([day,v,flag])=>{
      const previous=obs.get(kind==='yoy'&&freq==='D'?priorYear(day):seriesPeriod(day,freq)-lag);
      if(!previous||previous[1]<=0||v<0) return [];
      const value=100*(v/previous[1]-1);
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
  function adjustedRow(id,kind,cat,adjustment){
    const selected=cat.byId.get(id);
    if(!selected||!adjustment||selected.p.adjustment===adjustment) return selected;
    const equivalent=row=>row.series.freq===selected.series.freq&&row.p.kind===selected.p.kind;
    const sameMeasure=['original','b100','z'].includes(kind);
    const candidates=cat.byFamily.get(selected.p.family).filter(row=>row.p.adjustment===adjustment&&(!sameMeasure||equivalent(row)));
    // When starting from an unadjusted IPI, prefer the INE's own adjustment.
    const official=candidates.filter(row=>row.p.method==='ine');
    const choices=official.length?official:candidates;
    return choices.find(equivalent)||choices[0];
  }
  function resolve(id,kind,cat,start,end,en,baseDate,adjustment){
    const selected=cat.byId.get(id), row=adjustedRow(id,kind,cat,adjustment);
    const t=(es,english)=>en?english:es;
    const unavailable=reason=>({status:'unavailable',reason,baseSeries:row?.series});
    if(!selected) return unavailable(t('Sin datos de origen.','No source observations.'));
    if(!row) return unavailable(adjustment==='adjusted'
      ?t('Sin versión desestacionalizada comparable.','No comparable seasonally adjusted series.')
      :t('Sin versión sin desestacionalizar comparable.','No comparable unadjusted series.'));
    const {p,series:s}=row, family=cat.byFamily.get(p.family), big=cat.scope==='big';
    const stored=(variant,status='documented')=>({status,series:variant.series,percentScale:big,origin:variant.id});
    if(kind==='original') return stored(row,p.hasMethod?'documented':'original');
    const calc=(from,data,unit,freq,note)=>data.length?{
      status:'calculated',percentScale:false,origin:from.id,reason:note,
      series:{...from.series,unit,freq,data,label:from.series.label+' · '+names(kind,false)}
    }:unavailable(t('Faltan observaciones comparables para calcularla.','Comparable observations are missing.'));
    if(kind==='z'||kind==='b100'){
      const data=s.data.filter(o=>numeric(o)&&timestamp(o[0])>=start&&timestamp(o[0])<=end);
      if(kind==='b100'){
        const observation=baseDate?s.data.find(([day])=>day===baseDate):data[0];
        if(!observation||!(observation[1]>0)||!numeric(observation)) return unavailable(baseDate
          ?t('La fecha base debe tener una observación positiva.','The base date needs a positive observation.')
          :t('La primera observación visible debe ser positiva.','The first visible observation must be positive.'));
        const [date,base]=observation;
        const note=t(`Base 100 el ${date}.`,`Base 100 on ${date}.`);
        const result=calc(row,data.map(([day,value,flag])=>[day,100*(value/base),flag]).filter(numeric),'índice',s.freq,note);
        return result.series?{...result,baseDate:date,baseSeries:s,series:{...result.series,transform:note}}:result;
      }
      if(data.length<2) return unavailable(t('Se necesitan al menos dos observaciones visibles.','At least two visible observations are required.'));
      const mean=data.reduce((sum,o)=>sum+o[1],0)/data.length;
      const sd=Math.sqrt(data.reduce((sum,o)=>sum+(o[1]-mean)**2,0)/(data.length-1))||1;
      return calc(row,data.map(([d,v,f])=>[d,(v-mean)/sd,f]),'σ',s.freq,t('Media y desviación típica del periodo visible.','Mean and standard deviation over the visible period.'));
    }
    if(!['mom','qoq','yoy'].includes(kind)) return unavailable(t('Transformación no disponible.','Transformation unavailable.'));
    const variants=family.filter(v=>compatible(row,v)&&(!big||v.p.price===p.price));
    const desiredFreq=kind==='mom'?'M':kind==='qoq'?'Q':selected.series.freq;
    const matches=v=>v.p.kind===kind&&v.series.freq===desiredFreq;
    const candidate=matches(row)?row:variants.find(matches);
    if(candidate) return stored(candidate);

    const comparable=v=>v.p.kind==='level'&&v.p.canGrow;
    const native=variants.find(v=>comparable(v)&&v.series.freq===desiredFreq);
    const monthly=kind==='qoq'&&!native&&variants.find(v=>comparable(v)&&v.series.freq==='M'&&v.p.aggregate);
    const level=native||monthly;
    if(!level) return unavailable(t('No está disponible el nivel de origen compatible con esta operación.','A compatible underlying level is not available for this operation.'));
    const data=monthly?quarterly(level.series.data,level.p.aggregate):level.series.data;
    const unit='% '+({mom:'m/m',qoq:'t/t',yoy:'a/a'})[kind];
    const note=monthly
      ? (level.p.aggregate==='sum'?t('Suma de los tres meses de cada trimestre.','Sum of the three months in each quarter.'):t('Media de los tres meses de cada trimestre.','Average of the three months in each quarter.'))
      : t('Comparación con el periodo correspondiente, sin rellenar huecos.','Comparison with the corresponding period, with no gap filling.');
    return calc(level,growth(data,desiredFreq,kind),unit,desiredFreq,note);
  }
  return {names,kinds,adjustments,catalogue,resolve,adjustedRow};
})();
