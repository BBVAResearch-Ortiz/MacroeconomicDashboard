"""Collect the monthly reports requested in the Türkiye trade workbook from TÜİK."""

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re


PORTAL = 'https://bi.tuik.gov.tr/extensions/tuik-mashup/index.html?lang=en'
ADJUSTED = 'Seasonally and Calendar Adjusted Foreign Trade'
PRODUCT = 'Product-Product Group / Partner Country'
SNAPSHOT = Path(__file__).resolve().parent / 'snapshots' / 'turkey-tuik.json'


@dataclass(frozen=True)
class Report:
    code: str
    name: str
    category: str
    choices: tuple = ()
    code_column: str = ''
    groups: tuple = ()
    adjusted: bool = False


REPORTS = (
    Report('TOTAL', 'Total goods trade', 'Total Export/Import'),
    Report('CA_TOTAL', 'Total goods trade · calendar adjusted', ADJUSTED,
           ('Calendar Adjusted', 'Calendar', 'Value'), adjusted=True),
    Report('SCA_TOTAL', 'Total goods trade · seasonally and calendar adjusted', ADJUSTED,
           ('Calendar Adjusted', 'Season and Calendar', 'Value'), adjusted=True),
    Report('HS', 'HS chapter', PRODUCT, ('Product/Product Group', 'Harmonized System', 'HS2 (Chapter)'),
           'Chapter', ('71',)),
    Report('SITC', 'SITC Rev. 4', PRODUCT,
           ('Product/Product Group', 'SITC Rev.4 Classification', 'Level1 (1 Digit)'), 'SITC4', ('3', '9')),
    Report('SCA_SITC', 'SITC Rev. 4 · seasonally and calendar adjusted', ADJUSTED,
           ('Seasonally and Calendar Adjusted', 'SITC Rev.4', 'Season and Calendar', 'Value'),
           'SITC4', ('3', '9'), True),
    Report('CA_BEC', 'BEC · calendar adjusted', ADJUSTED,
           ('Seasonally and Calendar Adjusted', 'BEC', 'Calendar', 'Value'), 'BEC', ('1', '2', '3', '4'), True),
    Report('SCA_BEC', 'BEC · seasonally and calendar adjusted', ADJUSTED,
           ('Seasonally and Calendar Adjusted', 'BEC', 'Season and Calendar', 'Value'),
           'BEC', ('1', '2', '3', '4'), True),
    Report('PARTNER', 'Partner country', 'Country and Country Group', ('By Countries',), 'Country'),
)
GROUP_NAMES = {
    'HS': {'71': 'Precious stones, metals, jewellery and coins'},
    'SITC': {'3': 'Mineral fuels and lubricants', '9': 'Commodities not classified elsewhere'},
    'BEC': {'1': 'Capital goods', '2': 'Intermediate goods', '3': 'Consumer goods', '4': 'Other goods'},
}
REPORT_ROWS = """() => {
  const body = document.querySelector('.table-wrapper tbody');
  return [...body.rows].map(row => [...row.cells].map(cell =>
    [cell.textContent.trim(), cell.rowSpan, cell.classList.contains('total')]));
}"""


def choose_dates(page, years):
    year, month = page.locator('.date-wrapper').all()
    for value in years:
        if year.get_by_role('combobox').get_attribute('aria-expanded') != 'true':
            year.locator('[class$="-control"]').click()
        page.get_by_role('option', name=str(value), exact=True).click()
    month.locator('[class$="-control"]').click()
    page.get_by_role('option', name='All', exact=True).click()
    month.get_by_role('combobox').press('Escape')


def choose_groups(page, report):
    if not report.code_column:
        return
    search = page.get_by_placeholder('Search Code or Description')
    search.wait_for()
    if not report.groups:
        all_groups = page.get_by_role('checkbox', name='All', exact=True)
        if not all_groups.is_checked():
            all_groups.locator('xpath=..').click()
        return
    for code in report.groups:
        search.fill(code)
        page.get_by_text(re.compile(r'^' + re.escape(code) + r'\s*-')).first.click()
    search.clear()


def fetch_rows(browser, report, years):
    page = browser.new_page()
    page.set_default_timeout(25000)
    try:
        page.goto(PORTAL, wait_until='domcontentloaded', timeout=50000)
        page.get_by_role('button', name=report.category, exact=True).click()
        page.get_by_role('button', name='Next Step', exact=True).first.click()
        for choice in report.choices:
            page.locator('input[type=radio]').locator('xpath=..').get_by_text(choice, exact=True).click()
        if report.choices:
            page.get_by_role('button', name='Next Step', exact=True).click()
        choose_dates(page, years)
        choose_groups(page, report)
        for code in ('export', 'import', 'usd'):
            field = page.locator(f'#{code}')
            if code == 'usd' and report.adjusted and not field.count():
                continue
            if not field.is_checked():
                page.locator(f'label[for="{code}"]').click()
        with page.expect_popup(timeout=60000) as result:
            page.get_by_role('button', name='Generate Report', exact=True).click()
        output = result.value
        try:
            output.locator('.table-wrapper tbody tr').first.wait_for(timeout=90000)
            output.locator('.table-wrapper').evaluate("""async panel => {
              for(let i=0; i<105; i++){
                const count=panel.querySelectorAll('tbody tr').length;
                panel.scrollTop=panel.scrollHeight;
                panel.dispatchEvent(new Event('scroll', {bubbles:true}));
                await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
                if(panel.querySelectorAll('tbody tr').length===count) return;
              }
              throw new Error('TÜİK report did not finish expanding');
            }""")
            headers = output.locator('.table-wrapper th').all_inner_texts()
            return headers, output.evaluate(REPORT_ROWS)
        finally:
            output.close()
    finally:
        page.close()


