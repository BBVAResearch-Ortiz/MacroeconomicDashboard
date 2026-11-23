# Ingesta de Drive en `drive_processing`

El proyecto escribe en `BBVAResearch-Ortiz/MacroeconomicDashboard`, rama `drive_processing`. Agrupa los archivos y manifiestos que cambian en un solo commit. GitHub Actions procesa ese commit y genera el artefacto `drive-dashboard-preview`.

| Fuente | Datos | Ruta en la rama |
| --- | --- | --- |
| [Big Data](https://drive.google.com/drive/folders/1thGWH7iyzwmC3YDjMHf1J_vwmPfNpm8H) | `Datos_informe.csv` para consumo diario y territorios, `Tabla_monitor.csv` para el mapa de calor | `drive_data/bigdata/` |
| [Datos manuales](https://drive.google.com/drive/folders/1U8giN5bJ4tJLAtVf_rjlxLu9s6qGr3u2) | CSV de series y hoja `Alta Frecuencia - España` (consumo total real y nominal) | `manual_csv/` y `drive_data/manual/` |
| Turquía | CSV de series de la carpeta indicada por `DRIVE_TURKEY_FOLDER_ID` (opcional) | `turkey_csv/` |

Los CSV de series admiten columnas `fecha` y `valor` (o `date` y `value`), y los campos opcionales `unidad` y `frecuencia` (`D`, `M`, `Q`). Los datos sincronizados son visibles en la rama pública de GitHub.

## Sustituir el código del proyecto existente

1. En **Configuración del proyecto → Propiedades de la secuencia de comandos**, añade `GITHUB_TOKEN_DRIVE_PROCESSING` con un token que tenga permiso **Contents: Read and write** sobre `BBVAResearch-Ortiz/MacroeconomicDashboard`. El token de la copia anterior puede seguir guardado en `GITHUB_TOKEN`.
2. Sustituye en el editor el contenido del archivo que define `syncDriveToGitHub` por [DriveToGitHubSync.gs](DriveToGitHubSync.gs). La sincronización usa los permisos de Drive, peticiones externas y disparadores que figuran en [appsscript.json](appsscript.json).
3. Ejecuta `syncDriveToGitHub` y comprueba el commit en `drive_processing`. Al repetir la ejecución sin cambios en las fuentes, el registro debe mostrar `GitHub sync: no changes.`.
4. El disparador existente conserva el nombre `syncDriveToGitHub` y pasa a usar el código guardado. Si el proyecto no tiene disparador, ejecuta `installDriveSyncTrigger` para programarlo cada cinco minutos.

## Ver el resultado

Descarga y extrae `drive-dashboard-preview` desde la ejecución de **Build Drive dashboard preview** en GitHub Actions. Abre una terminal en la carpeta extraída, ejecuta `python -m http.server 8000 --bind 127.0.0.1` y visita `http://127.0.0.1:8000/espana.html`. El artefacto incluye los archivos que carga el dashboard en el navegador.
