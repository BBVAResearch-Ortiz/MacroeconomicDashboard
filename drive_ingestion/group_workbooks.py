"""Add the dashboard group to the dictionary and coverage sheets of a master workbook."""

import argparse
from pathlib import Path

TURKEY_GROUPS = {
    'LABOUR_MARKET': 'empleo',
    'INFLATION': 'precios',
    'INTEREST_RATES': 'monetario',
    'BANKING': 'financiero',
    'FINANCIAL': 'financiero',
    'TREASURY_CASH': 'fiscal',
    'CENTRAL_GOVERNMENT_BUDGET': 'fiscal',
    'PUBLIC_SECTOR': 'fiscal',
    'BALANCE_OF_PAYMENTS': 'exterior',
    'EXTERNAL_TRADE': 'exterior',
    'TUIK_TRADE': 'exterior',
    'EXTERNAL_SECTOR': 'exterior',
    'TRADE_BALANCE': 'exterior',
    'HOUSING': 'vivienda',
}


def spain_group(block, area):
    external = area in ('sector_exterior', 'external_sector') or block in (
        'TRADE_BALANCE', 'BAL_COM', 'EXTERNAL_SECTOR', 'exterior',
    )
    return 'exterior' if external else 'actividad'


def group_workbook(path, country):
    from openpyxl import load_workbook

    workbook = load_workbook(path)
    groups = {}
    changed = False
    for name in ('DICTIONARY', 'DICCIONARIO', 'COVERAGE', 'COBERTURA'):
        if name not in workbook:
            continue
        sheet = workbook[name]
        columns = {cell.value: cell.column for cell in sheet[1] if cell.value}
        id_column = columns.get('series_id', columns.get('id_serie'))
        block_column = columns.get('block', columns.get('bloque'))
        area_column = columns.get('area', columns.get('área'))
        if not id_column or not block_column:
            continue
        group_column = columns.get('grupo', sheet.max_column + 1)
        sheet.cell(1, group_column, 'grupo')
        for row in range(2, sheet.max_row + 1):
            series_id = sheet.cell(row, id_column).value
            if not series_id:
                continue
            if series_id not in groups:
                block = sheet.cell(row, block_column).value
                area = sheet.cell(row, area_column).value if area_column else None
                groups[series_id] = (spain_group(block, area) if country == 'spain'
                                     else TURKEY_GROUPS.get(block, 'actividad'))
            cell = sheet.cell(row, group_column)
            if cell.value != groups[series_id]:
                cell.value = groups[series_id]
                changed = True
    if not groups:
        raise ValueError(f'{path}: no dictionary or coverage rows found')
    if changed:
        temporary = path.with_name(f'.{path.stem}.grouped.xlsx')
        try:
            workbook.save(temporary)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    workbook.close()
    return groups


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('country', choices=('spain', 'turkey'))
    parser.add_argument('workbooks', nargs='+', type=Path)
    args = parser.parse_args()
    for workbook_path in args.workbooks:
        print(f'{workbook_path}: {len(group_workbook(workbook_path, args.country))} series')
