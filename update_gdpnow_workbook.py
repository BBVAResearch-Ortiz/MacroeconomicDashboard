"""Extract the current-quarter GDPNow tracking series from Atlanta Fed's workbook."""
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
import json, re, sys
import openpyxl
from urllib.request import Request, urlopen

URL = 'https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/research-and-data/data/gdpnow/GDPTrackingModelDataAndForecasts.xlsx'
OUT = Path(__file__).resolve().parent / 'gdpnow_tracking.json'

def extract(source):
    book = openpyxl.load_workbook(source, read_only=True, data_only=True)
    try:
        history = book['TrackingHistory']
        heading = str(history.cell(2, 1).value or '')
        quarter = re.search(r'(20\d{2})\s*q([1-4])', heading, re.I)
        if not quarter:
            raise ValueError('Trimestre no reconocido en TrackingHistory')
        points = []
        for d, release, value in book['CurrentQtrEvolution'].iter_rows(min_row=2, max_col=3, values_only=True):
            if isinstance(d, (datetime, date)) and isinstance(value, (int, float)) and not isinstance(value, bool) and -100 < value < 100:
                points.append({'date': d.isoformat()[:10], 'value': round(value, 6), 'release': str(release or '')})
        points.sort(key=lambda x:x['date'])
        if not points or len({p['date'] for p in points}) != len(points):
            raise ValueError('Evolución vacía o fechas duplicadas')
        return {'quarter': f'{quarter.group(1)}-Q{quarter.group(2)}', 'updated_at':points[-1]['date'], 'observations':points, 'source_url':URL}
    finally:
        book.close()

def main():
    if len(sys.argv) > 1:
        source = sys.argv[1]
    else:
        with urlopen(Request(URL, headers={'User-Agent':'Macroeconomic-Dashboard/1.0'}), timeout=90) as response:
            source = BytesIO(response.read())
    result = extract(source)
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding='utf-8'))
        if result['updated_at'] < old.get('updated_at',''):
            raise ValueError('El libro contiene datos anteriores a los guardados')
    temp = OUT.with_suffix('.tmp')
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temp.replace(OUT)
    print('GDPNow evolución:',result['quarter'],result['updated_at'],len(result['observations']),'observaciones')

if __name__ == '__main__':
    try: main()
    except Exception as exc:
        print('No se ha actualizado GDPNow; se conservan los datos anteriores:', exc, file=sys.stderr)
        sys.exit(1)
