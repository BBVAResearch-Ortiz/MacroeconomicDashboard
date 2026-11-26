#!/usr/bin/env python3
"""Descarga las previsiones publicadas del modelo DSGE de la Fed de Nueva York.

Lee los mismos CSV que alimentan los gráficos interactivos oficiales
(https://www.newyorkfed.org/research/policy/dsge#/interactive) y escribe
``dsge_frbny.json``. No ejecuta el modelo: solo copia las cifras publicadas.

Si la Fed publica una previsión nueva, la tabla anterior se conserva como
"previous" para poder compararlas. Ante cualquier fallo se mantiene el
archivo existente y el script termina con error.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://www.newyorkfed.org/medialibrary/research/interactives/data/dsge/"
OUT = Path("dsge_frbny.json")
BANDS = [50, 60, 68, 70, 80, 90]
FANS = {
    "gdp": "Four-quarter_percentage_change_PseudoGDP.csv",
    "core_pce": "Four-quarter_percentage_change_PseudoCorePCE.csv",
    "rstar": "Percent_NaturalRate.csv",
}
REVISIONS = {
    "gdp": "Quarter-to-quarter_percentage_change_annualized_PseudoGDP.csv",
    "core_pce": "Quarter-to-quarter_percentage_change_annualized_PseudoCorePCE.csv",
}
TABLE_ROWS = {
    "gdp": "GDP growth",
    "core_pce": "Core PCE inflation",
    "rstar": "Real natural rate of interest",
}
MONTHS = {name: number for number, name in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], start=1)}


def fetch(name: str) -> str:
    response = requests.get(BASE + name, timeout=40, headers={"User-Agent": "MacroeconomicDashboard/1.0"})
    response.raise_for_status()
    return response.content.decode("utf-8-sig")


def number(text: str):
    text = (text or "").strip()
    return round(float(text), 3) if text else None


def read_rows(text: str, required: list[str]) -> list[dict]:
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or any(column not in rows[0] for column in required):
        raise ValueError(f"columnas inesperadas: {list(rows[0]) if rows else 'sin filas'}")
    return rows


def read_fan(text: str) -> dict:
    columns = [f"{band:.1f}%_{side}" for band in BANDS for side in ("lb", "ub")]
    rows = read_rows(text, ["dates", "mean_history", "mean_forecast", *columns])
    fan = {
        "dates": [row["dates"] for row in rows],
        "history": [number(row["mean_history"]) for row in rows],
        "forecast": [number(row["mean_forecast"]) for row in rows],
        "bands": {str(band): [[number(row[f"{band:.1f}%_lb"]), number(row[f"{band:.1f}%_ub"])] for row in rows]
                  for band in BANDS},
    }
    if not any(value is not None for value in fan["forecast"]):
        raise ValueError("el CSV no trae previsión")
    return fan


def read_revision(text: str) -> dict:
    rows = read_rows(text, ["dates", "mean_forecast_old", "mean_history", "mean_forecast_new"])
    return {
        "dates": [row["dates"] for row in rows],
        "history": [number(row["mean_history"]) for row in rows],
        "previous": [number(row["mean_forecast_old"]) for row in rows],
        "current": [number(row["mean_forecast_new"]) for row in rows],
    }


def read_table(text: str) -> tuple[list[int], dict]:
    rows = list(csv.reader(io.StringIO(text)))
    years = [int(year) for year in rows[0][1:]]
    by_label = {row[0].strip(): [number(value) for value in row[1:]] for row in rows[1:] if row}
    table = {}
    for key, prefix in TABLE_ROWS.items():
        mean = next((values for label, values in by_label.items()
                     if label.startswith(prefix) and not label.endswith((" LB", " UB"))), None)
        low, high = by_label.get(f"{prefix} LB"), by_label.get(f"{prefix} UB")
        if not (mean and low and high) or not (len(mean) == len(low) == len(high) == len(years)):
            raise ValueError(f"tabla incompleta para {prefix}")
        table[key] = [[mean[i], low[i], high[i]] for i in range(len(years))]
    return years, table


def release_date(text: str) -> str:
    match = re.search(r"([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})", text)
    if not match or match.group(1) not in MONTHS:
        raise ValueError(f"fecha de publicación no reconocida: {text!r}")
    return f"{int(match.group(3)):04d}-{MONTHS[match.group(1)]:02d}-{int(match.group(2)):02d}"


def build(previous_file: dict | None) -> dict:
    release_text = fetch("updated.txt").strip()
    release = release_date(release_text)
    years, table = read_table(fetch("dsgeTableData.csv"))
    current = {"release": release, "years": years, "rows": table}
    previous = None
    if previous_file:
        old = previous_file.get("table", {})
        if old.get("current", {}).get("release") == release:
            previous = old.get("previous")
        else:
            previous = old.get("current")
    return {
        "model": "New York Fed DSGE model",
        "source": "Federal Reserve Bank of New York",
        "source_url": "https://www.newyorkfed.org/research/policy/dsge#/interactive",
        "posts_url": "https://libertystreeteconomics.newyorkfed.org/dsge-forecast/",
        "release": release,
        "release_text": release_text,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bands": BANDS,
        "table": {"band": 68, "current": current, "previous": previous},
        "fans": {key: read_fan(fetch(name)) for key, name in FANS.items()},
        "revisions": {key: read_revision(fetch(name)) for key, name in REVISIONS.items()},
    }


def main() -> int:
    existing = None
    if OUT.exists():
        try:
            existing = json.loads(OUT.read_text(encoding="utf-8"))
        except ValueError:
            existing = None
    try:
        data = build(existing)
    except Exception as error:  # noqa: BLE001 - conservar el archivo anterior ante cualquier fallo
        print(f"DSGE FRB-NY: no se pudo actualizar ({error}); se conserva el archivo anterior", file=sys.stderr)
        return 1
    if existing:
        same = {k: v for k, v in existing.items() if k != "fetched_at"} == {k: v for k, v in data.items() if k != "fetched_at"}
        if same:
            print(f"DSGE FRB-NY: sin cambios (publicación {data['release']})")
            return 0
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"DSGE FRB-NY: publicación {data['release']} guardada en {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
