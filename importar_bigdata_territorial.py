"""Importa tres libros territoriales a archivos por territorio y tipo."""
import sys,json,hashlib,math,re
from pathlib import Path
from datetime import date,datetime
import openpyxl
if len(sys.argv)!=4: raise SystemExit('Uso: python importar_bigdata_territorial.py ccaa.xlsx provincias.xlsx municipios.xlsx')
out=Path('bigdata_geo');out.mkdir(exist_ok=True);index={'groups':{}}
for fname,group in zip(sys.argv[1:],['CCAA','Provincial','Urbano']):
 ws=openpyxl.load_workbook(fname,read_only=True,data_only=True).worksheets[0];rows=ws.iter_rows(values_only=True);english=list(next(rows));spanish=list(next(rows));headers=list(next(rows));columns=[(i,str(spanish[i] or english[i] or headers[i]).strip()) for i in range(5,len(headers)) if headers[i] is not None];areas={};current=None;bucket={};seen=set()
 def flush():
  global bucket,current
  if current is None:return
  typ,code,name=current; token=hashlib.sha256((group+'|'+code+'|'+typ).encode()).hexdigest()[:20];folder=Path(group.lower())/typ.lower();(out/folder).mkdir(parents=True,exist_ok=True);filename=(folder/(token+'.json')).as_posix();series=[]
  for j,(col,lab) in enumerate(columns):
   values=bucket.get(j,{})
   if values:series.append({'id':'geo_'+token+'_'+str(j),'label':f'{group} · {name} · {lab} · {typ}','group':group,'unit':'valor original de la hoja','freq':'D','source':'BBVA Research','data':[[d,v,0] for d,v in sorted(values.items())]})
  (out/filename).write_text(json.dumps({'series':series},ensure_ascii=False,separators=(',',':')),encoding='utf8')
  item=areas.setdefault(code,{'id':code,'label':name,'files':[]});item['files'].append(filename);bucket={}
 for row in rows:
  if len(row)<5 or not row[1] or not row[2]:continue
  typ=str(row[0] or '').strip();code=str(row[1]).strip();name=str(row[4] or row[3] or code).strip()
  if typ not in ('Nominal','Real'):continue
  key=(typ,code,name)
  if key!=current:
   if key in seen: raise ValueError(f'Territorio no contiguo: {group} {code} {typ}')
   flush();seen.add(key);current=key
  d=row[2];day=d.strftime('%Y-%m-%d') if isinstance(d,(date,datetime)) else str(d).strip()[:10]
  if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):continue
  for j,(i,lab) in enumerate(columns):
   if i>=len(row) or row[i] is None:continue
   try:
    v=float(row[i].strip().replace(',','.')) if isinstance(row[i],str) else float(row[i])
    if math.isfinite(v):bucket.setdefault(j,{})[day]=v
   except (TypeError,ValueError):pass
 flush();index['groups'][group]=sorted(areas.values(),key=lambda a:a['label']);print(group,':',len(areas),'territorios;',sum(len(a['files']) for a in areas.values()),'archivos',flush=True)
(out/'index.json').write_text(json.dumps(index,ensure_ascii=False,separators=(',',':')),encoding='utf8')
