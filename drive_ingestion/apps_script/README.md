# Upload to Dashboard

El [proyecto de Apps Script](https://script.google.com/d/1STAYKSxjDHDALjRbL_t4yHb8VoGI_U35x0xtmPaYJM9F1lNCGmc4CImM/edit) consulta `Spain`, `Global Scenarios` y `Turkiye` cada 15 minutos cuando se instala el disparador. Cada carpeta admite un Excel en el formato acordado.

Primero compara la revisión de cada Excel en Drive. Si cambió, convierte una copia temporal a Google Sheets y compara por separado los datos de `LONG_DATA` y los metadatos de `DICTIONARY`. También admite los libros anteriores con encabezados y pestañas en español. Cambios de formato, orden o pestañas auxiliares que no cambien la salida no producen un commit. Un Excel inválido deja disponible la última instantánea válida. Las carpetas vacías se comprobarán en la siguiente ejecución.

## Prueba en Google

1. Abre **Upload to Dashboard** y añade [UploadToDashboard.gs](UploadToDashboard.gs) como archivo de secuencia de comandos. Conserva los archivos existentes. Activa el servicio avanzado **Drive API v3** y, si el manifiesto declara permisos explícitos, incorpora los de [appsscript.json](appsscript.json).
2. Ejecuta `previewDashboardUpload`. La prueba no escribe en GitHub. Comprueba que se registran 145 series y 58.916 observaciones para la versión inicial de España. Revisa la duración de la primera ejecución con el Excel real.

Si mantienes una lista explícita de permisos, usa `https://www.googleapis.com/auth/spreadsheets` para `SpreadsheetApp.openById`. El permiso `spreadsheets.readonly` es insuficiente para ese método. Guarda el manifiesto y vuelve a ejecutar la prueba para autorizar el cambio.

Antes de sustituir los Excel de Drive por sus ediciones en inglés, actualiza `Código.gs` con la versión de `UploadToDashboard.gs` que admite `DICTIONARY` y `LONG_DATA`. Los activadores existentes usan ese código al guardar y mantienen su horario.

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
3. Verifica la pestaña Big Data de España en Pages y ejecuta una vez `installDashboardBigDataTrigger` para comprobar cambios cada miércoles alrededor de las 18:00, hora peninsular (`Europe/Madrid`). Google puede variar la ejecución hasta 15 minutos. Si ya instalaste un disparador de Big Data, vuelve a ejecutar esta función con la misma cuenta para sustituirlo. El disparador del Blackboard sigue cada 15 minutos.

Los archivos de origen quedan en Drive. El script guarda solo las series, el índice territorial y el mapa de calor procesados en `drive_ingestion/snapshots/bigdata/`. La página consulta esa salida en cada carga y usa sus datos de respaldo hasta que esté disponible.

## Piloto de Turquía

En **Upload to Dashboard**, sustituye el código del importador por la versión de `UploadToDashboard.gs` de este repositorio, añade `UploadTurkeyData.gs` como archivo de secuencia de comandos y actualiza `appsscript.json`. El manifiesto pide acceso de escritura a Drive para actualizar el Excel existente por ID. Autoriza el cambio con la cuenta que mantiene los disparadores. Esa cuenta necesita permiso de edición sobre el Excel madre de `Turkiye`.

1. Ejecuta `previewTurkeyWorkbook`. Solo trabaja sobre copias temporales. El registro muestra el número de observaciones y la última fecha de cada serie, y si cambiaría el Excel.
2. Ejecuta `syncTurkeyWorkbook`. Al detectar cambios, actualiza el `.xlsx` que ya está en `Turkiye` conservando su ID. Actualiza el saldo, los ingresos y los gastos de caja del Tesoro, el crédito semanal de BDDK y el crédito y los depósitos mensuales de BDDK. Preserva las demás series y conserva los últimos datos de una fuente si esta falla. Si el productor registra un 403 al guardar, comprueba que la cuenta pueda editar el fichero y que el proyecto tenga autorización de escritura sobre ese archivo.
3. Ejecuta `syncDashboardFromDrive` o espera su disparador de 15 minutos. Si cambia el contenido, el importador registra el SHA del commit y la instantánea de Turquía incluye `origen.updated_at`. Cuando el sitio reciba ese JSON, aparecerá **Excel publicado** en el monitor de Turquía.
4. Tras comprobar el circuito, ejecuta `installTurkeyWorkbookTrigger`. Programa una comprobación diaria alrededor de las 19:00, hora de Estambul. El primer pase consulta hasta 12 meses de BDDK mensual y el histórico semanal que devuelve el boletín. Los siguientes consultan los tres meses recientes y conservan el histórico ya guardado.

Para confirmar un despliegue, abre [el entorno `github-pages`](https://github.com/BBVAResearch-Ortiz/MacroeconomicDashboard/deployments/github-pages) y compara el SHA desplegado con el commit de la sincronización. El flujo **Build Drive dashboard preview** genera un artefacto de prueba. Para comprobar los datos que recibe la web, abre [el JSON servido por Pages](https://bbvaresearch-ortiz.github.io/MacroeconomicDashboard/drive_ingestion/snapshots/turkey.json) y revisa `origen.updated_at` y la última observación de la serie. La fecha de publicación del Excel y la fecha de observación miden cosas distintas.
