#!/usr/bin/env python3
"""Ejemplos de simulación con PyFRB/US. No constituye una previsión de la Fed."""
from pathlib import Path
from datetime import datetime
import argparse
import json
import math
import sys
import traceback

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pyfrbus.frbus import Frbus
from pyfrbus.load_data import load_data

SCENARIOS=[
 {'id':'tipos_mas_25','label':'Tipos +25 pb, 1 trimestre','equation':'rffintay_aerr','size':0.25,'duration':1},
 {'id':'tipos_mas_50','label':'Tipos +50 pb, 1 trimestre','equation':'rffintay_aerr','size':0.50,'duration':1},
 {'id':'tipos_mas_100','label':'Tipos +100 pb, 1 trimestre','equation':'rffintay_aerr','size':1.00,'duration':1},
 {'id':'tipos_menos_100','label':'Tipos −100 pb, 1 trimestre','equation':'rffintay_aerr','size':-1.00,'duration':1},
 {'id':'tipos_mas_100_persistente','label':'Tipos +100 pb, 4 trimestres','equation':'rffintay_aerr','size':1.00,'duration':4},
 {'id':'prima_credito_mas_100','label':'Prima BBB +100 pb, 1 trimestre','equation':'rbbbp_aerr','size':1.00,'duration':1},
 {'id':'consumo_shock','label':'Shock negativo en ecuación de consumo','equation':'eco_aerr','size':-0.01,'duration':1},
 {'id':'vivienda_shock','label':'Shock negativo en ecuación de vivienda','equation':'eh_aerr','size':-0.01,'duration':1},
]
VARIABLES={'pib':'Crecimiento del PIB real (% interanual)','paro':'Tasa de desempleo (%)','inflacion':'Inflación PCE subyacente (% interanual)','tipos':'Tipo de los fondos federales (%)'}

def finite(value):
 try:
  x=float(value)
  return x if math.isfinite(x) else None
 except (TypeError,ValueError):return None

def indicators(frame,index):
 return {'pib':frame['xgdp'].pct_change(4,fill_method=None).mul(100).loc[index], 'paro':frame['lur'].loc[index], 'inflacion':frame['pcxfe'].pct_change(4,fill_method=None).mul(100).loc[index], 'tipos':frame['rff'].loc[index]}

def main():
 parser=argparse.ArgumentParser(description='Escenarios ilustrativos usando los ejemplos FRB/US.')
 parser.add_argument('--inicio',default='2040Q1',help='Trimestre inicial, por defecto 2040Q1 como el ejemplo oficial')
 parser.add_argument('--trimestres',type=int,default=24,help='Duración total, por defecto 24 trimestres')
 parser.add_argument('--proyecto',type=Path,default=Path.home()/'Downloads/FRBUS_prueba_inicial/pyfrbus')
 parser.add_argument('--salida',type=Path,default=Path.home()/'Downloads',help='Carpeta donde crear los resultados')
 args=parser.parse_args()
 if args.trimestres<4 or args.trimestres>80:parser.error('El horizonte debe estar entre 4 y 80 trimestres')
 root=args.proyecto.expanduser().resolve();source=root/'data/LONGBASE.TXT';model=root/'models/model.xml'
 for file in [source,model]:
  if not file.is_file():raise FileNotFoundError(f'No se encuentra {file}; usa --proyecto para señalar la carpeta pyfrbus.')
 start=pd.Period(args.inicio,freq='Q');end=start+args.trimestres-1;periods=pd.period_range(start,end,freq='Q');hist=pd.period_range(start-4,end,freq='Q')
 print(f'Cargando modelo. Periodo: {start} a {end}.',flush=True)
 data=load_data(str(source))
 if not hist.isin(data.index).all():raise ValueError('El periodo o los cuatro trimestres anteriores no están completos en LONGBASE.TXT.')
 model_obj=Frbus(str(model));data.loc[start:end,'dfpdbt']=0;data.loc[start:end,'dfpsrp']=1
 print('Calculando escenario base...',flush=True);baseline=model_obj.init_trac(start,end,data)
 base=indicators(baseline,periods);successful=[];errors=[]
 for spec in SCENARIOS:
  print('Calculando:',spec['label'],flush=True)
  try:
   if spec['equation'] not in baseline.columns:raise KeyError('No está disponible '+spec['equation'])
   values=baseline.copy(deep=True);values.loc[start:start+spec['duration']-1,spec['equation']]+=spec['size']
   result=model_obj.solve(start,end,values);out=indicators(result,periods)
   if any(not math.isfinite(float(v)) for col in out.values() for v in col):raise ValueError('La solución contiene valores vacíos o no finitos.')
   successful.append((spec,out))
  except Exception as exc:
   print('  No se pudo calcular:',str(exc),flush=True);errors.append({'escenario':spec['id'],'error':str(exc),'detalle':traceback.format_exc()})
 if not successful:raise RuntimeError('Ningún escenario se pudo calcular; revisa los errores anteriores.')
 folder=args.salida.expanduser()/('FRBUS_resultados_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'));folder.mkdir(parents=True,exist_ok=False)
 records=[]
 for j,period in enumerate(periods):
  for spec,out in successful:
   for key in VARIABLES:
    b=finite(base[key].iloc[j]);v=finite(out[key].iloc[j]);records.append({'escenario':spec['id'],'nombre':spec['label'],'trimestre':str(period),'indicador':key,'base':b,'simulacion':v,'diferencia':v-b if b is not None and v is not None else None})
 pd.DataFrame(records).to_csv(folder/'resultados.csv',index=False,encoding='utf-8-sig')
 document={'modelo':'FRB/US · PyFRB/US','inicio':str(start),'fin':str(end),'advertencia':'Simulaciones ilustrativas, no previsiones oficiales de la Fed. LONGBASE incluye una trayectoria de referencia mecánica.','escenarios':[x for x,_ in successful],'errores':errors,'datos':records}
 (folder/'resultados.json').write_text(json.dumps(document,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
 fig,axes=plt.subplots(2,2,figsize=(14,9),layout='constrained');colors=plt.get_cmap('tab10')
 for ax,(key,title) in zip(axes.flat,VARIABLES.items()):
  ax.plot(range(len(periods)),base[key],color='#001391',linewidth=2.5,label='Base')
  for i,(spec,out) in enumerate(successful):ax.plot(range(len(periods)),out[key],color=colors(i),linewidth=1.3,label=spec['label'])
  step=max(1,len(periods)//6);ticks=list(range(0,len(periods),step));ax.set_xticks(ticks,[str(periods[i]) for i in ticks],rotation=30,ha='right');ax.set_title(title,color='#001391',fontsize=11);ax.grid(alpha=.18)
 handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=3,fontsize=8);fig.suptitle('FRB/US · Escenario base y simulaciones ilustrativas',color='#001391');fig.savefig(folder/'comparacion.png',dpi=160);plt.close(fig)
 (folder/'LEEME.txt').write_text('Las simulaciones son ilustrativas y no son previsiones oficiales de la Fed. El escenario base público es una trayectoria mecánica. Los shocks de consumo y vivienda son alteraciones de residuos de ecuaciones logarítmicas, no cambios garantizados en el nivel observado. Consulte resultados.json para los valores y shocks exactos.\n',encoding='utf8')
 print('\nResultados guardados en:',folder,flush=True)
 if errors:print('Atención: no se pudieron calcular',len(errors),'escenarios; detalles en resultados.json.',flush=True)
 print('Archivos: comparacion.png, resultados.csv, resultados.json y LEEME.txt',flush=True)
 return 0
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as exc:print('\nError:',exc,file=sys.stderr);sys.exit(1)
