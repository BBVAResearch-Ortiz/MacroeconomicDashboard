# Upload to Dashboard

El [proyecto de Apps Script](https://script.google.com/d/1STAYKSxjDHDALjRbL_t4yHb8VoGI_U35x0xtmPaYJM9F1lNCGmc4CImM/edit) consulta `Spain`, `Global Scenarios` y `Turkiye` cada 15 minutos cuando se instala el disparador. Cada carpeta admite un Excel en el formato acordado.

Primero compara la revisión de cada Excel en Drive. Si cambió, convierte una copia temporal a Google Sheets y compara por separado los datos de `DATOS_LARGO` y los metadatos de `DICCIONARIO`. Cambios de formato, orden o pestañas auxiliares que no cambien la salida no producen un commit. Un Excel inválido deja disponible la última instantánea válida. Las carpetas vacías se comprobarán en la siguiente ejecución.

## Prueba en Google

1. Abre **Upload to Dashboard** y añade [UploadToDashboard.gs](UploadToDashboard.gs) como archivo de secuencia de comandos. Conserva los archivos existentes. Activa el servicio avanzado **Drive API v3** y, si el manifiesto declara permisos explícitos, incorpora los de [appsscript.json](appsscript.json).
2. Ejecuta `previewDashboardUpload`. La prueba no escribe en GitHub. Comprueba que se registran 145 series y 58.916 observaciones para la versión inicial de España. Revisa la duración de la primera ejecución con el Excel real.

## Activación

La rama remota `drive_processing` debe contener el workflow `drive-preview.yml`. Cuando las series estén autorizadas para el repositorio de destino, configura la propiedad de proyecto `FOW_DASHBOARD_GITHUB_TOKEN` con un token que tenga permiso **Contents: read and write** en `BBVAResearch-Ortiz/MacroeconomicDashboard`. Ejecuta `syncDashboardFromDrive`, revisa la primera salida y después ejecuta `installDashboardUploadTrigger` con la cuenta que mantendrá la automatización.

Revisa los disparadores existentes del proyecto antes de activar el nuevo para evitar que dos sincronizaciones procesen la misma fuente.

El script sube los JSON procesados a `drive_ingestion/snapshots/`. GitHub Actions genera la vista previa de España con los datos actuales y los importados. El workflow entrega el artefacto `drive-dashboard-preview`. La configuración de Pages requiere un despliegue separado.
