#!/usr/bin/env python3
"""Descarga el Inflation Nowcasting de la Fed de Cleveland y escribe inflation_nowcast.json.

Lee los tres JSON que alimentan los gráficos oficiales
(https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting):
nowcast mensual intermensual, mensual interanual y trimestral anualizado de
CPI, CPI subyacente, PCE y PCE subyacente, con su evolución diaria y el dato
publicado cuando existe. No ejecuta ningún modelo: solo copia lo publicado.

Los archivos originales pesan unos 20 MB; aquí se guardan los últimos meses y
trimestres completos y un historial resumido de nowcast final frente a dato.
Ante cualquier fallo se conserva el archivo anterior y el script termina con error.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/"
OUT = Path("inflation_nowcast.json")
MEASURES = {
    "CPI Inflation": "cpi",
    "Core CPI Inflation": "core_cpi",
    "PCE Inflation": "pce",
    "Core PCE Inflation": "core_pce",
}
MONTHS_KEPT = 6       # meses con evolución diaria completa
QUARTERS_KEPT = 3     # trimestres con evolución diaria completa
TRACK_MONTHS = 36     # meses en el historial de nowcast final frente a dato


def fetch(name: str) -> list:
    response = requests.get(BASE + name, params={"sc_lang": "en"}, timeout=120,
                            headers={"User-Agent": "MacroeconomicDashboard/1.0"})
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list) or not data:
        raise ValueError(f"{name}: formato inesperado")
    return data


def number(text):
    text = "" if text is None else str(text).strip()
    return round(float(text), 3) if text else None


def month_key(caption: str) -> str:
    year, month = caption.split("-")
    return f"{int(year):04d}-{int(month):02d}"


def quarter_key(caption: str) -> str:
    year, quarter = caption.split(":Q")
    return f"{int(year):04d}-Q{int(quarter)}"


def first_year(key: str) -> int:
    return int(key[:4])


def parse(entry: dict, key: str) -> dict:
    """Convierte un gráfico de la Fed en fechas ISO, series diarias, datos publicados y marcas."""
    labels, events, year, previous_month = [], [], first_year(key), None
    for category in entry["categories"][0]["category"]:
        label = str(category.get("label", "")).strip()
        if str(category.get("vline", "")).lower() == "true":
            events.append({"label": label, "after": len(labels) - 1})
            continue
        month, day = (int(part) for part in label.split("/"))
        if previous_month is not None and month < previous_month:
            year += 1
        previous_month = month
        labels.append(f"{year:04d}-{month:02d}-{day:02d}")
    series, actual = {}, {}
    for dataset in entry["dataset"]:
        name = str(dataset.get("seriesname", "")).strip()
        values = [number(point.get("value")) for point in dataset.get("data", [])]
        if len(values) > len(labels):
            raise ValueError(f"{key}: más valores que fechas en {name}")
        values += [None] * (len(labels) - len(values))
        if name.startswith("Actual "):
            measure = MEASURES.get(name[len("Actual "):])
            if measure:
                found = [(i, v) for i, v in enumerate(values) if v is not None]
                if found:
                    actual[measure] = {"value": found[0][1], "date": labels[found[0][0]]}
        elif name in MEASURES:
            series[MEASURES[name]] = values
    if set(series) != set(MEASURES.values()):
        raise ValueError(f"{key}: faltan series ({sorted(series)})")
    return {"period": key, "dates": labels, "nowcast": series, "actual": actual,
            "events": [{"label": e["label"], "date": labels[e["after"]]} for e in events if 0 <= e["after"] < len(labels)]}


def last_value(values):
    return next((value for value in reversed(values) if value is not None), None)


def build() -> dict:
    month_raw, year_raw, quarter_raw = fetch("nowcast_month.json"), fetch("nowcast_year.json"), fetch("nowcast_quarter.json")
    monthly = {month_key(e["chart"]["subcaption"]): e for e in month_raw}
    yearly = {month_key(e["chart"]["subcaption"]): e for e in year_raw}
    quarterly = {quarter_key(e["chart"]["subcaption"]): e for e in quarter_raw}
    month_keys = sorted(set(monthly) & set(yearly))
    if not month_keys or not quarterly:
        raise ValueError("no hay periodos comunes")

    months = []
    for key in month_keys[-MONTHS_KEPT:]:
        mm, yy = parse(monthly[key], key), parse(yearly[key], key)
        months.append({"period": key, "mm": mm, "yy": yy})
    quarters = [parse(quarterly[key], key) for key in sorted(quarterly)[-QUARTERS_KEPT:]]

    track = []
    for key in month_keys[-TRACK_MONTHS:]:
        row = {"period": key}
        for kind, source in (("mm", monthly), ("yy", yearly)):
            parsed = parse(source[key], key)
            row[kind] = {measure: {"nowcast": last_value(values), "actual": parsed["actual"].get(measure, {}).get("value")}
                         for measure, values in parsed["nowcast"].items()}
        track.append(row)

    updated = str(month_raw[-1]["chart"].get("_comment", "")).strip()[:10]
    datetime.strptime(updated, "%Y-%m-%d")
    return {
        "model": "Cleveland Fed Inflation Nowcasting",
        "source": "Federal Reserve Bank of Cleveland",
        "source_url": "https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting",
        "updated": updated,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "measures": list(MEASURES.values()),
        "months": months,
        "quarters": quarters,
        "track": track,
    }


def main() -> int:
    try:
        data = build()
    except Exception as error:  # noqa: BLE001 - conservar el archivo anterior ante cualquier fallo
        print(f"Inflation Nowcasting: no se pudo actualizar ({error}); se conserva el archivo anterior", file=sys.stderr)
        return 1
    if OUT.exists():
        try:
            existing = json.loads(OUT.read_text(encoding="utf-8"))
            if {k: v for k, v in existing.items() if k != "fetched_at"} == {k: v for k, v in data.items() if k != "fetched_at"}:
                print(f"Inflation Nowcasting: sin cambios (actualización {data['updated']})")
                return 0
        except ValueError:
            pass
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Inflation Nowcasting: actualización {data['updated']} guardada en {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
