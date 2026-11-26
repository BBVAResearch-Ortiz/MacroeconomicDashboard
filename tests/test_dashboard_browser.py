"""Browser regression tests against the checked-in pages and data."""

import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'http://dashboard.test'


def serve_repository(route):
    url = urlsplit(route.request.url)
    if url.hostname != 'dashboard.test':
        route.abort()
        return
    resource = (ROOT / (url.path.lstrip('/') or 'index.html')).resolve()
    if resource.is_relative_to(ROOT) and resource.is_file():
        route.fulfill(path=resource)
    else:
        route.fulfill(status=404)


class DashboardBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        playwright = sync_playwright().start()
        cls.addClassCleanup(playwright.stop)
        cls.browser = playwright.chromium.launch()
        cls.addClassCleanup(cls.browser.close)

    def start_page(self, **options):
        context = self.browser.new_context(**options)
        self.addCleanup(context.close)
        page = context.new_page()
        page.route('**/*', serve_repository)
        errors = []
        page.on('pageerror', lambda error: errors.append(error.stack or str(error)))
        self.addCleanup(lambda: self.assertEqual(errors, []))
        return page

    def assert_language(self, page, code):
        expect(page.locator('html')).to_have_attribute('lang', code)
        expect(page.locator(f'#langSeg [data-lang="{code}"]')).to_have_attribute('aria-pressed', 'true')

    def assert_blackboard(self, page, language):
        expect(page.locator('#tab-explorador')).to_have_attribute('aria-selected', 'true')
        expect(page.locator('#bbchart svg').first).to_be_visible()
        self.assert_language(page, language)

    def test_blackboard_click_and_keyboard_preserve_language(self):
        page = self.start_page()
        page.goto(f'{ORIGIN}/espana.html?lang=en')
        page.locator('#tab-explorador').click()
        self.assert_blackboard(page, 'en')
        expect(page.locator('#bbcatalog summary').first).to_have_text('Add or remove series')
        expect(page.locator('#tab-explorador')).to_be_focused()

        page.keyboard.press('ArrowLeft')
        expect(page.locator('#tab-resumen')).to_be_focused()
        self.assert_language(page, 'en')
        page.keyboard.press('ArrowRight')
        self.assert_blackboard(page, 'en')

    def test_deep_links_and_language_change_survive_reload(self):
        page = self.start_page()
        page.goto(f'{ORIGIN}/?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        page.locator('#langSeg [data-lang="es"]').click()
        self.assert_blackboard(page, 'es')
        expect(page).to_have_url(re.compile(r'\?lang=es#explorador$'))
        page.reload()
        self.assert_blackboard(page, 'es')
        expect(page.locator('#bbcatalog summary').first).to_have_text('Añadir o quitar series')

    def test_blackboard_renders_each_chart_mode(self):
        page = self.start_page()
        page.goto(f'{ORIGIN}/espana.html?lang=es#pizarra')
        self.assert_blackboard(page, 'es')
        for mode in ('dual', 'bars', 'stack', 'scatter', 'heat', 'multiples', 'lines'):
            with self.subTest(mode=mode):
                button = page.locator(f'[data-bbm="{mode}"]')
                button.click()
                expect(button).to_have_attribute('aria-pressed', 'true')
                chart = '#bbchart table' if mode == 'heat' else '#bbchart svg'
                expect(page.locator(chart).first).to_be_visible()
                self.assert_language(page, 'es')

    def test_mobile_navigation_preserves_language(self):
        page = self.start_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        page.goto(f'{ORIGIN}/espana.html?lang=es')
        page.locator('#tab-explorador').tap()
        self.assert_blackboard(page, 'es')
        page.locator('#bbcatalog summary').first.tap()
        expect(page.locator('#bblist')).to_be_visible()

    def test_scatter_analysis_and_calculated_csv(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/espana.html?lang=en#dispersion')
        self.assert_blackboard(page, 'en')
        expect(page.locator('.subnav')).to_have_count(0)
        expect(page.locator('[data-bbm]')).to_have_count(7)
        chart = page.locator('#bbchart')
        analysis = page.get_by_role('region', name='Scatterplot analysis')
        self.assertGreaterEqual(analysis.bounding_box()['y'], chart.bounding_box()['y'] + chart.bounding_box()['height'])
        expect(analysis.get_by_role('button', name='Linear', exact=True)).to_have_attribute('aria-pressed', 'true')
        analysis.get_by_role('button', name='Quadratic').click()
        expect(page.locator('#bb-fit-stats')).to_contain_text('Quadratic R²')
        analysis.get_by_role('button', name='Non-linear (LOWESS)').click()
        expect(page.locator('#bb-fit-stats')).to_contain_text('LOWESS R²')
        transform = analysis.get_by_label('Transformation')
        expect(transform.locator('option[value=delta]')).to_have_text(
            'Change from previous observation (Calculated here)'
        )
        transform.select_option('delta')
        expect(analysis.locator('[data-status=calculated]')).to_have_count(2)
        expect(chart.locator('svg')).to_be_visible()
        with page.expect_download() as pending:
            page.locator('.figure-csv-header .csv-action').click()
        downloaded = pending.value.path().read_text(encoding='utf-8-sig')
        self.assertIn('Calculated here.', downloaded)
        self.assertIn('Source URL', downloaded)

    def test_scatter_axes_use_the_grouped_series_catalogue(self):
        page = self.start_page()
        page.goto(f'{ORIGIN}/espana.html?lang=en#dispersion')
        self.assert_blackboard(page, 'en')
        x = page.get_by_role('group', name='Horizontal axis (X)')
        y = page.get_by_role('group', name='Vertical axis (Y)')
        x_summary = x.locator('#bbx-summary')
        y_summary = y.locator('#bby-summary')
        x_summary.click()
        x_option = x.locator('input[type=radio][data-catalog-pick=paro_epa]')
        for heading in x_option.locator('xpath=ancestor::details[@data-catalog-group]/summary').all():
            heading.click()
        x_option.focus()
        x_option.press('Space')
        expect(x_option).to_be_checked()
        expect(x_option).to_be_focused()
        expect(x_summary).to_contain_text('Unemployment')

        y_summary.click()
        y_option = y.locator('input[type=radio][data-catalog-pick=ipc_sub]')
        for heading in y_option.locator('xpath=ancestor::details[@data-catalog-group]/summary').all():
            heading.click()
        y_option.check()
        expect(y_option).to_be_checked()
        expect(y.locator('[data-catalog-pick=paro_epa]')).to_be_disabled()
        expect(page.locator('#bbchart svg')).to_be_visible()

        page.get_by_role('button', name='Swap axes').click()
        expect(x.locator('[data-catalog-pick=ipc_sub]')).to_be_checked()
        expect(y.locator('[data-catalog-pick=paro_epa]')).to_be_checked()
        expect(page.locator('#bbchart svg')).to_be_visible()

        page.locator('[data-bbm=lines]').click()
        expect(page.locator('#bblist input[type=checkbox]')).not_to_have_count(0)

    def test_overview_and_blackboard_share_numeric_typography(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/espana.html?lang=en')
        card = page.locator('.gcard').first
        reading = card.locator('.chart-reading-value')
        expect(reading).to_be_visible()
        expect(reading.locator('small')).to_have_text('% y/y')
        expect(card.locator('.reading-context time')).to_have_attribute('datetime', re.compile(r'^\d{4}-\d{2}-\d{2}$'))
        properties = ['font-family', 'font-size', 'font-weight', 'font-variant-numeric']
        overview_style = reading.evaluate('(value, keys) => keys.map(key => getComputedStyle(value).getPropertyValue(key))', properties)
        title_size = card.locator('h3').evaluate('title => parseFloat(getComputedStyle(title).fontSize)')

        page.locator('#tab-explorador').click()
        self.assert_blackboard(page, 'en')
        board_reading = page.locator('#bbchart .chart-reading-value').first
        board_style = board_reading.evaluate('(value, keys) => keys.map(key => getComputedStyle(value).getPropertyValue(key))', properties)
        board_title_size = page.locator('.figure-csv-title h3').evaluate('title => parseFloat(getComputedStyle(title).fontSize)')
        self.assertEqual(overview_style, board_style)
        self.assertLess(title_size, board_title_size)

    def test_overview_card_headings_stay_on_one_line(self):
        page = self.start_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        page.goto(f'{ORIGIN}/espana.html?lang=en')
        headings = page.locator('.gcard :is(h3,.sub)')
        expect(headings.first).to_be_visible()
        self.assertTrue(headings.evaluate_all('''nodes => nodes.length > 0 && nodes.every(node => {
            const style = getComputedStyle(node);
            return style.whiteSpace === 'nowrap' && style.textOverflow === 'ellipsis'
                && node.title === node.textContent;
        })'''))

    def test_ipi_switch_and_csv_keep_the_source(self):
        page = self.start_page()
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        page.wait_for_function("Boolean(S().drive_es_IPI_GEN_RAW)")
        page.evaluate("""localStorage.setItem('mme-bb', JSON.stringify({
            picks:['drive_es_IPI_GEN_RAW'], tr:'original', adjustment:'published'
        }))""")
        page.reload()
        self.assert_blackboard(page, 'en')
        choice = page.locator('#board-transform-seasonal')
        expect(choice.locator('option')).to_have_count(2)
        expect(choice).to_have_value('raw')
        choice.select_option('adjusted')
        expect(page.locator('.figure-csv-title h3')).to_contain_text('CVEC INE')
        with page.expect_download() as pending:
            page.locator('.figure-csv-header .csv-action').click()
        csv = pending.value.path().read_text(encoding='utf-8-sig')
        self.assertIn('Source URL', csv)
        self.assertIn('CVEC INE', csv)

    def test_transform_menu_labels_only_calculated_options(self):
        page = self.start_page()
        page.add_init_script("""
            localStorage.setItem('mme-bb', JSON.stringify({picks:['pib_yoy']}))
        """)
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        select = page.locator('#board-transform')
        expect(select.locator('option[value=qoq]')).to_have_text('Quarter-on-quarter change')
        expect(select.locator('option[value=mom]')).to_have_text('Month-on-month change')
        expect(select.locator('option[value=mom]')).to_be_disabled()
        page.evaluate("bb.picks=['cc_pib']; saveBB(); render()")
        expect(select.locator('option[value=qoq]')).to_have_text('Quarter-on-quarter change (Calculated here)')
        expect(select.locator('option[value=mom]')).to_be_disabled()
        select.select_option('qoq')
        expect(page.locator('[data-status=calculated]')).to_contain_text('percentage points')
        expect(page.locator('#bbchart svg')).to_be_visible()

    def test_big_data_catalogue_and_csv_header(self):
        page = self.start_page()
        page.goto(f'{ORIGIN}/espana.html?lang=en#bigdata')
        expect(page.locator('#big-chart svg').first).to_be_visible()
        expect(page.locator('.figure-csv-header #big-csv')).to_be_enabled()
        page.locator('#big-catalog-summary').click()
        expect(page.locator('#big-series-field')).to_be_visible()
        page.locator('#big-variant').select_option('Nominal')
        expect(page.locator('#big-variant')).to_have_value('Nominal')
        expect(page.locator('#big-series-field [data-catalog-pick]').first).to_be_attached()
        self.assert_language(page, 'en')

    def test_other_country_blackboards_open_from_their_own_tabs(self):
        for country in ('turquia', 'usa'):
            with self.subTest(country=country):
                page = self.start_page()
                page.goto(f'{ORIGIN}/{country}.html?lang=en')
                page.locator('#tab-explorador').click()
                self.assert_blackboard(page, 'en')

    def test_turkiye_keeps_verified_data_when_the_workbook_contains_only_examples(self):
        page = self.start_page()
        example = {'series': {'EXAMPLE': {'fuente': 'Turkey_example_data.xlsx · Monthly!M'}}}
        page.route('**/snapshots/turkey.json', lambda route: route.fulfill(json=example))
        page.goto(f'{ORIGIN}/turquia.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        expect(page.locator('#stamp')).to_contain_text('61 series')
        expect(page.locator('#foot a')).to_have_count(3)
        source = page.locator('#bbchart .source-publisher').first
        expect(source).to_contain_text('Ministry of Treasury and Finance of Türkiye')
        expect(source).to_have_attribute('href', 'https://en.hmb.gov.tr/public-finance')
        with page.expect_download() as pending:
            page.locator('.figure-csv-header .csv-action').click()
        csv = pending.value.path().read_text(encoding='utf-8-sig')
        self.assertIn('Treasury Cash Realizations', csv)
        self.assertIn('https://en.hmb.gov.tr/public-finance', csv)

    def test_turkiye_combines_new_live_values_with_verified_history(self):
        page = self.start_page()
        verified = json.loads((ROOT / 'drive_ingestion/snapshots/turkey-verified.json').read_text(encoding='utf-8'))
        code = 'TR_TRADE_M_EXPORTS'
        entry = {**verified['series'][code], 'observaciones': [['2026-10-01', 25885]]}
        page.route('**/snapshots/turkey.json', lambda route: route.fulfill(json={'series': {code: entry}}))
        page.goto(f'{ORIGIN}/turquia.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        expect(page.locator('#stamp')).to_contain_text('61 series')
        points = page.evaluate("DATA.series.drive_tr_TR_TRADE_M_EXPORTS.data")
        self.assertEqual(len(points), 166)
        self.assertEqual(points[0][:2], ['2013-01-01', 12263])
        self.assertEqual(points[-1][:2], ['2026-10-01', 25885])


if __name__ == '__main__':
    unittest.main()
