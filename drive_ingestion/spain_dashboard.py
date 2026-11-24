"""Build a copy of the dashboard with Spain's Drive series in the Blackboard."""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parent.parent
FREQUENCIES = {'Diaria': 'D', 'Mensual': 'M', 'Trimestral': 'Q', 'D': 'D', 'M': 'M', 'Q': 'Q'}
BLOCKS = {
    'actividad_empresarial': 'coyuntura',
    'industria': 'coyuntura',
    'encuestas_opinión': 'coyuntura',
    'consumo': 'coyuntura',
    'sector_exterior': 'exterior',
}
SITE_FILES = (
    'index.html', 'pais.html', 'usa.html', 'i18n.js', 'bbva-research-logo.png',
    'bigdata.json', 'bigdata_heatmap.json', 'forecasts.json', 'frbus_resultados.json',
    'gdpnow.json', 'gdpnow_tracking.json',
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
            'block': BLOCKS.get(entry['área'], 'actividad'),
            'source': re.split(r' \| (?:Archivo interno|Internal file):',
                               entry['fuente'] or 'Google Drive', maxsplit=1)[0],
            'code': source_id,
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
        for name in (*SITE_FILES, 'template.html'):
            shutil.copyfile(ROOT / name, staging / name)
        (staging / 'data.json').write_text(
            json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(',', ':')),
            encoding='utf-8',
        )
        subprocess.run([sys.executable, str(ROOT / 'build_page.py')], cwd=staging, check=True)
        for name in (*SITE_FILES, 'data.json', 'espana.html', 'artifact.html'):
            (staging / name).replace(destination / name)
    finally:
        shutil.rmtree(staging)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    build_site(args.snapshot, args.destination)
