"""Synchronize the monitoring workbooks from Google Drive."""

import argparse
import json
import logging
import math
import re
import tempfile
import time
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook

from drive_ingestion.spain_dashboard import build_site


ROOT_FOLDER = '1Ejg2KKXKKT1QOjTb0OZFcZ0y2vUry2cr'
FOLDERS = {'global': 'Global Scenarios', 'turkey': 'Turkiye', 'spain': 'Spain', 'usa': 'USA'}
MASTER_FILES = {'spain': 'excel_madre.xlsx', 'turkey': 'turkey_macro_master.xlsx'}
XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
FOLDER = 'application/vnd.google-apps.folder'
DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive.readonly'
DRIVE_FILES = 'https://www.googleapis.com/drive/v3/files'
METADATA_FIELDS = (
    'titulo_serie', 'subtitulo_descripcion', 'transformacion_y_calculo', 'fuente',
    'frecuencia_y_cobertura_temporal', 'tipo_grafico', 'bloque', 'área',
    'frecuencia', 'unidad',
)
ENGLISH_HEADERS = {
    'series_id': 'id_serie', 'series_title': 'titulo_serie',
    'subtitle_description': 'subtitulo_descripcion',
    'transformation_and_calculation': 'transformacion_y_calculo', 'source': 'fuente',
    'frequency_and_coverage': 'frecuencia_y_cobertura_temporal', 'chart_type': 'tipo_grafico',
    'block': 'bloque', 'area': 'área', 'frequency': 'frecuencia', 'unit': 'unidad',
    'date': 'fecha', 'value': 'valor',
}
ENGLISH_FREQUENCIES = {'Daily': 'Diaria', 'Weekly': 'Semanal', 'Monthly': 'Mensual', 'Quarterly': 'Trimestral'}
ENGLISH_AREAS = {
    'consumption': 'consumo', 'industry': 'industria', 'opinion_surveys': 'encuestas_opinión',
    'business_activity': 'actividad_empresarial', 'external_sector': 'sector_exterior',
}


class Drive:
    def __init__(self):
        import google.auth
        from google.auth.transport.requests import AuthorizedSession

        credentials, _ = google.auth.default(scopes=[DRIVE_SCOPE])
        self.session = AuthorizedSession(credentials)

    def children(self, parent, mime_type):
        params = {
            'q': f"'{parent}' in parents and trashed = false and mimeType = '{mime_type}'",
            'fields': 'nextPageToken,files(id,name,version)',
            'includeItemsFromAllDrives': 'true',
            'supportsAllDrives': 'true',
        }
        while True:
            response = self.session.get(DRIVE_FILES, params=params, timeout=30)
            response.raise_for_status()
            page = response.json()
            yield from page.get('files', [])
            if not page.get('nextPageToken'):
                break
            params['pageToken'] = page['nextPageToken']

    def download(self, file_id):
        response = self.session.get(
            f'{DRIVE_FILES}/{file_id}',
            params={'alt': 'media', 'supportsAllDrives': 'true'},
            timeout=120,
        )
        response.raise_for_status()
        return response.content


def worksheet_rows(workbook, name, required):
    if name not in workbook:
        raise ValueError(f'Missing worksheet {name}')
    rows = workbook[name].values
    headers = tuple(ENGLISH_HEADERS.get(field, field) for field in next(rows, ()))
    if missing := set(required) - set(headers):
        raise ValueError(f'{name}: missing columns {", ".join(sorted(missing))}')
    if duplicates := [field for field in required if headers.count(field) > 1]:
        raise ValueError(f'{name}: duplicate columns {", ".join(duplicates)}')
    for line, values in enumerate(rows, start=2):
        if any(value is not None for value in values):
            yield line, dict(zip(headers, values))


