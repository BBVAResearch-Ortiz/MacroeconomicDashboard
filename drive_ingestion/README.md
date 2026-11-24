# Ingesta automática desde Google Drive

La ingesta lee las subcarpetas `Global Scenarios`, `Turkiye` y `Spain` de [FoW: Monitoring external information](https://drive.google.com/drive/folders/1Ejg2KKXKKT1QOjTb0OZFcZ0y2vUry2cr). Cada una admite un fichero `.xlsx` con el formato de `excel_madre.xlsx`.

- `DATOS_LARGO` contiene una fila por observación con `id_serie`, `fecha` y `valor`.
- `DICCIONARIO` contiene los metadatos por `id_serie`, incluidos título, descripción, transformación, fuente, frecuencia, cobertura, gráfico, bloque, área y unidad.
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
