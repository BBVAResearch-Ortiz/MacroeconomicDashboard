"""Browser regression tests against the checked-in pages and data."""

import csv
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
        expect(page.locator('.board-head [data-bbm]')).to_have_count(7)
        expect(page.locator('.bbside [data-bbm]')).to_have_count(0)
        for mode in ('dual', 'bars', 'stack', 'scatter', 'heat', 'multiples', 'lines'):
            with self.subTest(mode=mode):
                button = page.locator(f'[data-bbm="{mode}"]')
                button.click()
                expect(button).to_have_attribute('aria-pressed', 'true')
                chart = '#bbchart table' if mode == 'heat' else '#bbchart svg'
                expect(page.locator(chart).first).to_be_visible()
                self.assert_language(page, 'es')

    def test_blackboard_axis_assignments_survive_toggle_reorder_and_removal(self):
        page = self.start_page()
        page.add_init_script("""
            if (!localStorage.getItem('mme-bb')) {
                localStorage.setItem('mme-bb', JSON.stringify({
                    mode:'dual', picks:['drive_es_IPI_GEN_RAW','drive_es_IPI_ENE_RAW'], adjustment:'raw'
                }));
            }
        """)
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        chart = page.locator('#bbchart')
        employed = page.locator('[data-bbax=drive_es_IPI_GEN_RAW]')
        unemployed = page.locator('[data-bbax=drive_es_IPI_ENE_RAW]')
        expect(employed).to_have_text('Left axis')
        expect(unemployed).to_have_text('Right axis')

        employed.press('Enter')
        expect(employed).to_be_focused()
        expect(employed).to_have_text('Right axis')
        expect(chart.locator('path[data-axis=right]')).to_have_count(2)
        expect(chart.locator('[data-axis-label=left]')).to_have_count(0)
        expect(page.locator('#bblg')).to_contain_text('right axis')
        employed.press('Enter')
        expect(employed).to_have_text('Left axis')

        page.locator('[data-bbm=lines]').click()
        page.locator('[data-bb-row=drive_es_IPI_GEN_RAW] [data-bb-move="1"]').click()
        page.locator('[data-bbm=dual]').click()
        expect(employed).to_have_text('Left axis')
        expect(unemployed).to_have_text('Right axis')
        expect(chart.locator('path[data-axis=left]')).to_have_count(1)
        expect(chart.locator('path[data-axis=right]')).to_have_count(1)

        page.locator('[data-bbrm=drive_es_IPI_GEN_RAW]').click()
        expect(unemployed).to_have_text('Right axis')
        expect(chart.locator('[data-axis-label=right]')).to_have_text('Right')
        page.reload()
        self.assert_blackboard(page, 'en')
        expect(chart.locator('path[data-axis=right]')).to_have_count(1)
        page.locator('#explorer-search').fill('IPI_GEN_RAW')
        page.locator('#explorer-search-results [data-search-pick=drive_es_IPI_GEN_RAW]').click()
        expect(employed).to_have_text('Left axis')
        unemployed.click()
        expect(chart.locator('path[data-axis=left]')).to_have_count(2)
        expect(chart.locator('[data-axis-label=right]')).to_have_count(0)

    def test_blackboard_axes_use_independent_scales_and_visible_dates(self):
        page = self.start_page(viewport={'width': 390, 'height': 900})
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        page.wait_for_function('!spainDriveLoading')
        page.evaluate("""() => {
            const series = (label, data) => ({label, data, unit:'%', block:'actividad', freq:'M'});
            S().drive_es_test_left=series('Large scale', [['2025-01-01',1000000],['2025-02-01',2000000]]);
            S().drive_es_test_right=series('Narrow scale', [['2025-01-01',0.037],['2025-02-01',0.041],['2025-09-01',0.043]]);
            Object.assign(bb,{picks:['drive_es_test_left','drive_es_test_right'], mode:'dual', tr:'original', adjustment:'raw'});
            state.range='todo';
            render();
        }""")
        chart = page.locator('#bbchart')
        svg = chart.locator('svg')
        left_ticks = chart.locator('[data-axis-tick=left]').all_text_contents()
        right_ticks = chart.locator('[data-axis-tick=right]').all_text_contents()
        self.assertGreater(float(left_ticks[-1].replace(',', '')), 1000000)
        self.assertLess(float(right_ticks[-1]), 0.05)
        self.assertGreater(len(right_ticks), 2)
        self.assertEqual(len(right_ticks), len(set(right_ticks)))
        svg.press('ArrowLeft')
        expect(svg.locator('#dots circle')).to_have_count(2)
        page.locator('.chart-range [data-r="1m"]').click()
        expect(chart.locator('[data-axis-label=left]')).to_have_count(0)
        expect(chart.locator('[data-axis-label=right]')).to_have_text('Right')
        expect(chart.locator('path[data-axis=right]')).to_have_count(1)
        expect(page.locator('[data-bbax=drive_es_test_left]')).to_have_text('Left axis')

    def test_blackboard_discards_a_pending_redraw_after_switching_axes(self):
        page = self.start_page()
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        page.wait_for_function('!spainDriveLoading')
        page.locator('[data-bbm=dual]').click()
        result = page.evaluate("""async () => {
            let ran = false;
            observe(() => {ran = true;});
            const previousTimer = roT;
            document.querySelector('#bbchart svg').setAttribute('viewBox','0 0 100 100');
            for(let i=0; i<10 && roT===previousTimer; i++){
                await new Promise(requestAnimationFrame);
            }
            const scheduled = roT!==previousTimer;
            document.querySelector('[data-bbax]').click();
            await new Promise(resolve=>setTimeout(resolve,130));
            return {scheduled,ran};
        }""")
        self.assertEqual(result, {'scheduled': True, 'ran': False})
        expect(page.locator('#bbchart [data-axis-label=left]')).to_have_count(0)
        expect(page.locator('#bbchart [data-axis-label=right]')).to_have_count(1)

    def test_mobile_navigation_preserves_language(self):
        page = self.start_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        page.goto(f'{ORIGIN}/espana.html?lang=es')
        page.locator('#tab-explorador').tap()
        self.assert_blackboard(page, 'es')
        page.locator('#bbcatalog summary').first.tap()
        expect(page.locator('#bblist')).to_be_visible()

    def test_spain_header_is_compact_and_tabs_stay_in_one_row(self):
        page = self.start_page(viewport={'width': 1440, 'height': 900})
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        expect(page.locator('.mast .lede')).to_be_hidden()
        expect(page.locator('.mast #stamp')).to_be_hidden()
        self.assertLessEqual(page.locator('.mast #liveMsg').bounding_box()['height'], 1)
        tabs = page.get_by_role('tablist')
        expect(tabs.get_by_role('tab')).to_have_count(10)
        for width in (1440, 390):
            with self.subTest(width=width):
                page.set_viewport_size({'width': width, 'height': 900})
                positions = tabs.get_by_role('tab').evaluate_all(
                    'buttons => buttons.map(button => button.getBoundingClientRect().top)'
                )
                self.assertEqual(len(set(positions)), 1)
                overflows = tabs.evaluate('bar => bar.scrollWidth > bar.clientWidth')
                self.assertEqual(overflows, width == 390)
        page.locator('#tab-resumen').press('ArrowLeft')
        expect(page.locator('#tab-fuentes')).to_be_focused()
        self.assertGreater(tabs.evaluate('bar => bar.scrollLeft'), 0)

    def test_custom_dates_open_to_the_right_and_apply_on_change(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        page.wait_for_function('!spainDriveLoading')
        dates = page.locator('.chart-date-range')
        expect(page.locator('.board-figure .date-coverage')).to_have_count(0)
        dates.locator('summary').click()
        expect(dates.get_by_role('button', name='Apply dates')).to_have_count(0)
        quick_ranges = page.locator('.chart-range .seg').bounding_box()
        trigger = dates.locator('summary').bounding_box()
        fields = dates.locator('form').bounding_box()
        self.assertGreater(fields['x'], quick_ranges['x'] + quick_ranges['width'])
        self.assertGreater(fields['x'], trigger['x'] + trigger['width'])
        self.assertLess(abs(fields['y'] - quick_ranges['y']), 16)
        start = dates.get_by_label('From')
        end = dates.get_by_label('To')
        for field in (start, end):
            geometry = field.evaluate("""input => {
                const text=document.createRange();
                text.selectNode(input.closest('label').firstChild);
                const label=text.getBoundingClientRect(), field=input.getBoundingClientRect();
                return {labelRight:label.right,inputLeft:field.left,
                    centerDifference:Math.abs(label.top+label.height/2-field.top-field.height/2)};
            }""")
            self.assertLessEqual(geometry['labelRight'], geometry['inputLeft'])
            self.assertLess(geometry['centerDifference'], 3)
        start.fill('2025-01-01')
        expect(dates).to_have_attribute('data-custom', '')
        expect(start).to_be_focused()
        expect(dates.locator('form')).to_be_visible()
        end.fill('2025-07-01')
        expect(start).to_have_value('2025-01-01')
        expect(end).to_have_value('2025-07-01')
        expect(end).to_be_focused()
        chart = page.locator('#bbchart')
        chart.locator('svg').press('ArrowRight')
        tooltip_date = chart.locator('.tip time')
        expect(tooltip_date).to_be_visible()
        self.assertLessEqual(tooltip_date.get_attribute('datetime'), '2025-07-01')
        end.fill('2024-12-01')
        expect(dates.get_by_role('alert')).to_contain_text('chronological order')
        self.assertEqual(page.evaluate('customRange.end'), '2025-07-01')
        end.fill('2025-06-01')
        expect(end).to_have_value('2025-06-01')

        page.set_viewport_size({'width': 320, 'height': 900})
        fields = dates.locator('form').bounding_box()
        self.assertLessEqual(fields['x'] + fields['width'], 320)
        page.reload()
        self.assert_blackboard(page, 'en')
        expect(start).to_have_value('2025-01-01')
        expect(end).to_have_value('2025-06-01')

    def test_scatter_analysis_and_calculated_csv(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/espana.html?lang=en#dispersion')
        self.assert_blackboard(page, 'en')
        expect(page.locator('.subnav')).to_have_count(0)
        expect(page.locator('[data-bbm]')).to_have_count(7)
        chart = page.locator('#bbchart')
        analysis = page.get_by_role('region', name='Scatterplot analysis')
        self.assertEqual(page.locator('.bbside .scatter-analysis').count(), 1)
        analysis_box = analysis.bounding_box()
        self.assertLessEqual(analysis_box['x'] + analysis_box['width'], chart.bounding_box()['x'])
        expect(analysis.get_by_role('button', name='Linear', exact=True)).to_have_attribute('aria-pressed', 'true')
        analysis.get_by_role('button', name='Quadratic').click()
        expect(page.locator('#bb-fit-stats')).to_contain_text('Quadratic R²')
        analysis.get_by_role('button', name='Non-linear (LOWESS)').click()
        expect(page.locator('#bb-fit-stats')).to_contain_text('LOWESS R²')
        transform = page.locator('.board-layout > aside').get_by_label('Transformation')
        expect(transform.locator('option[value=delta]')).to_have_count(0)
        transform.select_option('z')
        expect(page.locator('[data-status=calculated], [data-status=documented]')).to_have_count(0)
        expect(chart.locator('svg')).to_be_visible()
        expect(analysis.locator('.series-chart-sources summary')).to_have_text('Sources by series')
        with page.expect_download() as pending:
            analysis.get_by_role('button', name='Download CSV').click()
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
        x_option = x.locator('input[type=radio][data-catalog-pick=drive_es_BC_EXP_TOTAL_BRUTO]')
        for heading in x_option.locator('xpath=ancestor::details[@data-catalog-group]/summary').all():
            heading.click()
        x_option.focus()
        x_option.press('Space')
        expect(x_option).to_be_checked()
        expect(x_option).to_be_focused()
        expect(x_summary).to_contain_text('Exports of goods')

        y_summary.click()
        y_option = y.locator('input[type=radio][data-catalog-pick=drive_es_IASS_GEN_RAW]')
        for heading in y_option.locator('xpath=ancestor::details[@data-catalog-group]/summary').all():
            heading.click()
        y_option.check()
        expect(y_option).to_be_checked()
        expect(y.locator('[data-catalog-pick=drive_es_BC_EXP_TOTAL_BRUTO]')).to_be_disabled()
        expect(page.locator('#bbchart svg')).to_be_visible()

        page.get_by_role('button', name='Swap axes').click()
        expect(x.locator('[data-catalog-pick=drive_es_IASS_GEN_RAW]')).to_be_checked()
        expect(y.locator('[data-catalog-pick=drive_es_BC_EXP_TOTAL_BRUTO]')).to_be_checked()
        expect(page.locator('#bbchart svg')).to_be_visible()

        page.locator('[data-bbm=lines]').click()
        expect(page.locator('#bblist input[type=checkbox]')).not_to_have_count(0)

    def test_scatter_search_targets_the_axis_that_contains_it(self):
        page = self.start_page()
        page.goto(f'{ORIGIN}/espana.html?lang=en#dispersion')
        self.assert_blackboard(page, 'en')
        x_summary = page.locator('#bbx-summary')
        y_summary = page.locator('#bby-summary')
        initial_x = x_summary.inner_text()
        y_summary.click()
        search_y = page.get_by_role('searchbox', name='Search for axis Y')
        search_y.fill('IASS_GEN_RAW')
        page.locator('#bby-search-results [data-search-pick=drive_es_IASS_GEN_RAW]').click()
        expect(y_summary).to_contain_text('IASS General index')
        expect(x_summary).to_have_text(initial_x)
        expect(search_y).to_be_focused()

        x_summary.click()
        search_x = page.get_by_role('searchbox', name='Search for axis X')
        search_x.fill('IPI_ENE_RAW')
        expect(page.locator('#bbx-search-results [data-search-pick=drive_es_IPI_ENE_RAW]')).to_be_visible()
        search_x.press('Enter')
        expect(x_summary).to_contain_text('Energy')
        expect(y_summary).to_contain_text('IASS General index')
        expect(page.locator('#bbchart svg')).to_be_visible()

    def test_blackboard_shows_readings_on_hover_and_places_csv_below_chart(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/espana.html?lang=en')
        card = page.locator('.gcard').first
        reading = card.locator('.chart-reading-value')
        expect(reading).to_be_visible()
        expect(reading.locator('small')).to_have_text('% y/y')
        expect(card.locator('.reading-context time')).to_have_attribute('datetime', re.compile(r'^\d{4}-\d{2}-\d{2}$'))
        page.locator('#tab-explorador').click()
        self.assert_blackboard(page, 'en')
        figure = page.locator('.board-figure')
        chart = figure.locator('#bbchart')
        tooltip = chart.locator('.tip')
        expect(figure.locator('h3.board-chart-title')).to_be_visible()
        expect(figure.locator('.chart-readings, .chart-reading-value')).to_have_count(0)
        expect(tooltip).to_be_hidden()
        chart.locator('#hit').hover()
        expect(tooltip).to_be_visible()
        expect(tooltip.locator('time')).to_have_attribute('datetime', re.compile(r'^\d{4}-\d{2}-\d{2}$'))
        page.locator('#board-transform').hover()
        expect(tooltip).to_be_hidden()
        footer = figure.locator('.figure-csv-footer')
        expect(footer.get_by_role('button', name='Download CSV')).to_be_enabled()
        bounds = chart.bounding_box()
        self.assertGreater(bounds['height'], 380)
        self.assertGreaterEqual(footer.bounding_box()['y'], bounds['y'] + bounds['height'])

    def test_blackboard_title_uses_the_indicator_or_groups(self):
        page = self.start_page()
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        title = page.locator('h3.board-chart-title')
        cases = [
            (['IPI_GEN_RAW', 'IPI_GEN_CVEC_INE'], re.compile(r'IPI.*general index', re.I)),
            (['IPI_GEN_RAW', 'IPI_ENE_RAW'], 'Industrial production (IPI)'),
            (['IPI_GEN_RAW', 'IASS_GEN_RAW'], 'Industry vs. Business activity'),
        ]
        for picks, expected in cases:
            with self.subTest(picks=picks):
                page.evaluate("(ids) => {bb.picks=ids.map(id=>'drive_es_'+id); viewBoard();}", picks)
                expect(title).to_have_text(expected)

    def test_blackboard_downloads_a_png_from_chart_and_heat_map(self):
        page = self.start_page(viewport={'width': 1440, 'height': 900})
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        marker = page.locator('.chart-date-range summary')
        download_button = page.get_by_role('button', name='Download PNG')
        self.assertGreaterEqual(download_button.bounding_box()['x'], marker.bounding_box()['x'] + marker.bounding_box()['width'])
        expect(page.get_by_role('button', name='Copy image')).to_have_count(0)
        self.assertGreater(page.locator('#bbchart svg').bounding_box()['height'], 500)

        for mode in ('lines', 'heat'):
            with self.subTest(mode=mode):
                page.locator(f'[data-bbm={mode}]').click()
                with page.expect_download() as pending:
                    download_button.click()
                self.assertEqual(pending.value.suggested_filename, 'blackboard.png')
                png = pending.value.path().read_bytes()
                self.assertEqual(png[:8], b'\x89PNG\r\n\x1a\n')
                self.assertGreater(int.from_bytes(png[16:20], 'big'), 0)
                self.assertGreater(int.from_bytes(png[20:24], 'big'), 0)

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
        page.locator('.board-figure > .series-chart-sources summary').click()
        expect(page.locator('.board-figure > .series-chart-sources .series-source-name')).to_contain_text('CVEC INE')
        with page.expect_download() as pending:
            page.locator('.board-figure > .figure-csv-footer .csv-action').click()
        csv = pending.value.path().read_text(encoding='utf-8-sig')
        self.assertIn('Source URL', csv)
        self.assertIn('CVEC INE', csv)

    def test_transform_menu_uses_plain_labels_and_preserves_csv_metadata(self):
        page = self.start_page()
        page.add_init_script("""
            localStorage.setItem('mme-bb', JSON.stringify({
                picks:['drive_es_IPI_GEN_RAW'], adjustment:'adjusted', tr:'delta'
            }))
        """)
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        select = page.locator('#board-transform')
        expect(select.locator('option[value=yoy]')).to_have_text('Year-on-year change')
        expect(select).to_have_value('original')
        expect(select.locator('option[value=delta]')).to_have_count(0)
        expect(select.locator('option[value=z]')).to_have_text('Standardised')
        select.select_option('z')
        expect(page.locator('[data-status=calculated], [data-status=documented]')).to_have_count(0)
        with page.expect_download() as pending:
            page.locator('.board-figure > .figure-csv-footer .csv-action').click()
        with pending.value.path().open(encoding='utf-8-sig', newline='') as downloaded:
            rows = list(csv.DictReader(downloaded))
        self.assertTrue(rows and rows[0]['Transformation'].startswith('Calculated here.'))
        self.assertEqual(page.evaluate("""() => {
            const tail = 1024.1 - 1024;
            return [csvSeriesValue({calculated:true}, tail), csvSeriesValue({}, tail),
                    Object.is(csvSeriesValue({calculated:true}, -1e-14), -0)];
        }"""), [0.1, 1024.1 - 1024, False])

    def test_transform_and_seasonality_are_stacked_in_the_sidebar(self):
        page = self.start_page()
        for width in (1180, 390, 320):
            with self.subTest(width=width):
                page.set_viewport_size({'width': width, 'height': 900})
                page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
                self.assert_blackboard(page, 'en')
                for mode in ('lines', 'scatter'):
                    page.locator(f'[data-bbm={mode}]').click()
                    sidebar = page.locator('.board-layout > aside')
                    transform = sidebar.get_by_label('Transformation').bounding_box()
                    seasonal = sidebar.get_by_label('Seasonal adjustment').bounding_box()
                    self.assertAlmostEqual(transform['x'], seasonal['x'], delta=1)
                    self.assertLess(transform['y'] + transform['height'], seasonal['y'])
                    self.assertLessEqual(seasonal['x'] + seasonal['width'], width)

    def test_spain_catalogue_contains_only_the_four_workbook_areas(self):
        page = self.start_page()
        page.add_init_script("""
            localStorage.setItem('mme-bb', JSON.stringify({picks:['ocup_epa','bono_de']}))
        """)
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        catalogue = page.evaluate("""() => ({
            picks:bb.picks,
            groups:Object.fromEntries(explorerGroups().groups.map(group => [
                L10(group.label), Object.fromEntries(group.groups.map(block => [L10(block.label), block.count]))
            ])),
            ids:explorerSearchEntries().map(row=>row.id)
        })""")
        self.assertEqual(catalogue['groups'], {
            'Business activity': {'Large enterprises': 53, 'Services activity (IASS)': 16},
            'Industry': {'Industrial production (IPI)': 30},
            'Opinion surveys': {'ESI': 21, 'PMI': 3},
            'External sector': {'Trade balance': 22},
        })
        self.assertEqual(len(catalogue['ids']), 145)
        self.assertTrue(all(key.startswith('drive_es_') for key in catalogue['ids']))
        self.assertTrue(catalogue['picks'] and all(key.startswith('drive_es_') for key in catalogue['picks']))
        page.locator('#explorer-search').fill('EPA387796')
        expect(page.locator('#explorer-search-results')).to_contain_text('No matching series.')
        expect(page.locator('#tab-empleo')).to_have_count(0)

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
                expect(page.locator('.board-head [data-bbm]')).to_have_count(8 if country == 'usa' else 7)
                expect(page.locator('.bbside [data-bbm]')).to_have_count(0)
                if country == 'usa':
                    page.locator('[data-bbm=bands]').click()
                    expect(page.locator('#bbchart .chart-bands').first).to_be_visible()
                    expect(page.locator('#bbchart .band-key [data-band-z]').first).to_contain_text('Latest')

    def test_turkiye_keeps_verified_data_when_the_workbook_contains_only_examples(self):
        page = self.start_page()
        example = {'series': {'EXAMPLE': {'fuente': 'Turkey_example_data.xlsx · Monthly!M'}}}
        page.route('**/snapshots/turkey.json', lambda route: route.fulfill(json=example))
        page.goto(f'{ORIGIN}/turquia.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        expect(page.locator('#stamp')).to_contain_text('61 series')
        expect(page.locator('#foot a')).to_have_count(3)
        sources = page.locator('.board-figure > .series-chart-sources')
        sources.locator('summary').click()
        source = sources.locator('.source-publisher').first
        expect(source).to_contain_text('Ministry of Treasury and Finance of Türkiye')
        expect(source).to_have_attribute('href', 'https://en.hmb.gov.tr/public-finance')
        with page.expect_download() as pending:
            page.locator('.board-figure > .figure-csv-footer .csv-action').click()
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
