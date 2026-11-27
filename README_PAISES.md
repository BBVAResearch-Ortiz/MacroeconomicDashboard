# Monitor por países

La portada `index.html` permite elegir país. El monitor de España está en `espana.html`. El enlace de Turquía abre `turquia.html`, que usa el Blackboard y carga `drive_ingestion/snapshots/turkey.json`. México, Argentina, Colombia, Perú y Venezuela tienen una página provisional. Los enlaces antiguos con secciones en el fragmento se redirigen a España.

El enlace de Estados Unidos abre `usa.html`, con Blackboard (`drive_ingestion/snapshots/usa.json`) y Modelos (`GDPNow` y `FRB/US`).

El proceso `build_page.py` usa `template_spain_turkey.html` para generar `espana.html`, `artifact.html` y `turquia.html`. `template.html` genera `usa.html` con sus módulos de modelos. Antes de subir, compare con la versión actual del repositorio.
