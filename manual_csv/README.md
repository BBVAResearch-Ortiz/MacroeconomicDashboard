# Manual CSV series

This public folder is the handoff point between Google Drive, Apps Script, and the dashboard.

- `manifest.json` is maintained by `apps_script/DriveToGitHubSync.gs`.
- Apps Script copies each CSV from the configured Drive folder here and updates the manifest.
- the `espana.html` dashboard reads the manifest and CSV files and adds the series to the dashboard and Blackboard.

## CSV format

Use one CSV per series. Required columns are `fecha` (or `date`) and `valor` (or `value`). Optional metadata columns are `id`, `etiqueta`/`label`, `unidad`/`unit`, `frecuencia`/`frequency`, and `bloque`/`block`. The metadata can be filled on the first data row; Apps Script infers missing values from the filename and observations.

Example:

```csv
fecha,valor,id,etiqueta,unidad,frecuencia,bloque
2025-01-01,1.2,actividad_local,Actividad local,%,Q,actividad
2025-04-01,1.4,actividad_local,Actividad local,%,Q,actividad
```

Dates may use `YYYY-MM-DD`, `YYYY-MM`, `YYYY-Q1`…`YYYY-Q4`, or `DD/MM/YYYY`. Decimal comma is supported in semicolon-delimited CSVs. Supported frequencies are `D`, `M`, and `Q`. Supported dashboard blocks include `actividad`, `coyuntura`, `empleo`, `precios`, `vivienda`, `publico`, `exterior`, `financiero`, `credito`, and `manual`. For Turkey experiments, prefix IDs with `turquia_` and set `bloque=manual` unless a Spanish dashboard category is also appropriate.

The repository and Pages site are public. Only place data here that is suitable for public access.