def expand_spans(rows, width):
    active = {}
    for cells in rows:
        row = [None] * width
        subtotal = False
        for index, (value, is_total, remaining) in list(active.items()):
            row[index] = value
            subtotal |= is_total
            if remaining == 1:
                del active[index]
            else:
                active[index] = value, is_total, remaining - 1
        positions = [i for i, value in enumerate(row) if value is None]
        if len(positions) != len(cells):
            raise ValueError('Unexpected number of cells in a TÜİK report row')
        for index, (value, span, is_total) in zip(positions, cells):
            row[index] = value
            subtotal |= is_total
            if span > 1:
                active[index] = value, is_total, span - 1
        if not subtotal:
            yield row


def parse_value(value):
    if value in ('', '-', '–', '—', '.'):
        return None
    if not re.fullmatch(r'-?(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d+)?', value):
        raise ValueError(f'Unexpected TÜİK number: {value!r}')
    return float(value.replace('.', '').replace(',', '.')) / 1_000_000


def parse_report(report, headers, rows, years, today):
    measure = 'Value' if report.adjusted else 'USD'
    required = ['Year', 'Month', f'Export {measure}', f'Import {measure}']
    if report.code_column:
        required += [report.code_column, report.code_column + ' Name']
    columns = {name: headers.index(name) for name in required}
    if any(headers.count(name) != 1 for name in required):
        raise ValueError('Duplicate TÜİK columns')
    values = {}
    found = set()
    for row in expand_spans(rows, len(headers)):
        year, month = (int(row[columns[key]]) for key in ('Year', 'Month'))
        day = date(year, month, 1)
        if year not in years or day >= today.replace(day=1):
            raise ValueError(f'Unexpected TÜİK reference month: {day}')
        code = row[columns[report.code_column]] if report.code_column else ''
        if report.groups and code not in report.groups:
            raise ValueError(f'Unexpected TÜİK subgroup: {code}')
        if report.code_column and not re.fullmatch(r'[0-9A-Za-z]+', code):
            raise ValueError(f'Invalid TÜİK subgroup identifier: {code!r}')
        code_name = row[columns[report.code_column + ' Name']] if code else ''
        if report.groups:
            taxonomy = report.code.removeprefix('SCA_').removeprefix('CA_')
            code_name = GROUP_NAMES[taxonomy][code]
        for flow, suffix in (('Export', 'EXPORTS'), ('Import', 'IMPORTS')):
            value = parse_value(row[columns[f'{flow} {measure}']])
            if value is None:
                continue
            key = '_'.join(filter(None, ('TR_TUIK_M', report.code, code, suffix)))
            title = f'Goods {flow.lower()}s · {report.name}'
            if code:
                title += f' · {code_name}'
            entry = values.setdefault(key, {'titulo_serie': title, 'observaciones': {}})
            if day.isoformat() in entry['observaciones']:
                raise ValueError(f'Duplicate TÜİK observation for {key} on {day}')
            entry['observaciones'][day.isoformat()] = value
            found.add((code, suffix))
    expected = {(code, flow) for code in report.groups or ('',) for flow in ('EXPORTS', 'IMPORTS')}
    if not values or (report.code != 'PARTNER' and not expected <= found):
        raise ValueError(f'Incomplete TÜİK report: {report.code}')
    for entry in values.values():
        entry.update(
            subtitulo_descripcion='General Trade System · monthly · ' + report.name,
            transformacion_y_calculo='Official USD values divided by 1,000,000.',
            fuente='Turkish Statistical Institute (TÜİK) · Foreign Trade Statistics',
            frecuencia_y_cobertura_temporal='Monthly',
            tipo_grafico='Line chart',
            bloque='TUIK_TRADE',
            área='external_sector',
            grupo='exterior',
            frecuencia='Mensual',
            unidad='Millones de USD',
            source_url=PORTAL,
        )
        entry['observaciones'] = sorted(entry['observaciones'].items())
    return values


def main():
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=SNAPSHOT, type=Path)
    parser.add_argument('--years', default=2, type=int, choices=range(1, 6))
    parser.add_argument('--report', action='append', choices=[report.code for report in REPORTS])
    args = parser.parse_args()
    today = datetime.now(timezone.utc).date()
    years = list(range(today.year, today.year - args.years, -1))
    previous = json.loads(args.output.read_text(encoding='utf8')) if args.output.exists() else {'series': {}}
    updated, failed = {}, []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for report in REPORTS:
                if args.report and report.code not in args.report:
                    continue
                try:
                    headers, rows = fetch_rows(browser, report, years)
                    series = parse_report(report, headers, rows, years, today)
                    updated.update(series)
                    print(f'{report.code}: {len(series)} series', flush=True)
                except Exception as error:
                    failed.append(report.code)
                    print(f'{report.code}: {error}', flush=True)
        finally:
            browser.close()
    if not updated:
        raise SystemExit('No TÜİK report could be verified')
    values = previous['series'].copy()
    for key, entry in updated.items():
        observations = dict(values.get(key, {}).get('observaciones', []))
        observations.update(entry['observaciones'])
        values[key] = {**entry, 'observaciones': [list(point) for point in sorted(observations.items())]}
    if values != previous['series']:
        snapshot = {
            'origen': {'name': 'TÜİK Foreign Trade Statistics', 'updated_at': datetime.now(timezone.utc).isoformat()},
            'series': dict(sorted(values.items())),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix('.tmp')
        temporary.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf8')
        temporary.replace(args.output)
    if failed:
        print('::warning::TUIK reports with errors: ' + ', '.join(failed), flush=True)


if __name__ == '__main__':
    main()
