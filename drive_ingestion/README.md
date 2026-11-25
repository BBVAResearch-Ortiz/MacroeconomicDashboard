# Ingesta automática desde Google Drive

La ingesta lee las subcarpetas `Global Scenarios`, `Turkiye` y `Spain` de [FoW: Monitoring external information](https://drive.google.com/drive/folders/1Ejg2KKXKKT1QOjTb0OZFcZ0y2vUry2cr). Cada una admite un fichero `.xlsx` con el formato de `excel_madre.xlsx`.

- `LONG_DATA` contiene una fila por observación con `series_id`, `date` y `value`.
- `DICTIONARY` contiene los metadatos por `series_id`, incluidos título, descripción, transformación, fuente, frecuencia, cobertura, gráfico, bloque, área y unidad.
- Los libros anteriores con las hojas `DATOS_LARGO` y `DICCIONARIO` siguen siendo compatibles.
- Una carpeta vacía conserva su última salida, si existe. Una exportación incompleta o inválida deja disponible la última salida válida de esa carpeta.

## Ejecutar

En el proyecto de Google Cloud de la identidad de ejecución, habilita la API de Google Drive. Concede a esa identidad acceso de lectura a la carpeta raíz y a sus tres subcarpetas. El proceso usa [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials) y el alcance `drive.readonly`. Configura las credenciales en el entorno del servicio.

```powershell
python -m pip install -r drive_ingestion/requirements.txt
python drive_ingestion/sync.py drive_ingestion/local-data --site drive_ingestion/local-site --interval 900
```

El comando consulta Drive cada 15 minutos mientras está en ejecución. Para ejecutarlo desde un planificador externo, omite `--interval` y programa ese mismo comando. Solo se descarga y procesa una versión nueva de cada libro.

La primera ruta recibe las instantáneas `global.json`, `turkey.json` y `spain.json` cuando hay datos. La opción `--site` genera una copia del dashboard con las series de España añadidas al Blackboard bajo IDs `drive_es_*`. Sírvela con `python -m http.server 8000 --bind 127.0.0.1 --directory drive_ingestion/local-site` y abre [España](http://127.0.0.1:8000/espana.html#explorador). El Excel y las instantáneas de Global y Turquía quedan fuera de la copia del dashboard.

La ejecución online se configura en [Upload to Dashboard](apps_script/README.md).

## Fuente pública de Turquía

El [monitor de Turquía](../turquia.html#tr_cpi) conserva el libro maestro y consulta además el archivo publicado por el [Türkiye Macro Monitor de Batuhan Barlas](https://batuhan-barlas.github.io/turkey-macro-dashboard/). Su extracción de CBRT EVDS y TurkStat está programada a las 06:15 y 14:15 UTC. Este repositorio valida su publicación a las 07:40 y 15:40 UTC mediante el flujo `Check Türkiye public data`, que también se puede ejecutar manualmente.

El navegador consulta el archivo público al abrir Turquía, al pulsar **Actualizar datos** y cada 15 minutos mientras la página está abierta. Conserva las observaciones recibidas durante la sesión si falla una actualización. El libro maestro se carga por separado.

La integración utiliza los datos publicados en sus unidades y convenciones de signo originales. Admite las frecuencias diaria, semanal y mensual de la fuente. Cuando se comparan frecuencias distintas en dispersión, barras o mapas de calor, las series de mayor frecuencia se promedian por periodo.
