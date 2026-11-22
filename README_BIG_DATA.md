# Big Data · España

El dashboard incluye una instantánea de las hojas ESP_Consumo, Inversion_España y España_Activ_Sectorial. Las 70 series se muestran tal como figuran en la hoja, sin transformar su escala. La fecha más reciente depende de cada serie. Compruebe las unidades y metodología de la fuente antes de interpretar o comparar indicadores.

La hoja original tiene acceso restringido. El paquete incluye los datos seleccionados en bigdata.json y en las páginas generadas; si se publica en GitHub Pages, esos datos serán públicos. No incluye el libro Excel completo.

La actualización de Big Data todavía es manual: exporte la hoja de Google Sheets como Excel (.xlsx) y ejecute desde la carpeta del dashboard:

```
python -m pip install openpyxl
python importar_bigdata.py /ruta/al/archivo.xlsx
python build_page.py
```

Tras comprobar el resultado, suba bigdata.json, espana.html y artifact.html al repositorio. No incluya credenciales. El flujo de actualización de las series macroeconómicas no descarga automáticamente esta hoja privada.

## Datos territoriales

Los datos de comunidades autónomas, provincias y municipios se guardan en `bigdata_geo/`, divididos por territorio y por tipo (nominal o real). En Big Data se elige primero el territorio y después la serie. Los datos aparecen en la escala original de los archivos; las etiquetas proceden de sus encabezados.

Para actualizar los tres conjuntos territoriales, exporte los libros de comunidades, provincias y municipios como `.xlsx` y ejecute:

```
python importar_bigdata_territorial.py /ruta/ccaa.xlsx /ruta/provincias.xlsx /ruta/municipios.xlsx
```

Después, suba la carpeta `bigdata_geo/` y las páginas del dashboard que hayan cambiado. La actualización es manual: GitHub Actions no tiene acceso automático a estas hojas restringidas. Los archivos territoriales seleccionados se publicarán si se suben al repositorio público.
