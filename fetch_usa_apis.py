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
        "bloque": "monetario",
        "fuente": "Federal Reserve / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "FEDFUNDS",
    },
    "DGS2": {
        "titulo_serie": "2-Year Treasury Yield (FED)",
        "subtitulo_descripcion": "Market Yield on U.S. Treasury Securities at 2-Year Constant Maturity",
        "unidad": "%",
        "frecuencia": "D",
        "bloque": "monetario",
        "fuente": "Federal Reserve / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "DGS2",
    },
    "DGS10": {
        "titulo_serie": "10-Year Treasury Yield (FED)",
        "subtitulo_descripcion": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity",
        "unidad": "%",
        "frecuencia": "D",
        "bloque": "monetario",
        "fuente": "Federal Reserve / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "DGS10",
    },
    "PCEC96": {
        "titulo_serie": "Real Personal Consumption Expenditures (BEA)",
        "subtitulo_descripcion": "Real Personal Consumption Expenditures",
        "unidad": "Billions of chained 2017 USD",
        "frecuencia": "M",
        "bloque": "actividad",
        "fuente": "BEA / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "PCEC96",
    },
    "RSAFS": {
        "titulo_serie": "Retail Sales (Census)",
        "subtitulo_descripcion": "Advance Retail Sales: Retail Trade and Food Services",
        "unidad": "Millions of USD",
        "frecuencia": "M",
        "bloque": "actividad",
        "fuente": "Census Bureau / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "RSAFS",
    },
    "TCU": {
        "titulo_serie": "Capacity Utilization (FED)",
        "subtitulo_descripcion": "Capacity Utilization: Total Index",
        "unidad": "%",
        "frecuencia": "M",
        "bloque": "actividad",
        "fuente": "Federal Reserve / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "TCU",
    },
    "DGORDER": {
        "titulo_serie": "Durable Goods Orders (Census)",
        "subtitulo_descripcion": "Manufacturers' New Orders: Durable Goods",
        "unidad": "Millions of USD",
        "frecuencia": "M",
        "bloque": "actividad",
        "fuente": "Census Bureau / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "DGORDER",
    },
    "UMCSENT": {
        "titulo_serie": "Consumer Sentiment (UMich)",
        "subtitulo_descripcion": "University of Michigan: Consumer Sentiment",
        "unidad": "Index 1966Q1=100",
        "frecuencia": "M",
        "bloque": "actividad",
        "fuente": "University of Michigan / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "UMCSENT",
    },
    "CFNAI": {
        "titulo_serie": "Chicago Fed National Activity Index (Chicago Fed)",
        "subtitulo_descripcion": "Chicago Fed National Activity Index",
        "unidad": "Index",
        "frecuencia": "M",
        "bloque": "actividad",
        "fuente": "Chicago Fed / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "CFNAI",
    },
    "CIVPART": {
        "titulo_serie": "Labor Force Participation Rate (BLS)",
        "subtitulo_descripcion": "Labor Force Participation Rate",
        "unidad": "%",
        "frecuencia": "M",
        "bloque": "empleo",
        "fuente": "BLS / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "CIVPART",
    },
    "U6RATE": {
        "titulo_serie": "U-6 Unemployment Rate (BLS)",
        "subtitulo_descripcion": "Total Unemployed, Plus Marginally Attached, Plus Part Time for Economic Reasons (U-6)",
        "unidad": "%",
        "frecuencia": "M",
        "bloque": "empleo",
        "fuente": "BLS / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "U6RATE",
    },
    "JTSJOL": {
        "titulo_serie": "Job Openings (BLS)",
        "subtitulo_descripcion": "Job Openings: Total Nonfarm",
        "unidad": "Thousands",
        "frecuencia": "M",
        "bloque": "empleo",
        "fuente": "BLS / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "JTSJOL",
    },
    "CES0500000003": {
        "titulo_serie": "Average Hourly Earnings (BLS)",
        "subtitulo_descripcion": "Average Hourly Earnings of All Employees, Total Private",
        "unidad": "USD per hour",
        "frecuencia": "M",
        "bloque": "empleo",
        "fuente": "BLS / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "CES0500000003",
    },
    "CCSA": {
        "titulo_serie": "Continued Jobless Claims (DOL / ETA)",
        "subtitulo_descripcion": "Continued Claims (Insured Unemployment)",
        "unidad": "Personas",
        "frecuencia": "W",
        "bloque": "empleo",
        "fuente": "DOL / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "CCSA",
    },
    "PCEPI": {
        "titulo_serie": "PCE Price Index (BEA)",
        "subtitulo_descripcion": "Personal Consumption Expenditures: Chain-type Price Index",
        "unidad": "Index 2017=100",
        "frecuencia": "M",
        "bloque": "precios",
        "fuente": "BEA / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "PCEPI",
    },
    "PCEPILFE": {
        "titulo_serie": "Core PCE Price Index (BEA)",
        "subtitulo_descripcion": "Personal Consumption Expenditures Excluding Food and Energy (Chain-Type Price Index)",
        "unidad": "Index 2017=100",
        "frecuencia": "M",
        "bloque": "precios",
        "fuente": "BEA / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "PCEPILFE",
    },
    "PPIFIS": {
        "titulo_serie": "PPI Final Demand (BLS)",
        "subtitulo_descripcion": "Producer Price Index by Commodity: Final Demand",
        "unidad": "Index Nov 2009=100",
        "frecuencia": "M",
        "bloque": "precios",
        "fuente": "BLS / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "PPIFIS",
    },
    "MICH": {
        "titulo_serie": "Inflation Expectations 1-Year (UMich)",
        "subtitulo_descripcion": "University of Michigan: Inflation Expectation",
        "unidad": "%",
        "frecuencia": "M",
        "bloque": "precios",
        "fuente": "University of Michigan / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "MICH",
    },
    "T5YIE": {
        "titulo_serie": "5-Year Breakeven Inflation (FRED)",
        "subtitulo_descripcion": "5-Year Breakeven Inflation Rate",
        "unidad": "%",
        "frecuencia": "D",
        "bloque": "precios",
        "fuente": "St. Louis Fed / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "T5YIE",
    },
    "DCOILWTICO": {
        "titulo_serie": "WTI Crude Oil Price (EIA)",
        "subtitulo_descripcion": "Crude Oil Prices: West Texas Intermediate (WTI) - Cushing, Oklahoma",
        "unidad": "USD per barrel",
        "frecuencia": "D",
        "bloque": "precios",
        "fuente": "EIA / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "DCOILWTICO",
    },
    "DFEDTARU": {
        "titulo_serie": "Fed Funds Target Upper Limit (FED)",
        "subtitulo_descripcion": "Federal Funds Target Range - Upper Limit",
        "unidad": "%",
        "frecuencia": "D",
        "bloque": "monetario",
        "fuente": "Federal Reserve / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "DFEDTARU",
    },
    "T10Y2Y": {
        "titulo_serie": "10-Year minus 2-Year Treasury Spread (FRED)",
        "subtitulo_descripcion": "10-Year Treasury Constant Maturity Minus 2-Year Treasury Constant Maturity",
        "unidad": "%",
        "frecuencia": "D",
        "bloque": "monetario",
        "fuente": "St. Louis Fed / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "T10Y2Y",
    },
    "M2SL": {
        "titulo_serie": "M2 Money Stock (FED)",
        "subtitulo_descripcion": "M2",
        "unidad": "Billions of USD",
        "frecuencia": "M",
        "bloque": "monetario",
        "fuente": "Federal Reserve / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "M2SL",
    },
    "WALCL": {
        "titulo_serie": "Fed Total Assets (FED)",
        "subtitulo_descripcion": "Assets: Total Assets (Less Eliminations from Consolidation): Wednesday Level",
        "unidad": "Millions of USD",
        "frecuencia": "W",
        "bloque": "monetario",
        "fuente": "Federal Reserve / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "WALCL",
    },
    "SP500": {
        "titulo_serie": "S&P 500 (S&P)",
        "subtitulo_descripcion": "S&P 500",
        "unidad": "Index",
        "frecuencia": "D",
        "bloque": "financiero",
        "fuente": "S&P Dow Jones Indices / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "SP500",
    },
    "VIXCLS": {
        "titulo_serie": "VIX Volatility Index (CBOE)",
        "subtitulo_descripcion": "CBOE Volatility Index: VIX",
        "unidad": "Index",
        "frecuencia": "D",
        "bloque": "financiero",
        "fuente": "CBOE / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "VIXCLS",
    },
    "BAA10Y": {
        "titulo_serie": "Baa Corporate Spread over 10-Year Treasury (FRED)",
        "subtitulo_descripcion": "Moody's Seasoned Baa Corporate Bond Yield Relative to Yield on 10-Year Treasury Constant Maturity",
        "unidad": "%",
        "frecuencia": "D",
        "bloque": "financiero",
        "fuente": "St. Louis Fed / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "BAA10Y",
    },
    "NFCI": {
        "titulo_serie": "National Financial Conditions Index (Chicago Fed)",
        "subtitulo_descripcion": "Chicago Fed National Financial Conditions Index",
        "unidad": "Index",
        "frecuencia": "W",
        "bloque": "financiero",
        "fuente": "Chicago Fed / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "NFCI",
    },
    "MORTGAGE30US": {
        "titulo_serie": "30-Year Mortgage Rate (Freddie Mac)",
        "subtitulo_descripcion": "30-Year Fixed Rate Mortgage Average in the United States",
        "unidad": "%",
        "frecuencia": "W",
        "bloque": "financiero",
        "fuente": "Freddie Mac / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "MORTGAGE30US",
    },
    "DTWEXBGS": {
        "titulo_serie": "Broad Dollar Index (FED)",
        "subtitulo_descripcion": "Nominal Broad U.S. Dollar Index",
        "unidad": "Index Jan 2006=100",
        "frecuencia": "D",
        "bloque": "financiero",
        "fuente": "Federal Reserve / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "DTWEXBGS",
    },
    "MTSDS133FMS": {
        "titulo_serie": "Federal Surplus or Deficit (Treasury)",
        "subtitulo_descripcion": "Federal Surplus or Deficit [-]",
        "unidad": "Millions of USD",
        "frecuencia": "M",
        "bloque": "fiscal",
        "fuente": "U.S. Treasury / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "MTSDS133FMS",
    },
    "GFDEBTN": {
        "titulo_serie": "Federal Debt (Treasury)",
        "subtitulo_descripcion": "Federal Debt: Total Public Debt",
        "unidad": "Millions of USD",
        "frecuencia": "Q",
        "bloque": "fiscal",
        "fuente": "U.S. Treasury / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "GFDEBTN",
    },
    "GFDEGDQ188S": {
        "titulo_serie": "Federal Debt to GDP (OMB)",
        "subtitulo_descripcion": "Federal Debt: Total Public Debt as Percent of Gross Domestic Product",
        "unidad": "% of GDP",
        "frecuencia": "Q",
        "bloque": "fiscal",
        "fuente": "OMB / FRED",
        "transformacion_y_calculo": "Tasa (%)",
        "fred_id": "GFDEGDQ188S",
    },
    "W006RC1Q027SBEA": {
        "titulo_serie": "Federal Tax Receipts (BEA)",
        "subtitulo_descripcion": "Federal government current tax receipts",
        "unidad": "Billions of USD, annual rate",
        "frecuencia": "Q",
        "bloque": "fiscal",
        "fuente": "BEA / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "W006RC1Q027SBEA",
    },
    "FGEXPND": {
        "titulo_serie": "Federal Current Expenditures (BEA)",
        "subtitulo_descripcion": "Federal Government: Current Expenditures",
        "unidad": "Billions of USD, annual rate",
        "frecuencia": "Q",
        "bloque": "fiscal",
        "fuente": "BEA / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "FGEXPND",
    },
    "A091RC1Q027SBEA": {
        "titulo_serie": "Federal Interest Payments (BEA)",
        "subtitulo_descripcion": "Federal government current expenditures: Interest payments",
        "unidad": "Billions of USD, annual rate",
        "frecuencia": "Q",
        "bloque": "fiscal",
        "fuente": "BEA / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "A091RC1Q027SBEA",
    },
    "BOPGSTB": {
        "titulo_serie": "Trade Balance Goods and Services (Census)",
        "subtitulo_descripcion": "Trade Balance: Goods and Services, Balance of Payments Basis",
        "unidad": "Millions of USD",
        "frecuencia": "M",
        "bloque": "exterior",
        "fuente": "Census Bureau / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "BOPGSTB",
    },
    "BOPTEXP": {
        "titulo_serie": "Exports of Goods and Services (Census)",
        "subtitulo_descripcion": "Exports of Goods and Services: Balance of Payments Basis",
        "unidad": "Millions of USD",
        "frecuencia": "M",
        "bloque": "exterior",
        "fuente": "Census Bureau / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "BOPTEXP",
    },
    "BOPTIMP": {
        "titulo_serie": "Imports of Goods and Services (Census)",
        "subtitulo_descripcion": "Imports of Goods and Services: Balance of Payments Basis",
        "unidad": "Millions of USD",
        "frecuencia": "M",
        "bloque": "exterior",
        "fuente": "Census Bureau / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "BOPTIMP",
    },
    "IEABC": {
        "titulo_serie": "Current Account Balance (BEA)",
        "subtitulo_descripcion": "Balance on current account",
        "unidad": "Millions of USD",
        "frecuencia": "Q",
        "bloque": "exterior",
        "fuente": "BEA / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "IEABC",
    },
    "DEXUSEU": {
        "titulo_serie": "USD per Euro Exchange Rate (FED)",
        "subtitulo_descripcion": "U.S. Dollars to Euro Spot Exchange Rate",
        "unidad": "USD per EUR",
        "frecuencia": "D",
        "bloque": "exterior",
        "fuente": "Federal Reserve / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "DEXUSEU",
    },
    "HOUST": {
        "titulo_serie": "Housing Starts (Census)",
        "subtitulo_descripcion": "New Privately-Owned Housing Units Started: Total Units",
        "unidad": "Thousands of units, annual rate",
        "frecuencia": "M",
        "bloque": "vivienda",
        "fuente": "Census Bureau / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "HOUST",
    },
    "PERMIT": {
        "titulo_serie": "Building Permits (Census)",
        "subtitulo_descripcion": "New Privately-Owned Housing Units Authorized in Permit-Issuing Places: Total Units",
        "unidad": "Thousands of units, annual rate",
        "frecuencia": "M",
        "bloque": "vivienda",
        "fuente": "Census Bureau / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "PERMIT",
    },
    "HSN1F": {
        "titulo_serie": "New Home Sales (Census)",
        "subtitulo_descripcion": "New One Family Houses Sold: United States",
        "unidad": "Thousands, annual rate",
        "frecuencia": "M",
        "bloque": "vivienda",
        "fuente": "Census Bureau / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "HSN1F",
    },
    "EXHOSLUSM495S": {
        "titulo_serie": "Existing Home Sales (NAR)",
        "subtitulo_descripcion": "Existing Home Sales",
        "unidad": "Units, annual rate",
        "frecuencia": "M",
        "bloque": "vivienda",
        "fuente": "National Association of Realtors / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "EXHOSLUSM495S",
    },
    "CSUSHPISA": {
        "titulo_serie": "Case-Shiller Home Price Index (S&P)",
        "subtitulo_descripcion": "S&P Cotality Case-Shiller U.S. National Home Price Index",
        "unidad": "Index Jan 2000=100",
        "frecuencia": "M",
        "bloque": "vivienda",
        "fuente": "S&P Dow Jones Indices / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "CSUSHPISA",
    },
    "MSPUS": {
        "titulo_serie": "Median New Home Sales Price (Census)",
        "subtitulo_descripcion": "Median Sales Price of Houses Sold for the United States",
        "unidad": "USD",
        "frecuencia": "Q",
        "bloque": "vivienda",
        "fuente": "Census Bureau / FRED",
        "transformacion_y_calculo": "Nivel original",
        "fred_id": "MSPUS",
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
    try:
        data = http_get_json(url)
        tables = data.get("BEAAPI", {}).get("Results", {}).get("ParamValue", [])
        print(f"[BEA API] Conexión OK ({len(tables)} tablas NIPA disponibles)", flush=True)
    except Exception as exc:
        print(f"[WARN] BEA API no disponible temporalmente: {exc}", flush=True)


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
