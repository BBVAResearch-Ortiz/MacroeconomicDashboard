"""Actualiza GDPNow desde el punto de datos público de la Fed de Atlanta."""
import datetime,json,re,sys
from pathlib import Path
import requests
URL='https://www.atlantafed.org/data/research-data'
path=Path('gdpnow.json')
try:
 old=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
 response=requests.get(URL,timeout=30,headers={'User-Agent':'Macroeconomic-Dashboard/1.0'});response.raise_for_status()
 body=response.json();matches=[x for x in body.get('ResearchData',[]) if x.get('IconAlias')=='GDPNow']
 if len(matches)!=1:raise ValueError('No se encontró un indicador GDPNow único')
 item=matches[0];raw=str(item.get('Indicator','')).strip();m=re.fullmatch(r'([+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*%',raw)
 q=re.search(r'(20\d\d)\s*:\s*Q([1-4])',str(item.get('Name','')),re.I)
 if not m or not q:raise ValueError('Formato de valor o trimestre desconocido')
 stamp=str(item['UpdatedDate']);datetime.datetime.fromisoformat(stamp.replace('Z','+00:00'));value=float(m.group(1))
 if abs(value)>100:raise ValueError('Valor fuera de rango esperado')
 if old.get('updated_at') and stamp[:19]<old['updated_at'][:19]:raise ValueError('La fuente devolvió una estimación anterior')
 result={'value':value,'quarter':q.group(1)+'-Q'+q.group(2),'updated_at':stamp,'source':'Federal Reserve Bank of Atlanta · GDPNow','source_url':'https://www.atlantafed.org/research-and-data/data/gdpnow','description':'Tasa de crecimiento trimestral anualizada del PIB real; estimación del modelo GDPNow.'}
 path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('GDPNow actualizado:',result['quarter'],result['updated_at'])
except Exception as e:
 print('GDPNow no actualizado; se conserva la última estimación válida:',e,file=sys.stderr);sys.exit(1)
