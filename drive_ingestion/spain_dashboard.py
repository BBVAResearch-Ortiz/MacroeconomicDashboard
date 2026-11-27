"""Build a copy of the dashboard with Spain's Drive series in the Blackboard."""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from group_workbooks import spain_group


ROOT = Path(__file__).resolve().parent.parent
FREQUENCIES = {'Diaria': 'D', 'Mensual': 'M', 'Trimestral': 'Q', 'D': 'D', 'M': 'M', 'Q': 'Q'}
SITE_FILES = (
    'index.html', 'pais.html', 'summary.html', 'usa.html', 'i18n.js', 'bbva-research-logo.png', 'series_transforms.js',
    'bigdata.json', 'bigdata_heatmap.json', 'forecasts.json', 'frbus_resultados.json',
    'gdpnow.json', 'gdpnow_tracking.json', 'dsge_frbny.json', 'dsge_irf.json', 'inflation_nowcast.json',
)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def merge_series(base, imported):
    for source_id, entry in imported.items():
        series_id = f'drive_es_{source_id}'
        if series_id in base['series']:
            raise ValueError(f'Duplicate dashboard series ID: {series_id}')
        frequency = FREQUENCIES.get(entry['frecuencia'])
        if not frequency:
            raise ValueError(f'{source_id}: unsupported dashboard frequency {entry["frecuencia"]!r}')
        base['series'][series_id] = {
            'label': entry['titulo_serie'],
            'unit': entry['unidad'],
            'freq': frequency,
            'block': spain_group(entry.get('bloque'), entry.get('área')),
            'family': entry.get('bloque'),
            'areaLabel': entry['área'].strip(),
            'source': re.split(r' \| (?:Archivo interno|Internal file):',
                               entry['fuente'] or 'Google Drive', maxsplit=1)[0],
            'code': source_id,
            'link': entry.get('source_url'),
            'translations': entry.get('translations'),
            'original_name': entry['subtitulo_descripcion'],
            'transform': entry['transformacion_y_calculo'],
            'data': [[day, value, 0] for day, value in entry['observaciones']],
        }
    base['meta']['n_series'] = len(base['series'])
    return base


def build_site(snapshot, destination):
    destination = destination.resolve()
    if destination == ROOT or destination in ROOT.parents:
        raise ValueError('Choose a dashboard output directory separate from the repository root')
    data = merge_series(read_json(ROOT / 'data.json'), read_json(snapshot)['series'])
    destination.mkdir(parents=True, exist_ok=True)
    staging = destination / f'.build-{uuid4().hex}'
    staging.mkdir()
    try:
        for name in (*SITE_FILES, 'template.html', 'template_spain_turkey.html'):
            shutil.copyfile(ROOT / name, staging / name)
        (staging / 'data.json').write_text(
            json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(',', ':')),
            encoding='utf-8',
        )
        subprocess.run([sys.executable, str(ROOT / 'build_page.py')], cwd=staging, check=True)
        for name in (*SITE_FILES, 'data.json', 'espana.html', 'artifact.html', 'turquia.html'):
            (staging / name).replace(destination / name)
        for name in ('turkey.json', 'turkey-verified.json', 'usa.json'):
            snapshot_path = Path('drive_ingestion/snapshots') / name
            if (ROOT / snapshot_path).is_file():
                (destination / snapshot_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / snapshot_path, destination / snapshot_path)
    finally:
        shutil.rmtree(staging)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    build_site(args.snapshot, args.destination)
