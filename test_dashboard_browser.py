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
                    mode:'dual', picks:['ocup_epa','paro_epa'], adjustment:'raw'
                }));
            }
        """)
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        chart = page.locator('#bbchart')
        employed = page.locator('[data-bbax=ocup_epa]')
        unemployed = page.locator('[data-bbax=paro_epa]')
        expect(employed).to_have_text('Left axis')
        expect(unemployed).to_have_text('Right axis')

        employed.press('Enter')
        expect(employed).to_be_focused()
        expect(employed).to_have_text('Right axis')
        expect(chart.locator('path[data-axis=right]')).to_have_count(2)
        expect(chart.locator('[data-axis-label=left]')).to_have_count(0)
        expect(chart.locator('.chart-reading-label').first).to_contain_text('(right axis)')
        employed.press('Enter')
        expect(employed).to_have_text('Left axis')

        page.locator('[data-bbm=lines]').click()
        page.locator('[data-bb-row=ocup_epa] [data-bb-move="1"]').click()
        page.locator('[data-bbm=dual]').click()
        expect(employed).to_have_text('Left axis')
        expect(unemployed).to_have_text('Right axis')
        expect(chart.locator('path[data-axis=left]')).to_have_count(1)
        expect(chart.locator('path[data-axis=right]')).to_have_count(1)

        page.locator('[data-bbrm=ocup_epa]').click()
        expect(unemployed).to_have_text('Right axis')
        expect(chart.locator('[data-axis-label=right]')).to_have_text('Right')
        page.reload()
        self.assert_blackboard(page, 'en')
        expect(chart.locator('path[data-axis=right]')).to_have_count(1)
        page.locator('#explorer-search').fill('EPA387796')
        page.locator('#explorer-search-results [data-search-pick=ocup_epa]').click()
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
            S().test_left=series('Large scale', [['2025-01-01',1000000],['2025-02-01',2000000]]);
            S().test_right=series('Narrow scale', [['2025-01-01',0.037],['2025-02-01',0.041],['2025-09-01',0.043]]);
            Object.assign(bb,{picks:['test_left','test_right'], mode:'dual', tr:'original', adjustment:'raw'});
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
        expect(page.locator('[data-bbax=test_left]')).to_have_text('Left axis')

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

    def test_custom_dates_open_to_the_right_and_apply_on_change(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        page.wait_for_function('!spainDriveLoading')
        dates = page.locator('.chart-date-range')
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
        start.fill('2025-01-01')
        expect(dates).to_have_attribute('data-custom', '')
        expect(start).to_be_focused()
        expect(dates.locator('form')).to_be_visible()
        end.fill('2025-07-01')
        expect(page.locator('.date-coverage')).to_contain_text('1 Jan 2025 – 1 Jul 2025')
        self.assertTrue(all(day <= '2025-07-01' for day in page.locator(
            '#bbchart .chart-readings time[datetime]'
        ).evaluate_all("(readings) => readings.map(reading => reading.dateTime)")))
        expect(end).to_be_focused()
        end.fill('2024-12-01')
        expect(dates.get_by_role('alert')).to_contain_text('chronological order')
        expect(page.locator('.date-coverage')).to_contain_text('1 Jan 2025 – 1 Jul 2025')
        end.fill('2025-06-01')
        expect(page.locator('.date-coverage')).to_contain_text('1 Jan 2025 – 1 Jun 2025')

        page.set_viewport_size({'width': 320, 'height': 900})
        fields = dates.locator('form').bounding_box()
        self.assertLessEqual(fields['x'] + fields['width'], 320)
        page.reload()
        expect(page.locator('.date-coverage')).to_contain_text('1 Jan 2025 – 1 Jun 2025')

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

    def test_scatter_search_targets_the_axis_that_contains_it(self):
        page = self.start_page()
        page.goto(f'{ORIGIN}/espana.html?lang=en#dispersion')
        self.assert_blackboard(page, 'en')
        x_summary = page.locator('#bbx-summary')
        y_summary = page.locator('#bby-summary')
        initial_x = x_summary.inner_text()
        y_summary.click()
        search_y = page.get_by_role('searchbox', name='Search for axis Y')
        search_y.fill('core cpi')
        page.locator('#bby-search-results [data-search-pick=ipc_sub]').click()
        expect(y_summary).to_contain_text('Core CPI')
        expect(x_summary).to_have_text(initial_x)
        expect(search_y).to_be_focused()

        x_summary.click()
        search_x = page.get_by_role('searchbox', name='Search for axis X')
        search_x.fill('paro epa')
        expect(page.locator('#bbx-search-results [data-search-pick=paro_epa]')).to_be_visible()
        search_x.press('Enter')
        expect(x_summary).to_contain_text('Unemployment rate')
        expect(y_summary).to_contain_text('Core CPI')
        expect(page.locator('#bbchart svg')).to_be_visible()

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
        with page.expect_download() as pending:
            page.locator('.figure-csv-header .csv-action').click()
        with pending.value.path().open(encoding='utf-8-sig', newline='') as downloaded:
            rows = {row['Date']: row['Value'] for row in csv.DictReader(downloaded)}
        self.assertEqual(rows['2026-04-01'], '-0.46')
        self.assertEqual(page.evaluate("""() => {
            const tail = 1024.1 - 1024;
            return [csvSeriesValue({calculated:true}, tail), csvSeriesValue({}, tail),
                    Object.is(csvSeriesValue({calculated:true}, -1e-14), -0)];
        }"""), [0.1, 1024.1 - 1024, False])

    def test_usa_blackboard_layout_rules(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/usa.html?lang=es#explorador')
        self.assert_blackboard(page, 'es')
        figure = page.locator('figure.bbfig')
        box = figure.bounding_box()
        title = figure.locator('h3')
        # Rule 1: the title never wraps; the full text stays available as a tooltip.
        self.assertLess(title.bounding_box()['height'], 2 * title.evaluate('t => parseFloat(getComputedStyle(t).fontSize)'))
        self.assertEqual(title.get_attribute('title'), title.text_content())
        # Titles start with the country, omit the source and join series with an ampersand.
        self.assertRegex(title.text_content(), r'^USA: ')
        self.assertNotRegex(title.text_content(), r'\(|/|BEA|FED|BLS')
        self.assertIn(' & ', title.text_content())
        # The subtitle is shown in parentheses.
        self.assertEqual(figure.locator('.sub').evaluate('s => getComputedStyle(s, "::before").content + getComputedStyle(s, "::after").content'), '"(" ")"'.replace(' ', ''))
        # Rule 2: inside the card only title, subtitle and the period tiles precede the chart.
        tiles = figure.locator('.period-controls').bounding_box()
        chart = page.locator('#bbchart').bounding_box()
        subtitle = figure.locator('.sub').bounding_box()
        self.assertGreaterEqual(tiles['y'], subtitle['y'] + subtitle['height'])
        self.assertLess(chart['y'] - (tiles['y'] + tiles['height']), 24)
        self.assertLess(tiles['y'] - (subtitle['y'] + subtitle['height']), 24)
        for selector in ('#board-transform', '#board-transform-seasonal'):
            control = page.locator(selector).bounding_box()
            self.assertLessEqual(control['x'] + control['width'], box['x'])
        # The left panel does not list the "Documentada" status of each series.
        self.assertNotIn('Documentada', page.locator('.bbside').inner_text())
        expect(page.locator('.bbside [data-status=documented]').first).to_be_hidden()
        expect(figure.locator('.csv-action')).to_have_count(0)
        csv_button = page.locator('#bb-csv .csv-action').bounding_box()
        # The CSV download sits below the whole chart card, aligned to its right edge.
        self.assertGreaterEqual(csv_button['y'], box['y'] + box['height'])
        self.assertAlmostEqual(csv_button['x'] + csv_button['width'], box['x'] + box['width'], delta=2)
        expect(page.locator('.board-head .csv-action')).to_have_count(0)
        with page.expect_download():
            page.locator('#bb-csv .csv-action').click()
        # Chart types sit on the Blackboard heading row, not in the left panel.
        heading = page.locator('.board-head h2').bounding_box()
        modes = page.locator('.board-head [data-bbm]')
        expect(modes).to_have_count(8)
        expect(page.locator('.bbside [data-bbm]')).to_have_count(0)
        first_mode = modes.first.bounding_box()
        self.assertLess(first_mode['y'], heading['y'] + heading['height'])
        self.assertGreater(first_mode['y'] + first_mode['height'], heading['y'])
        # The chart types start right above the chart card, as grey tiles.
        self.assertAlmostEqual(first_mode['x'], box['x'], delta=2)
        pressed = page.locator('.board-head [data-bbm][aria-pressed=true]')
        idle = page.locator('.board-head [data-bbm][aria-pressed=false]').first
        self.assertEqual(idle.evaluate('b => getComputedStyle(b).backgroundColor'), 'rgb(243, 245, 246)')
        self.assertEqual(pressed.evaluate('b => getComputedStyle(b).backgroundColor'), 'rgb(0, 19, 145)')
        self.assertEqual(pressed.evaluate('b => getComputedStyle(b).color'), 'rgb(255, 255, 255)')
        # The period tiles keep the shared dashboard style.
        self.assertEqual(figure.locator('.seg button[aria-pressed=false]').first.evaluate('b => getComputedStyle(b).backgroundColor'), 'rgb(243, 245, 246)')
        # "Choose dates" follows the last period tile instead of sitting at the far right.
        last_tile = figure.locator('.seg button').last.bounding_box()
        choose = figure.locator('.chart-date-range summary').bounding_box()
        self.assertLess(choose['x'] - (last_tile['x'] + last_tile['width']), 16)
        # Rule 3: a plain legend (swatch and name) below the plot, at full width.
        plot = page.locator('#bbchart .chart-plot').bounding_box()
        readings = page.locator('#bbchart .chart-readings').bounding_box()
        self.assertGreaterEqual(readings['y'], plot['y'] + plot['height'])
        self.assertAlmostEqual(readings['width'], plot['width'], delta=2)
        # The "En pantalla / Datos disponibles" line is not shown.
        expect(figure.locator('.date-coverage')).to_be_hidden()
        self.assertLess(readings['height'], 60)
        expect(page.locator('#bbchart .chart-reading-label')).to_have_count(3)
        for hidden in ('.chart-reading-value', '.chart-readings time', '.chart-reading-source'):
            expect(page.locator(f'#bbchart {hidden}').first).to_be_hidden()
        page.locator('#bbchart svg').first.hover()
        expect(page.locator('#bbchart .chart-reading-value').first).to_be_visible()
        # Two axes: no "Izq./Dcha." above the axes and no mode name in the subtitle;
        # units read left axis first, then right axis.
        page.locator('[data-bbm=dual]').click()
        expect(page.locator('#bbchart [data-axis-tick=right]').first).to_be_visible()
        expect(page.locator('#bbchart [data-axis-label]')).to_have_count(0)
        self.assertEqual(figure.locator('.sub').text_content(), 'Chained 2017 USD · Billions of USD · Index 2017=100')
        expect(page.locator('#bbchart .chart-reading-label').first).to_contain_text('(eje izq.)')
        page.locator('[data-bbax]').nth(2).click()
        self.assertEqual(figure.locator('.sub').text_content(), 'Chained 2017 USD · Index 2017=100 · Billions of USD')
        self.assertRegex(figure.locator('h3').text_content(), r'^USA: Real GDP, Industrial Production Index & Personal Consumption Expenditures$')
        page.locator('[data-bbax]').nth(2).click()
        # The scatterplot keeps the menus in the left panel too.
        page.locator('[data-bbm=scatter]').click()
        expect(page.locator('.bbside #board-transform')).to_be_visible()
        expect(page.locator('figure.bbfig #board-transform')).to_have_count(0)

    def test_home_starts_with_summary_and_forecasts(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        for lang, open_label, pending in (('es', 'Ver monitor', 'En preparación'), ('en', 'View dashboard', 'Coming soon')):
            with self.subTest(lang=lang):
                page.goto(f'{ORIGIN}/index.html')
                page.locator(f'[data-lang={lang}]').click()
                cards = page.locator('.card')
                expect(cards).to_have_count(12)
                expect(cards.first.locator('.country')).to_have_text('Summary & Forecasts')
                expect(cards.first.locator('.status')).to_have_text(open_label)
                expect(page.locator('.card.featured .status')).to_have_text([open_label] * 4)
                self.assertEqual(page.locator('.card.featured .country').all_text_contents()[1], 'USA')
                expect(page.locator('.card:not(.featured) .status')).to_have_text([pending] * 8)
                # Three full rows of four tiles.
                boxes = [card.bounding_box() for card in cards.all()]
                self.assertEqual(len({round(box['y']) for box in boxes}), 3)
        cards.first.click()
        expect(page).to_have_url(re.compile(r'/summary\.html\?lang=en$'))
        expect(page.locator('h1')).to_have_text('Summary & Forecasts')

    def test_summary_and_forecasts_page(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/summary.html?lang=es')
        tabs = page.get_by_role('tab')
        expect(tabs).to_have_text(['Summary', 'Forecasts'])
        expect(tabs.first).to_have_attribute('aria-selected', 'true')
        summary = page.locator('#panel-summary')
        expect(page.locator('#panel-forecasts')).to_be_hidden()
        expect(summary.locator('tbody tr[data-geo]')).to_have_count(10)
        usa = summary.locator('tr[data-geo=usa] td')
        # GDP 2025, 2026, 2027 · inflation · policy rate, as published by BBVA Research.
        self.assertEqual([cell.strip() for cell in usa.all_inner_texts()],
                         ['2,10', '2,40▲', '2,20●', '2,80', '3,20●', '2,40●', '3,75', '4,25●', '4,25●'])
        expect(usa.nth(1).locator('.risk')).to_have_attribute('title', 'Al alza')
        self.assertEqual(summary.locator('tr[data-geo=espana] td').nth(6).inner_text().strip(), '—')
        self.assertEqual(summary.locator('tr[data-geo=turquia] td').nth(2).inner_text().strip(), '—')
        expect(summary).to_contain_text('Materias primas')
        expect(summary.locator('a[href="https://www.bbvaresearch.com/previsiones/"]')).to_be_visible()

        tabs.nth(1).click()
        forecasts = page.locator('#panel-forecasts')
        expect(summary).to_be_hidden()
        expect(forecasts.locator('[data-geo-pick]')).to_have_count(11)
        expect(forecasts.locator('h2')).to_have_text('Estados Unidos')
        expect(forecasts.locator('tbody tr')).to_have_count(7)
        forecasts.get_by_role('button', name='Argentina').click()
        expect(forecasts.locator('.sub')).to_contain_text('25 ago 2026')
        row = forecasts.locator('tbody tr', has_text='Tipo de cambio ARS/USD (fdp)')
        self.assertEqual(row.locator('td').all_inner_texts(), ['1.032,50', '1.459,40', '1.665,00', 'Al alza', '2.082,00', 'Al alza'])
        forecasts.get_by_role('button', name='Materias primas').click()
        expect(forecasts.locator('tbody tr')).to_have_count(3)

        page.locator('[data-lang=en]').click()
        expect(forecasts.locator('tbody tr').first).to_contain_text('Brent oil price')
        expect(forecasts.locator('tbody tr').first).to_contain_text('90.10')
        page.reload()
        expect(page.get_by_role('tab').nth(1)).to_have_attribute('aria-selected', 'true')

    def test_usa_confidence_bands(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/usa.html?lang=es#explorador')
        self.assert_blackboard(page, 'es')
        page.get_by_role('button', name='Confidence Bands', exact=True).click()
        minis = page.locator('#bbchart .bbmini')
        expect(minis).to_have_count(3)
        first = minis.first
        expect(first.locator('.chart-bands rect')).to_have_count(2)
        stats = first.locator('.chart-bands').evaluate('g => ({mean: +g.dataset.mean, sd: +g.dataset.sd, n: +g.dataset.n})')
        # Recompute mean and sample standard deviation from the CSV of the same chart.
        with page.expect_download() as download:
            first.locator('.csv-action').click()
        with open(download.value.path(), encoding='utf-8-sig', newline='') as downloaded:
            reader = csv.DictReader(downloaded, delimiter=';')
            value_column = 'Valor' if 'Valor' in reader.fieldnames else 'Value'
            values = [float(row[value_column].replace('.', '').replace(',', '.')) for row in reader]
        self.assertEqual(len(values), stats['n'])
        mean = sum(values) / len(values)
        sd = (sum((v - mean) ** 2 for v in values) / (len(values) - 1)) ** 0.5
        self.assertAlmostEqual(stats['mean'], mean, delta=abs(mean) * 1e-6)
        self.assertAlmostEqual(stats['sd'], sd, delta=sd * 1e-6)
        # The two bands are centred on the mean and the outer one is twice as tall.
        inner = first.locator('[data-band="1"]').bounding_box()
        outer = first.locator('[data-band="2"]').bounding_box()
        mean_line = first.locator('[data-band="mean"]').bounding_box()
        self.assertAlmostEqual(outer['height'], 2 * inner['height'], delta=1.5)
        self.assertAlmostEqual(mean_line['y'], inner['y'] + inner['height'] / 2, delta=1.5)
        expect(first.locator('.band-key')).to_contain_text('±2σ')
        expect(first.locator('[data-band-z]')).to_contain_text('σ')
        # Two columns, never one full-width chart.
        a, b = minis.nth(0).bounding_box(), minis.nth(1).bounding_box()
        self.assertAlmostEqual(a['y'], b['y'], delta=1)
        self.assertLess(a['x'] + a['width'], b['x'])

    def test_usa_series_menu_lists_only_the_main_categories(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        for lang, expected in (
            ('es', ['Actividad (3)', 'Empleo (3)', 'Precios (2)', 'Monetario (3)', 'Fiscal (0)', 'Exterior (0)', 'Vivienda (0)']),
            ('en', ['Activity (3)', 'Employment (3)', 'Prices (2)', 'Monetary (3)', 'Fiscal (0)', 'External (0)', 'Housing (0)']),
        ):
            with self.subTest(lang=lang):
                page.goto(f'{ORIGIN}/usa.html?lang={lang}#explorador')
                self.assert_blackboard(page, lang)
                groups = page.locator('.bbside .bbcatalog [data-catalog-group]')
                expect(groups.locator('> summary')).to_have_text(expected)
                # No nested subcategories: series hang directly from each category.
                expect(page.locator('.bbside [data-catalog-group] [data-catalog-group]')).to_have_count(0)
                groups.nth(3).locator('> summary').click()
                expect(groups.nth(3).locator('[data-catalog-pick]')).to_have_count(3)

    def test_other_blackboards_keep_their_layout(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        for name in ('espana', 'turquia'):
            with self.subTest(page=name):
                page.goto(f'{ORIGIN}/{name}.html?lang=es#explorador')
                self.assert_blackboard(page, 'es')
                page.locator('[data-bbm=lines]').click()
                expect(page.locator('figure.bbfig')).to_have_count(0)
                expect(page.locator('#bb-csv')).to_have_count(0)
                expect(page.locator('.bbside [data-bbm]')).to_have_count(7)
                expect(page.locator('[data-bbm=bands]')).to_have_count(0)
                expect(page.locator('#bbchart .chart-reading-value').first).to_be_visible()
                expect(page.locator('figure.fig #board-transform')).to_be_visible()
                expect(page.locator('figure.fig > .figure-csv-header .csv-action')).to_be_visible()

    def test_transform_and_seasonality_share_a_row(self):
        page = self.start_page()
        for width in (1180, 390, 320):
            with self.subTest(width=width):
                page.set_viewport_size({'width': width, 'height': 900})
                page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
                self.assert_blackboard(page, 'en')
                for mode in ('lines', 'scatter'):
                    page.locator(f'[data-bbm={mode}]').click()
                    transform = page.locator('#board-transform').bounding_box()
                    seasonal = page.locator('#board-transform-seasonal').bounding_box()
                    self.assertAlmostEqual(transform['y'], seasonal['y'], delta=1)
                    self.assertLess(transform['x'] + transform['width'], seasonal['x'])
                    self.assertLessEqual(seasonal['x'] + seasonal['width'], width)

    def test_employment_yoy_is_kept_when_the_level_is_transformed_to_qoq(self):
        page = self.start_page()
        page.add_init_script("""
            localStorage.setItem('mme-bb', JSON.stringify({
                mode:'dual', picks:['ocup_epa_yoy','ocup_epa'], tr:'qoq', adjustment:'raw'
            }))
        """)
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        select = page.locator('#board-transform')
        expect(select).to_have_value('qoq')
        expect(page.locator('[data-status=kept]')).to_contain_text('Year-on-year change')
        expect(page.locator('[data-status=calculated]')).to_have_count(1)
        with page.expect_download() as pending:
            page.locator('.figure-csv-header .csv-action').click()
        with pending.value.path().open(encoding='utf-8-sig', newline='') as downloaded:
            units = {row['Transformation']: row['Unit'] for row in csv.DictReader(downloaded)}
        self.assertEqual(len(units), 2)
        self.assertIn('yoy', units)
        self.assertTrue(any(key.startswith('Calculated here') for key in units))
        page.locator('[data-bbm=scatter]').click()
        expect(page.locator('[data-status=kept]')).to_contain_text('Year-on-year change')
        page.locator('[data-bbm=dual]').click()
        page.evaluate("bb.picks=['ocup_epa_yoy']; render()")
        expect(select).to_have_value('original')
        expect(select.locator('option[value=qoq]')).to_be_disabled()

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
