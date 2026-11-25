# Monitor por países

La portada `index.html` permite elegir país. El monitor de España está en `espana.html`. El enlace de Turquía abre `turquia.html`, que usa el Blackboard y carga `drive_ingestion/snapshots/turkey.json`. México, Argentina, Colombia, Perú y Venezuela tienen una página provisional. Los enlaces antiguos con secciones en el fragmento se redirigen a España.

El enlace de Estados Unidos abre `usa.html`, con Blackboard (`drive_ingestion/snapshots/usa.json`) y Modelos (`GDPNow` y `FRB/US`).

El proceso `build_page.py` regenera `espana.html`, `artifact.html`, `turquia.html` y `usa.html` a partir de la misma plantilla. Antes de subir, compare con la versión actual del repositorio.
