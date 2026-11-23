# Big Data · España

El monitor combina series nacionales de alta frecuencia y datos territoriales de consumo. El flujo experimental que las actualiza está en la rama `drive_processing`; no modifica `main`.

## Fuentes de Drive

- La hoja nativa `Alta Frecuencia - España` (carpeta [Alta Frecuencia en Drive](https://drive.google.com/drive/folders/1U8giN5bJ4tJLAtVf_rjlxLu9s6qGr3u2)) se exporta a XLSX. Sus hojas alimentan las series nacionales de consumo, inversión y actividad sectorial en `bigdata.json`.
- La carpeta [Big Data en Drive](https://drive.google.com/drive/folders/1thGWH7iyzwmC3YDjMHf1J_vwmPfNpm8H) contiene `Datos_informe.csv`, con observaciones diarias por territorio, y `Tabla_monitor.csv`, con el reporte publicado. Ambos se versionan en `drive_data/bigdata/`; el primero alimenta los datos territoriales y el segundo queda como archivo fuente de referencia.
- Las copias XLSX territoriales con fecha que aparecen junto a la hoja de alta frecuencia se ignoran. El CSV territorial anterior evita sincronizar varios XLSX grandes y repetidos.

Apps Script sondea las dos carpetas cada cinco minutos. Un workflow de GitHub Actions importa el XLSX, convierte el CSV territorial a `bigdata_geo/`, ejecuta `generar_heatmap.py` y regenera `espana.html` y `artifact.html`. El mapa de calor presenta observaciones al cierre de mes y semana; transforma fracciones a porcentaje y combina series BBVA Research con los dos indicadores del INE de `data.json`.

Los detalles de instalación están en [`apps_script/README.md`](apps_script/README.md). La futura carpeta de Turquía se conectará con la propiedad opcional `DRIVE_TURKEY_FOLDER_ID`.

## Publicación y privacidad

`drive_processing` es una rama experimental. Pages de `main` no se modifica ni cambia con esta automatización; para publicar la rama hace falta configurar una publicación de prueba o integrar los cambios más adelante. El repositorio es público: los CSV, el XLSX exportado y los datos generados en la rama también serán públicos. No sincronices datos que no estén aprobados para publicarse.
