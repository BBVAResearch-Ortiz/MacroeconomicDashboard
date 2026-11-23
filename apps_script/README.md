# Drive to GitHub CSV sync

`DriveToGitHubSync.gs` polls one Drive folder every five minutes and copies its CSV files to `manual_csv/` in `BBVAResearch-Ortiz/MacroeconomicDashboard` on branch `drive_processing`. It also updates `manual_csv/manifest.json`. The `espana.html` dashboard reads that manifest and the CSVs directly; no GitHub credential is included in the public page.

## One-time setup

1. Create a Drive folder for the CSVs and copy its folder ID from the URL.
2. Create a Google Apps Script project and paste in `DriveToGitHubSync.gs`.
3. Create a fine-grained GitHub token scoped to `BBVAResearch-Ortiz/MacroeconomicDashboard` on branch `drive_processing` with **Contents: Read and write**. Store it only in Apps Script **Project Settings → Script properties** as `GITHUB_TOKEN`; also add `DRIVE_FOLDER_ID` with the Drive folder ID.
4. In the Apps Script editor, run `syncDriveToGitHub` once and approve its Drive and external-request permissions.
5. Run `installDriveSyncTrigger` once. New or changed CSVs are copied to GitHub within about five minutes. This experimental branch is intended for review; publishing it to Pages depends on the repository Pages configuration. The importer refreshes the dashboard from this branch when deployed. The Apps Script pushes changes to `drive_processing`; it does not change the default branch.

## CSV contract

Put one CSV per series in the Drive folder. Required columns: `fecha`/`date` and `valor`/`value`. Optional metadata columns: `id`, `etiqueta`/`label`, `unidad`/`unit`, `frecuencia`/`frequency`, and `bloque`/`block`. If metadata is omitted, the script derives the series ID and label from the filename, infers D/M/Q frequency from the dates, and puts the series in the `manual` group.

```csv
fecha,valor,id,etiqueta,unidad,frecuencia,bloque
2025-01-01,1.2,actividad_local,Actividad local,%,Q,actividad
2025-04-01,1.4,actividad_local,Actividad local,%,Q,actividad
```

Supported frequencies are `D`, `M`, `Q`; supported blocks are `actividad`, `coyuntura`, `empleo`, `precios`, `vivienda`, `publico`, `exterior`, `financiero`, `credito`, and `manual`. Dates can be ISO (`YYYY-MM-DD`, `YYYY-MM`), quarters (`YYYY-Q1` through `YYYY-Q4`), or Spanish (`DD/MM/YYYY`).

The repository and Pages site are public, so only sync data that is suitable for public access. If a CSV is removed from Drive, it disappears from the dashboard manifest on the next sync; the old CSV file remains in GitHub until manually deleted.