def parse_workbook(workbook_bytes):
    workbook = load_workbook(BytesIO(workbook_bytes), read_only=True, data_only=True)
    try:
        dictionary_name = 'DICTIONARY' if 'DICTIONARY' in workbook else 'DICCIONARIO'
        observations_name = 'LONG_DATA' if 'LONG_DATA' in workbook else 'DATOS_LARGO'
        series = {}
        for line, row in worksheet_rows(workbook, dictionary_name, ('id_serie', *METADATA_FIELDS)):
            series_id = row['id_serie']
            if not isinstance(series_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', series_id) or series_id in series:
                raise ValueError(f'{dictionary_name}:{line}: invalid or duplicate series ID')
            for field in ('titulo_serie', 'frecuencia', 'unidad'):
                if not isinstance(row[field], str) or not row[field].strip():
                    raise ValueError(f'{dictionary_name}:{line}: missing {field}')
            row['frecuencia'] = ENGLISH_FREQUENCIES.get(row['frecuencia'], row['frecuencia'])
            row['área'] = ENGLISH_AREAS.get(row['área'], row['área'])
            series[series_id] = {field: row[field] for field in METADATA_FIELDS}
            if isinstance(source_url := row.get('source_url'), str) and source_url.lower().startswith('https://'):
                series[series_id]['source_url'] = source_url
            series[series_id]['observaciones'] = {}

        for line, row in worksheet_rows(workbook, observations_name, ('id_serie', 'fecha', 'valor')):
            series_id, day, value = row['id_serie'], row['fecha'], row['valor']
            if series_id not in series:
                raise ValueError(f'{observations_name}:{line}: unknown series ID {series_id!r}')
            try:
                if isinstance(day, datetime):
                    day = day.date()
                if not isinstance(day, date):
                    day = date.fromisoformat(str(day))
            except ValueError as error:
                raise ValueError(f'{observations_name}:{line}: invalid date') from error
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f'{observations_name}:{line}: invalid number')
            observations = series[series_id]['observaciones']
            day = day.isoformat()
            if day in observations:
                raise ValueError(f'{observations_name}:{line}: duplicate date for {series_id!r}')
            observations[day] = value
    finally:
        workbook.close()

    if not series:
        raise ValueError('The workbook contains no series')
    for series_id, entry in series.items():
        if not entry['observaciones']:
            raise ValueError(f'No observations for {series_id!r}')
        entry['observaciones'] = sorted(entry['observaciones'].items())
    return series


def write_snapshot(output, source, series):
    with tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', dir=output.parent, prefix=output.stem, delete=False,
    ) as stream:
        temporary = Path(stream.name)
        try:
            json.dump({'origen': source, 'series': series}, stream, ensure_ascii=False, allow_nan=False)
            stream.write('\n')
            stream.close()
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)


def sync_area(drive, folder_id, output):
    files = list(drive.children(folder_id, XLSX))
    if not files:
        logging.info('%s: no Excel workbook in Drive', output.stem)
        return
    master = MASTER_FILES.get(output.stem)
    matches = [file for file in files if file['name'].strip().lower() == master] if master else files
    if len(matches) != 1:
        raise ValueError(f'Expected one {master or "Excel workbook"}, found {len(matches)}')
    source = matches[0]
    if output.is_file():
        with output.open(encoding='utf-8') as stream:
            if json.load(stream)['origen'] == source:
                logging.info('%s: up to date', output.stem)
                return

    series = parse_workbook(drive.download(source['id']))
    if output.stem == 'turkey':
        series = {key: entry for key, entry in series.items()
                  if not re.search(r'\bTurkey_example_data\.xlsx\b', str(entry.get('fuente') or ''), re.IGNORECASE)}
        if not series:
            logging.info('turkey: only example data in Drive; keeping the published snapshot')
            return
    write_snapshot(output, source, series)
    logging.info('%s: synchronized %d series', output.stem, len(series))


def sync(drive, directory):
    directory.mkdir(parents=True, exist_ok=True)
    folders = list(drive.children(ROOT_FOLDER, FOLDER))
    success = True
    for area, name in FOLDERS.items():
        try:
            matches = [item for item in folders if item['name'] == name]
            if not matches and area == 'usa':
                logging.info('usa: USA folder not created in Drive yet; skipping')
                continue
            if len(matches) != 1:
                raise ValueError(f'Expected exactly one {name!r} folder, found {len(matches)}')
            sync_area(drive, matches[0]['id'], directory / f'{area}.json')
        except Exception as error:
            logging.error('%s: %s', area, error)
            success = False
    return success


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='directory for processed JSON snapshots')
    parser.add_argument('--site', type=Path, help='generate a dashboard copy with Spain Drive series')
    parser.add_argument('--interval', type=int, default=0, help='seconds between polls (default: run once)')
    args = parser.parse_args()
    if args.interval < 0:
        parser.error('--interval must be zero or positive')
    if args.site:
        site, output = args.site.resolve(), args.output.resolve()
        if site == output or site in output.parents or output in site.parents:
            parser.error('--site and the snapshot output must be separate directories')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    drive = Drive()
    while True:
        try:
            success = sync(drive, args.output)
            snapshot = args.output / 'spain.json'
            if args.site and snapshot.is_file():
                build_site(snapshot, args.site)
        except Exception as error:
            logging.error('Google Drive: %s', error)
            success = False
        if not args.interval:
            return int(not success)
        time.sleep(args.interval)


if __name__ == '__main__':
    raise SystemExit(main())
