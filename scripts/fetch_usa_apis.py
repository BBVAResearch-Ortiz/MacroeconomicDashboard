import csv
import io
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

OUT_PATH = os.environ.get("USA_JSON_PATH", "usa.json")
SNAPSHOT_PATH = os.path.join("drive_ingestion", "snapshots", "usa.json")

FRED_API_KEY = os.environ.get("FRED_API_KEY", "").strip()
BEA_API_KEY = os.environ.get("BEA_API_KEY", "").strip()
BLS_API_KEY = os.environ.get("BLS_API_KEY", "").strip()

SERIES_CONFIG = {
    "GDPC1": {
        "titulo_serie": "Real GDP (BEA)",
        "subtitulo_descripcion": "Real Gross Domestic Product",
        "unidad": "Chained 2017 USD",
        "frecuencia": "Q",
        "bloque": "actividad",
        "fuente": "BEA / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "GDPC1",
    },
    "PCE": {
        "titulo_serie": "Personal Consumption Expenditures (BEA)",
        "subtitulo_descripcion": "Personal Consumption Expenditures",
        "unidad": "Billions of USD",
        "frecuencia": "M",
        "bloque": "actividad",
        "fuente": "BEA / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "PCE",
    },
    "INDPRO": {
        "titulo_serie": "Industrial Production Index (FED)",
        "subtitulo_descripcion": "Industrial Production: Total Index",
        "unidad": "Index 2017=100",
        "frecuencia": "M",
        "bloque": "actividad",
        "fuente": "Federal Reserve / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "INDPRO",
    },
    "CPIAUCSL": {
        "titulo_serie": "CPI All Urban Consumers (BLS)",
        "subtitulo_descripcion": "Consumer Price Index for All Urban Consumers: All Items",
        "unidad": "Index 1982-84=100",
        "frecuencia": "M",
        "bloque": "precios",
        "fuente": "BLS / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "CPIAUCSL",
    },
    "CPILFESL": {
        "titulo_serie": "Core CPI All Items Less Food & Energy (BLS)",
        "subtitulo_descripcion": "Consumer Price Index for All Urban Consumers: All Items Less Food and Energy",
        "unidad": "Index 1982-84=100",
        "frecuencia": "M",
        "bloque": "precios",
        "fuente": "BLS / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "CPILFESL",
    },
    "UNRATE": {
        "titulo_serie": "Unemployment Rate (BLS)",
        "subtitulo_descripcion": "Unemployment Rate",
        "unidad": "%",
        "frecuencia": "M",
        "bloque": "empleo",
        "fuente": "BLS / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "UNRATE",
    },
    "PAYEMS": {
        "titulo_serie": "Nonfarm Payrolls (BLS)",
        "subtitulo_descripcion": "All Employees, Total Nonfarm",
        "unidad": "Miles de personas",
        "frecuencia": "M",
        "bloque": "empleo",
        "fuente": "BLS / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "PAYEMS",
    },
    "ICSA": {
        "titulo_serie": "Initial Jobless Claims (DOL / ETA)",
        "subtitulo_descripcion": "Initial Claims",
        "unidad": "Personas",
        "frecuencia": "W",
        "bloque": "empleo",
        "fuente": "DOL / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "ICSA",
    },
    "FEDFUNDS": {
        "titulo_serie": "Federal Funds Effective Rate (FED)",
        "subtitulo_descripcion": "Federal Funds Effective Rate",
        "unidad": "%",
        "frecuencia": "M",
        "bloque": "tipos",
        "fuente": "Federal Reserve / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "FEDFUNDS",
    },
    "DGS2": {
        "titulo_serie": "2-Year Treasury Yield (FED)",
        "subtitulo_descripcion": "Market Yield on U.S. Treasury Securities at 2-Year Constant Maturity",
        "unidad": "%",
        "frecuencia": "D",
        "bloque": "tipos",
        "fuente": "Federal Reserve / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "DGS2",
    },
    "DGS10": {
        "titulo_serie": "10-Year Treasury Yield (FED)",
        "subtitulo_descripcion": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity",
        "unidad": "%",
        "frecuencia": "D",
        "bloque": "tipos",
        "fuente": "Federal Reserve / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "DGS10",
    },
}


def http_get_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "Macroeconomic-Dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_fred_series(series_id: str):
    if FRED_API_KEY:
        params = urllib.parse.urlencode({
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
        })
        url = f"https://api.stlouisfed.org/fred/series/observations?{params}"
        raw = http_get_json(url)
        obs = []
        for item in raw.get("observations", []):
            d = str(item.get("date", "")).strip()
            v = str(item.get("value", "")).strip()
            if not d or v in ("", "."):
                continue
            try:
                obs.append([d, float(v)])
            except ValueError:
                continue
        return obs

    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={urllib.parse.quote(series_id)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    next(reader, None)
    obs = []
    for row in reader:
        if len(row) < 2:
            continue
        d, v = row[0].strip(), row[1].strip()
        if not d or v in ("", "."):
            continue
        try:
            obs.append([d, float(v)])
        except ValueError:
            continue
    return obs


def check_bea_api():
    if not BEA_API_KEY:
        print("[INFO] BEA_API_KEY no configurada todavía", flush=True)
        return
    params = urllib.parse.urlencode({
        "UserID": BEA_API_KEY,
        "method": "GetParameterValues",
        "DataSetName": "NIPA",
        "ParameterName": "TableName",
        "ResultFormat": "JSON",
    })
    url = f"https://apps.bea.gov/api/data?{params}"
    data = http_get_json(url)
    tables = data.get("BEAAPI", {}).get("Results", {}).get("ParamValue", [])
    print(f"[BEA API] Conexión OK ({len(tables)} tablas NIPA disponibles)", flush=True)


def main():
    check_bea_api()

    out_series = {}
    for code, cfg in SERIES_CONFIG.items():
        try:
            obs = fetch_fred_series(cfg["fred_id"])
        except Exception as exc:
            print(f"[WARN] {code}: {exc}", flush=True)
            continue

        if not obs:
            print(f"[WARN] {code}: sin observaciones", flush=True)
            continue

        out_series[code] = {
            "titulo_serie": cfg["titulo_serie"],
            "subtitulo_descripcion": cfg["subtitulo_descripcion"],
            "unidad": cfg["unidad"],
            "frecuencia": cfg["frecuencia"],
            "bloque": cfg["bloque"],
            "fuente": cfg["fuente"],
            "transformacion_y_calculo": cfg["transformacion_y_calculo"],
            "observaciones": obs,
        }
        print(f"[OK] {code}: {len(obs)} obs ({obs[0][0]} -> {obs[-1][0]})", flush=True)

    payload = {
        "country": "USA",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": ["FRED", "BEA", "BLS"],
        "series": out_series,
    }

    for target in {OUT_PATH, SNAPSHOT_PATH}:
        parent = os.path.dirname(target)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        print(f"[SAVED] {target}", flush=True)


if __name__ == "__main__":
    main()
