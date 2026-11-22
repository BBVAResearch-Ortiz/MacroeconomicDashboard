# Big Data · España

El dashboard incluye una instantánea de las hojas ESP_Consumo, Inversion_España y España_Activ_Sectorial. Las 70 series se guardan en la escala original de la hoja; el gráfico de líneas las muestra en porcentaje (multiplica por 100 solo para la presentación). La fecha más reciente depende de cada serie. Compruebe las unidades y metodología de la fuente antes de interpretar o comparar indicadores.

La hoja original tiene acceso restringido. El paquete incluye los datos seleccionados en bigdata.json y en las páginas generadas; si se publica en GitHub Pages, esos datos serán públicos. No incluye el libro Excel completo.

La actualización de Big Data todavía es manual: exporte la hoja de Google Sheets como Excel (.xlsx) y ejecute desde la carpeta del dashboard:

```
python -m pip install openpyxl
python importar_bigdata.py /ruta/al/archivo.xlsx
python generar_heatmap.py
python build_page.py
```

Tras comprobar el resultado, suba bigdata.json, espana.html y artifact.html al repositorio. No incluya credenciales. El flujo de actualización de las series macroeconómicas no descarga automáticamente esta hoja privada.

## Datos territoriales

Los datos de comunidades autónomas, provincias y municipios se guardan en `bigdata_geo/`, divididos por territorio y por tipo (nominal o real). En Big Data se elige primero el territorio y después la serie. Los datos aparecen en la escala original de los archivos; las etiquetas proceden de sus encabezados.

Para actualizar los tres conjuntos territoriales, exporte los libros de comunidades, provincias y municipios como `.xlsx` y ejecute:

```
python importar_bigdata_territorial.py /ruta/ccaa.xlsx /ruta/provincias.xlsx /ruta/municipios.xlsx
```

Después ejecute `python generar_heatmap.py` y suba `bigdata_heatmap.json` junto con la carpeta `bigdata_geo/` y las páginas del dashboard que hayan cambiado. La actualización es manual: GitHub Actions no tiene acceso automático a estas hojas restringidas. Los archivos territoriales seleccionados se publicarán si se suben al repositorio público.

## Tabla de consumo

El mapa de calor se genera a partir del dato real al cierre de cada mes y semana, multiplicando por 100 las fracciones de la hoja. Incluye consumo nacional, sus categorías y el total de consumo territorial. Los dos indicadores del INE proceden de data.json y conservan sus unidades. El proceso no vuelve a calcular la variación interanual ni la media móvil: utiliza las series publicadas.
