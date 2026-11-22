"""Incorpora resultados FRB/US generados por frbus_escenarios.py a usa.html."""
import json,sys,re,math
from pathlib import Path
if len(sys.argv)!=2:raise SystemExit('Uso: python actualizar_frbus.py /ruta/resultados.json')
source=Path(sys.argv[1]);data=json.loads(source.read_text(encoding='utf-8'));scenarios=data.get('escenarios');rows=data.get('datos')
if not isinstance(scenarios,list) or not scenarios or not isinstance(rows,list) or not rows:raise SystemExit('Archivo sin escenarios o datos válidos.')
if data.get('errores'):raise SystemExit('El archivo informa errores; revísalos antes de publicarlo.')
ids={s.get('id') for s in scenarios};required={'pib','paro','inflacion','tipos'}
if None in ids or len(ids)!=len(scenarios):raise SystemExit('Identificadores de escenario inválidos.')
base={};allkeys=set()
for r in rows:
 try:
  scenario=r['escenario'];indicator=r['indicador'];period=r['trimestre'];b=float(r['base']);v=float(r['simulacion']);d=float(r['diferencia'])
 except (KeyError,TypeError,ValueError):raise SystemExit('Existe una observación incompleta o no numérica.')
 if scenario not in ids or indicator not in required or not re.fullmatch(r'\d{4}Q[1-4]',period) or not all(map(math.isfinite,[b,v,d])) or not math.isclose(v-b,d,rel_tol=1e-9,abs_tol=1e-12):raise SystemExit('Existe una observación incoherente.')
 k=(indicator,period)
 if k in base and not math.isclose(base[k],b,rel_tol=1e-9,abs_tol=1e-12):raise SystemExit('Las trayectorias base difieren entre escenarios.')
 base[k]=b;key=(scenario,indicator,period)
 if key in allkeys:raise SystemExit('Hay observaciones duplicadas.')
 allkeys.add(key)
periods={r['trimestre'] for r in rows}
if len(allkeys)!=len(ids)*len(required)*len(periods):raise SystemExit('La matriz de escenarios, fechas e indicadores está incompleta.')
html=Path('usa.html');text=html.read_text(encoding='utf-8');serialized=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/');pattern=r'(<script id="frbus-embedded" type="application/json">).*?(</script>)';result,n=re.subn(pattern,lambda m:m.group(1)+serialized+m.group(2),text,flags=re.S)
if n!=1:raise SystemExit('No se encontró un único bloque de datos FRB/US en usa.html.')
html.write_text(result,encoding='utf-8');Path('frbus_resultados.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8');print(f'Actualizados {len(ids)} escenarios y {len(rows)} registros en usa.html y frbus_resultados.json.')
