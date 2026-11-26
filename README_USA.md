# Estados Unidos · Blackboard y Modelos

El monitor `usa.html` incluye la pestaña **Blackboard** (alimentada desde `drive_ingestion/snapshots/usa.json` cuando se publica el libro maestro en la subcarpeta `USA` de Google Drive) y la pestaña **Modelos**.

En la sección Modelos, las tarjetas GDPNow y FRB/US abren sus vistas, con un botón para volver al menú. La página usa la última observación GDPNow disponible de la Fed de Atlanta. Es una tasa anualizada de crecimiento trimestral del PIB real y no es una previsión oficial del FOMC. El archivo gdpnow.json inicial es una instantánea verificada; la fecha figura en la pantalla.

update_gdpnow.py consulta la fuente oficial y valida trimestre, fecha y valor; si falla, conserva la última observación. El flujo de GitHub lo ejecuta junto con el resto de actualizaciones. El acceso directo desde GitHub Actions aún debe probarse. No exponga claves privadas en el repositorio.

FRB/US presenta ocho escenarios precalculados por el usuario en PyFRB/US para 2040T1–2045T4. Los gráficos permiten seleccionar escenarios y visualizar trayectorias o diferencias. Cambiar la selección no ejecuta el modelo. La trayectoria pública LONGBASE es ilustrativa y no es una previsión oficial de la Fed. Los shocks de consumo y vivienda afectan residuos de ecuaciones; el shock de tipos de cuatro trimestres se aplica repetidamente a la ecuación de política.

Para incorporar resultados nuevos, ejecute el modelo en un entorno compatible y desde esta carpeta use:

```
python actualizar_frbus.py /ruta/resultados.json
```

El actualizador valida la consistencia de la base y las diferencias y actualiza usa.html y frbus_resultados.json. Suba ambos archivos. GitHub Pages es estático: ejecutar PyFRB/US para un escenario arbitrario requiere un servicio de cálculo o una adaptación contrastada para navegador.

## DSGE de la Fed de Nueva York

La ficha «DSGE FRB-NY» de la sección Modelos muestra las previsiones que publica la Fed de Nueva York; aquí no se ejecuta el modelo.

- `update_dsge_frbny.py` descarga los CSV que alimentan los gráficos interactivos oficiales (`newyorkfed.org/research/policy/dsge#/interactive`) y escribe `dsge_frbny.json`: tabla 4T/4T con banda del 68 %, abanicos trimestrales con bandas del 50 al 90 % y la revisión frente a la previsión anterior.
- Cuando cambia la fecha de publicación, la tabla anterior se conserva como comparación.
- El flujo `update-data.yml` lo ejecuta los días laborables; la página también relee `dsge_frbny.json` al abrirse y con «Actualizar datos».
- La Fed publica una previsión por trimestre (marzo, junio, septiembre y diciembre).

### Simulador de shocks

- `dsge_irf.json` contiene las respuestas al impulso de Model1002 (especificación `ss10`, parámetros por defecto del paquete) calculadas con DSGE.jl, el paquete público de la Fed de Nueva York: PIB, inflación PCE subyacente, tipo de los fondos federales, diferencial de crédito y tipo natural real ante seis shocks de una desviación típica.
- Como el modelo es lineal, la página escala y suma esas respuestas según los deslizadores y dibuja el escenario sobre la previsión publicada. El shock ocurre en el trimestre siguiente al de la publicación.
- Es un cálculo propio, no un escenario de la Fed: los parámetros por defecto no tienen por qué coincidir con su estimación actual, y las bandas no se recalculan.
- `dsge_irf.jl` regenera el archivo (instrucciones de instalación en su cabecera). Solo hace falta si cambian el modelo o los parámetros; no depende de los datos de cada trimestre.

## CPI Nowcasting (Fed de Cleveland)

La ficha «CPI Nowcasting» muestra el nowcast de inflación que publica la Fed de Cleveland (CPI y PCE, general y subyacente); aquí no se ejecuta el modelo.

- `update_inflation_nowcast.py` descarga los tres archivos públicos de la Fed de Cleveland (mes, trimestre e interanual) y escribe `inflation_nowcast.json`: seis meses de referencia con la trayectoria diaria del nowcast, tres trimestres y el historial de 36 meses de nowcast final frente a dato publicado.
- El workflow `update-data.yml` lo ejecuta cada día hábil. La página incrusta el último archivo y además lo vuelve a pedir al abrirse, así que basta con que el workflow actualice el JSON.
- El error absoluto medio del historial se calcula en la página a partir de ese archivo.

## Catálogo de series (FRED)

`scripts/fetch_usa_apis.py` descarga 55 series de FRED. El campo `bloque` de cada serie decide su categoría en el desplegable del Blackboard, que solo muestra estas ocho, sin subcategorías:

| Categoría | `bloque` | Series |
|---|---|---|
| Actividad | `actividad` | GDPC1, PCE, PCEC96, INDPRO, TCU, RSAFS, DGORDER, UMCSENT, CFNAI |
| Empleo | `empleo` | UNRATE, U6RATE, PAYEMS, CIVPART, JTSJOL, CES0500000003, ICSA, CCSA |
| Precios | `precios` | CPIAUCSL, CPILFESL, PCEPI, PCEPILFE, PPIFIS, MICH, T5YIE, DCOILWTICO |
| Monetario | `monetario` | FEDFUNDS, DFEDTARU, DGS2, DGS10, T10Y2Y, M2SL, WALCL |
| Financiero | `financiero` | SP500, VIXCLS, BAA10Y, NFCI, MORTGAGE30US, DTWEXBGS |
| Fiscal | `fiscal` | MTSDS133FMS, GFDEBTN, GFDEGDQ188S, W006RC1Q027SBEA, FGEXPND, A091RC1Q027SBEA |
| Exterior | `exterior` | BOPGSTB, BOPTEXP, BOPTIMP, IEABC, DEXUSEU |
| Vivienda | `vivienda` | HOUST, PERMIT, HSN1F, EXHOSLUSM495S, CSUSHPISA, MSPUS |

Para añadir una serie basta una entrada nueva en `SERIES_CONFIG` con su `fred_id`, frecuencia (`D`, `W`, `M` o `Q`; nunca anual) y `bloque`. El título debe acabar con la fuente entre paréntesis («Real GDP (BEA)»): los títulos de los gráficos la omiten. Las tres primeras entradas del catálogo son las series que se muestran por defecto.

Los datos llegan cuando se ejecuta el flujo «Update USA Macro Data from APIs» (a diario, o a mano con *Run workflow*). Una serie cuyo identificador falle se omite con un aviso y no interrumpe el resto.

