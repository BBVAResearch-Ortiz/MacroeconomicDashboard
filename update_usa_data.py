import csv
import io
import json
import os
import urllib.request
from datetime import datetime, timezone

OUT_PATH = os.path.join("drive_ingestion", "snapshots", "usa.json")

SERIES = [
    {"id": "GDPC1", "name": "Real GDP (BEA)", "source": "BEA / FRED", "unit": "Chained 2017 USD"},
    {"id": "CPIAUCSL", "name": "CPI All Urban Consumers (BLS)", "source": "BLS / FRED", "unit": "Index 1982-84=100"},
    {"id": "UNRATE", "name": "Unemployment Rate (BLS)", "source": "BLS / FRED", "unit": "%"},
    {"id": "PAYEMS", "name": "Nonfarm Payrolls (BLS)", "source": "BLS / FRED", "unit": "Thousands of Persons"},
    {"id": "FEDFUNDS", "name": "Federal Funds Effective Rate (FED)", "source": "Federal Reserve / FRED", "unit": "%"},
    {"id": "DGS10", "name": "10-Year Treasury Yield (FED)", "source": "Federal Reserve / FRED", "unit": "%"},
]


def fetch_fred_csv(series_id: str):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        text = resp.read().decode("utf-8")
    reader = csv.reader(io.StringIO(text))
    next(reader, None)
    rows = []
    for row in reader:
        if len(row) < 2:
            continue
        date_str, val_str = row[0].strip(), row[1].strip()
        if not date_str or val_str in ("", "."):
            continue
        try:
            rows.append((date_str, float(val_str)))
        except ValueError:
            continue
    return rows


def main():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    result_series = []

    for meta in SERIES:
        sid = meta["id"]
        try:
            obs = fetch_fred_csv(sid)
            tail = obs[-120:] if len(obs) > 120 else obs
            latest_date, latest_val = tail[-1] if tail else (None, None)
            prev_val = tail[-2][1] if len(tail) >= 2 else None
            change = round(latest_val - prev_val, 4) if (latest_val is not None and prev_val is not None) else None

            result_series.append({
                "id": sid,
                "name": meta["name"],
                "source": meta["source"],
                "unit": meta["unit"],
                "latest_date": latest_date,
                "latest_value": latest_val,
                "previous_change": change,
                "observations": [{"date": d, "value": v} for d, v in tail],
            })
            print(f"[OK] {sid}: {latest_val} ({latest_date})")
        except Exception as exc:
            print(f"[WARN] {sid}: {exc}")
            result_series.append({
                "id": sid,
                "name": meta["name"],
                "source": meta["source"],
                "unit": meta["unit"],
                "latest_date": None,
                "latest_value": None,
                "previous_change": None,
                "observations": [],
                "error": str(exc),
            })

    payload = {
        "country": "USA",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": ["FED", "BLS", "BEA"],
        "series": result_series,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print("Listo:", OUT_PATH)


if __name__ == "__main__":
    main()
