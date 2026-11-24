# Upload to Dashboard

El [proyecto de Apps Script](https://script.google.com/d/1STAYKSxjDHDALjRbL_t4yHb8VoGI_U35x0xtmPaYJM9F1lNCGmc4CImM/edit) consulta `Spain`, `Global Scenarios` y `Turkiye` cada 15 minutos cuando se instala el disparador. Cada carpeta admite un Excel en el formato acordado.

Primero compara la revisión de cada Excel en Drive. Si cambió, convierte una copia temporal a Google Sheets y compara por separado los datos de `DATOS_LARGO` y los metadatos de `DICCIONARIO`. Cambios de formato, orden o pestañas auxiliares que no cambien la salida no producen un commit. Un Excel inválido deja disponible la última instantánea válida. Las carpetas vacías se comprobarán en la siguiente ejecución.

## Prueba en Google

1. Abre **Upload to Dashboard** y añade [UploadToDashboard.gs](UploadToDashboard.gs) como archivo de secuencia de comandos. Conserva los archivos existentes. Activa el servicio avanzado **Drive API v3** y, si el manifiesto declara permisos explícitos, incorpora los de [appsscript.json](appsscript.json).
2. Ejecuta `previewDashboardUpload`. La prueba no escribe en GitHub. Comprueba que se registran 145 series y 58.916 observaciones para la versión inicial de España. Revisa la duración de la primera ejecución con el Excel real.

Si mantienes una lista explícita de permisos, usa `https://www.googleapis.com/auth/spreadsheets` para `SpreadsheetApp.openById`. El permiso `spreadsheets.readonly` es insuficiente para ese método. Guarda el manifiesto y vuelve a ejecutar la prueba para autorizar el cambio.

## Activación

La rama remota `main` debe contener el workflow `drive-preview.yml`. Esta integración de código se puede hacer antes de configurar el token. Cuando las series estén autorizadas para el repositorio de destino, configura la propiedad de proyecto `FOW_DASHBOARD_GITHUB_TOKEN` con un token que tenga permiso **Contents: read and write** en `BBVAResearch-Ortiz/MacroeconomicDashboard`. Ejecuta `syncDashboardFromDrive`, revisa la primera salida y después ejecuta `installDashboardUploadTrigger` con la cuenta que mantendrá la automatización.

Revisa los disparadores existentes del proyecto antes de activar el nuevo para evitar que dos sincronizaciones procesen la misma fuente.

El script sube los JSON procesados a `drive_ingestion/snapshots/`. El Blackboard de España en Pages consulta `spain.json` al abrir o actualizar la página. GitHub Actions también genera el artefacto descargable `drive-dashboard-preview`.

## Big Data de España

Añade [UploadBigData.gs](UploadBigData.gs) al mismo proyecto y actualiza [UploadToDashboard.gs](UploadToDashboard.gs) con la versión de `main`. Usa los permisos y el token ya configurados para el Blackboard.

- [Carpeta de exportaciones](https://drive.google.com/drive/folders/1thGWH7iyzwmC3YDjMHf1J_vwmPfNpm8H). `Datos_informe.csv` actualiza consumo real nacional y territorial y `Tabla_monitor.csv` alimenta el mapa de calor.
- [Carpeta de Alta Frecuencia](https://drive.google.com/drive/folders/1U8giN5bJ4tJLAtVf_rjlxLu9s6qGr3u2). El script lee las pestañas `ESP_Consumo`, `Inversion_España` y `España_Activ_Sectorial` de `Alta Frecuencia - España`. Las copias territoriales con fecha quedan como histórico en Drive.

1. Ejecuta `previewDashboardBigData` y comprueba que el registro muestre series nacionales, territorios y filas del mapa de calor. La prueba solo lee las fuentes.
2. Confirma que los datos procesados se pueden publicar en el repositorio público y ejecuta una vez `syncDashboardBigData`.
3. Verifica la pestaña Big Data de España en Pages y ejecuta una vez `installDashboardBigDataTrigger` para comprobar cambios cada 15 minutos. Este disparador es independiente del que alimenta el Blackboard.

Los archivos de origen quedan en Drive. El script guarda solo las series, el índice territorial y el mapa de calor procesados en `drive_ingestion/snapshots/bigdata/`. La página consulta esa salida en cada carga y usa sus datos de respaldo hasta que esté disponible.
