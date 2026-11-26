# Ingesta automática desde Google Drive

La ingesta lee las subcarpetas `Global Scenarios`, `Turkiye` y `Spain`, además de `USA` si existe, de [FoW: Monitoring external information](https://drive.google.com/drive/folders/1Ejg2KKXKKT1QOjTb0OZFcZ0y2vUry2cr). En `Spain` selecciona `excel_madre.xlsx`, aunque haya otras versiones. En `Turkiye` lee `turkey_macro_master.xlsx`, que Apps Script actualiza por ID. En las demás subcarpetas admite un único `.xlsx`.

- `LONG_DATA` contiene una fila por observación con `series_id`, `date` y `value`.
- `DICTIONARY` contiene los metadatos por `series_id`, incluidos título, descripción, transformación, fuente, frecuencia, cobertura, gráfico, bloque, área y unidad.
- Los libros anteriores con las hojas `DATOS_LARGO` y `DICCIONARIO` siguen siendo compatibles.
- La ingesta de Apps Script incorpora al JSON las traducciones de títulos y descripciones para el selector ES / EN. El proceso local en Python conserva los metadatos de origen.
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

## Fuentes de Turquía

El [monitor de Turquía](../turquia.html) carga las series del libro maestro con el nombre y el enlace del organismo que las publica. Las fuentes actuales son el Ministerio de Tesoro y Finanzas (HMB) y la Agencia de Regulación y Supervisión Bancaria (BDDK). Si falla la primera carga o el libro contiene solo ejemplos, el monitor utiliza la instantánea verificada.
