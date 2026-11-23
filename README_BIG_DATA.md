# Big Data · España

El monitor combina series nacionales de alta frecuencia y datos territoriales de consumo. El flujo experimental que las actualiza está en la rama `drive_processing`; no modifica `main`.

## Fuentes de Drive

- La hoja nativa `Alta Frecuencia - España` de la carpeta [Datos manuales en Drive](https://drive.google.com/drive/folders/1U8giN5bJ4tJLAtVf_rjlxLu9s6qGr3u2) se exporta a XLSX. Sus dos series de consumo total, real y nominal, aparecen en Datos manuales.
- La carpeta [Big Data en Drive](https://drive.google.com/drive/folders/1thGWH7iyzwmC3YDjMHf1J_vwmPfNpm8H) contiene `Datos_informe.csv`, que actualiza las series diarias de consumo nacional y territorial, y `Tabla_monitor.csv`, que actualiza los cierres mensuales y semanales del mapa de calor. Ambos se versionan en `drive_data/bigdata/`.
- Las copias XLSX territoriales con fecha que aparecen junto a la hoja de alta frecuencia se ignoran. El CSV territorial anterior evita sincronizar varios XLSX grandes y repetidos.

Apps Script sondea las carpetas configuradas cada cinco minutos. GitHub Actions procesa las exportaciones y empaqueta `espana.html`, `artifact.html` y los datos del dashboard como artefacto descargable. El mapa de calor presenta observaciones al cierre de mes y semana, transforma fracciones a porcentaje y combina series BBVA Research con dos indicadores del INE de `data.json`.

Los detalles de instalación están en [`apps_script/README.md`](apps_script/README.md). La futura carpeta de Turquía se conectará con la propiedad opcional `DRIVE_TURKEY_FOLDER_ID`.

## Publicación y privacidad

`drive_processing` es una rama experimental. Pages de `main` no se modifica ni cambia con esta automatización; para publicar la rama hace falta configurar una publicación de prueba o integrar los cambios más adelante. El repositorio es público: los CSV, el XLSX exportado y los datos generados en la rama también serán públicos. No sincronices datos que no estén aprobados para publicarse.
