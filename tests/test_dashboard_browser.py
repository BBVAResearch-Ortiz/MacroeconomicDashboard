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
        expect(page.locator('.board-head [data-bbm]')).to_have_count(8)
        expect(page.locator('.bbside [data-bbm]')).to_have_count(0)
        for mode in ('dual', 'bars', 'stack', 'scatter', 'heat', 'multiples', 'bands', 'lines'):
            with self.subTest(mode=mode):
                button = page.locator(f'[data-bbm="{mode}"]')
                button.click()
                expect(button).to_have_attribute('aria-pressed', 'true')
                chart = '#bbchart table' if mode == 'heat' else '#bbchart svg'
                expect(page.locator(chart).first).to_be_visible()
                if mode == 'bands':
                    expect(page.locator('#bbchart .chart-bands').first).to_be_visible()
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
            S().drive_es_test_right=series('Narrow scale', [['2025-01-01',0.037],['2025-02-01',0.041],['2025-11-01',0.043]]);
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
        left_y = chart.locator('[data-axis-tick=left]').evaluate_all("(ticks) => ticks.map(tick => Number(tick.getAttribute('y')))")
        right_y = chart.locator('[data-axis-tick=right]').evaluate_all("(ticks) => ticks.map(tick => Number(tick.getAttribute('y')))")
        self.assertEqual(len(left_y), len(right_y))
        for left, right in zip(left_y, right_y):
            self.assertAlmostEqual(left, right)
        svg.press('ArrowLeft')
        expect(svg.locator('#dots circle')).to_have_count(2)
        page.locator('.chart-range [data-r="6m"]').click()
        expect(chart.locator('[data-axis-label=left]')).to_have_count(0)
        expect(chart.locator('[data-axis-label=right]')).to_have_text('Right')
        expect(chart.locator('path[data-axis=right]')).to_have_count(1)
        expect(page.locator('[data-bbax=drive_es_test_left]')).to_have_text('Left axis')

    def test_heat_map_keeps_months_when_quarterly_series_are_selected(self):
        page = self.start_page()
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        page.evaluate("""() => {
            const monthly = 'drive_es_heat_monthly', quarterly = 'drive_es_heat_quarterly';
            S()[monthly]={label:'Monthly sample',block:'actividad',freq:'M',unit:'%',
                data:[['2025-02-01',5],['2025-03-01',6],['2025-06-01',7]]};
            S()[quarterly]={label:'Quarterly sample',block:'actividad',freq:'Q',unit:'%',
                data:[['2025-01-01',10],['2025-04-01',20]]};
            Object.assign(bb,{picks:[monthly,quarterly],mode:'heat',tr:'original',heatExampleLoaded:true});
            state.range='todo';
            render();
        }""")
        heat = page.locator('#bbchart .bbheat')
        expect(heat.locator('thead th[title]')).to_have_count(6)
        quarter = heat.get_by_role('row').filter(has_text='Quarterly sample')
        titles = quarter.locator('td').evaluate_all('(cells) => cells.map(cell => cell.title)')
        self.assertIn('2025-02-01', titles[1])
        self.assertTrue(all(title.endswith('z=-0.71') for title in titles[:3]))
        self.assertTrue(all(title.endswith('z=0.71') for title in titles[3:]))
        expect(page.locator('#bbchart')).to_contain_text('Quarterly values repeated in each month')

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

    def test_spain_header_is_compact_and_tabs_wrap_only_when_needed(self):
        page = self.start_page(viewport={'width': 1440, 'height': 900})
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        expect(page.locator('.mast .lede')).to_be_hidden()
        expect(page.locator('.mast #stamp')).to_be_hidden()
        self.assertLessEqual(page.locator('.mast #liveMsg').bounding_box()['height'], 1)
        tabs = page.get_by_role('tablist')
        expect(tabs.get_by_role('tab')).to_have_count(14)
        row_counts = []
        for width in (1440, 390):
            with self.subTest(width=width):
                page.set_viewport_size({'width': width, 'height': 900})
                layout = tabs.evaluate("""bar => {
                    const style = getComputedStyle(bar);
                    const right = bar.getBoundingClientRect().right - parseFloat(style.paddingRight);
                    const gap = parseFloat(style.columnGap);
                    const buttons = [...bar.querySelectorAll('[role=tab]')].map(tab => tab.getBoundingClientRect());
                    return {
                        rows: new Set(buttons.map(box => box.top)).size,
                        overflow: bar.scrollWidth > bar.clientWidth,
                        wrappedEarly: buttons.some((box, i) => i && box.top > buttons[i-1].top
                            && buttons[i-1].right + gap + box.width < right - 1)
                    };
                }""")
                row_counts.append(layout['rows'])
                self.assertFalse(layout['wrappedEarly'])
                self.assertFalse(layout['overflow'])
        self.assertGreater(row_counts[1], row_counts[0])
        page.locator('#tab-resumen').press('ArrowLeft')
        expect(page.locator('#tab-fuentes')).to_be_focused()

    def test_category_tabs_preserve_direct_links(self):
        for country, first, second in (
            ('espana', 'actividad', 'exterior'),
            ('turquia', 'exterior', 'fiscal'),
            ('usa', 'actividad', 'empleo'),
        ):
            with self.subTest(country=country):
                page = self.start_page()
                page.goto(f'{ORIGIN}/{country}.html?lang=es#{first}')
                expect(page.locator('#tab-indicadores')).to_have_count(0)
                expect(page.locator(f'#tab-{first}')).to_have_attribute('aria-selected', 'true')
                expect(page.locator('#panel')).to_have_attribute('aria-labelledby', f'tab-{first}')
                target = page.locator(f'#tab-{second}')
                target.click()
                expect(target).to_have_attribute('aria-selected', 'true')
                expect(page.locator('#panel .chart svg').first).to_be_visible()
                figure = page.locator('#panel figure.fig').first
                csv = figure.locator(':scope > .figure-csv-footer .csv-action')
                expect(csv).to_be_enabled()
                expect(csv).to_have_css('font-size', '10px')
                self.assertGreaterEqual(csv.bounding_box()['y'], figure.locator('figcaption').bounding_box()['y'])
                expect(page).to_have_url(re.compile(f'#{second}$'))
                page.reload()
                expect(target).to_have_attribute('aria-selected', 'true')

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
        expect(page.locator('[data-bbm]')).to_have_count(8)
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
        csv_button = page.locator('.board-figure > .figure-csv-footer .csv-action')
        expect(analysis.locator('.csv-action')).to_have_count(0)
        with page.expect_download() as pending:
            csv_button.click()
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
            (['IPI_GEN_RAW', 'IPI_GEN_CVEC_INE'], re.compile(r'^Spain: IPI.*general index$', re.I)),
            (['IPI_GEN_RAW', 'IPI_ENE_RAW'], re.compile(r'^Spain: IPI.*general index & IPI.*energy$', re.I)),
            (['IPI_GEN_RAW', 'BC_EXP_CAPITAL_BRUTO'], 'Spain: Activity & External'),
        ]
        for picks, expected in cases:
            with self.subTest(picks=picks):
                page.evaluate("(ids) => {bb.picks=ids.map(id=>'drive_es_'+id); viewBoard();}", picks)
                expect(title).to_have_text(expected)

    def test_blackboard_chart_keeps_its_expanded_height(self):
        page = self.start_page(viewport={'width': 1440, 'height': 900})
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        expect(page.get_by_role('button', name='Download PNG')).to_have_count(0)
        expect(page.get_by_role('button', name='Download CSV')).to_be_enabled()
        self.assertGreater(page.locator('#bbchart svg').bounding_box()['height'], 500)

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

    def test_ipi_csv_keeps_the_source_for_the_selected_series(self):
        page = self.start_page()
        page.goto(f'{ORIGIN}/espana.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        page.wait_for_function("Boolean(S().drive_es_IPI_GEN_RAW)")
        page.evaluate("""localStorage.setItem('mme-bb', JSON.stringify({
            picks:['drive_es_IPI_GEN_CVEC_INE'], tr:'original', adjustment:'raw'
        }))""")
        page.reload()
        self.assert_blackboard(page, 'en')
        expect(page.locator('#board-transform-seasonal')).to_have_count(0)
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

    def test_transform_fits_the_sidebar_without_a_seasonal_selector(self):
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
                    expect(sidebar.get_by_label('Seasonal adjustment')).to_have_count(0)
                    self.assertLessEqual(transform['x'] + transform['width'], width)

    def test_spain_catalogue_groups_all_workbook_series_under_activity_and_external(self):
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
            'Activity': {'Large enterprises': 53, 'Services activity (IASS)': 16,
                         'Industrial production (IPI)': 30, 'ESI': 21, 'PMI': 3},
            'Employment': {},
            'Prices': {},
            'Monetary': {},
            'Financial': {},
            'Fiscal': {},
            'External': {'Trade balance': 22},
            'Housing': {},
        })
        depths = page.evaluate('exIds().map(id => explorerPath(id).length)')
        self.assertLessEqual(max(depths), 3)
        self.assertEqual(len(catalogue['ids']), 145)
        self.assertTrue(all(key.startswith('drive_es_') for key in catalogue['ids']))
        self.assertTrue(catalogue['picks'] and all(key.startswith('drive_es_') for key in catalogue['picks']))
        page.locator('#explorer-search').fill('EPA387796')
        expect(page.locator('#explorer-search-results')).to_contain_text('No matching series.')
        expect(page.locator('#tab-empleo')).to_be_visible()

    def test_big_data_catalogue_and_csv_footer(self):
        page = self.start_page()
        page.goto(f'{ORIGIN}/espana.html?lang=en#bigdata')
        expect(page.locator('#big-chart svg').first).to_be_visible()
        expect(page.locator('.figure-csv-footer #big-csv')).to_be_enabled()
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
                expect(page.locator('.board-head [data-bbm]')).to_have_count(8)
                expect(page.locator('.bbside [data-bbm]')).to_have_count(0)
                page.locator('[data-bbm=bands]').click()
                expect(page.locator('#bbchart .chart-bands').first).to_be_visible()
                expect(page.locator('#bbchart .band-key [data-band-z]').first).to_contain_text('Latest')

    def test_turkiye_keeps_verified_data_when_the_workbook_contains_only_examples(self):
        page = self.start_page()
        example = {'series': {'EXAMPLE': {'fuente': 'Turkey_example_data.xlsx · Monthly!M'}}}
        page.route('**/snapshots/turkey.json', lambda route: route.fulfill(json=example))
        page.goto(f'{ORIGIN}/turquia.html?lang=en#explorador')
        self.assert_blackboard(page, 'en')
        expect(page.locator('#foot .stamp')).to_contain_text('series')
        self.assertTrue(page.evaluate("Object.hasOwn(S(), 'drive_tr_TR_HMB_M_CASH_BALANCE')"))
        self.assertTrue(page.evaluate("Object.hasOwn(S(), 'drive_tr_TR_TUIK_M_HS_71_EXPORTS')"))
        expect(page.locator('#foot a')).to_have_count(4)
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
        expect(page.locator('#foot .stamp')).to_contain_text('series')
        points = page.evaluate("DATA.series.drive_tr_TR_TRADE_M_EXPORTS.data")
        self.assertEqual(len(points), 166)
        self.assertEqual(points[0][:2], ['2013-01-01', 12263])
        self.assertEqual(points[-1][:2], ['2026-10-01', 25885])

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
        control = page.locator('#board-transform').bounding_box()
        self.assertLessEqual(control['x'] + control['width'], box['x'])
        expect(page.locator('#board-transform-seasonal')).to_have_count(0)
        expect(figure.locator('.period-controls [data-r]')).to_have_text(['6m', '1a', '4a', 'Todo'])
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
        expect(page.locator('[data-bbax]')).to_have_count(0)
        page.locator('.bbsel .row').nth(2).locator('[data-bb-move="-1"]').click()
        self.assertEqual(figure.locator('.sub').text_content(), 'Chained 2017 USD · Index 2017=100 · Billions of USD')
        self.assertRegex(figure.locator('h3').text_content(), r'^USA: Real GDP, Industrial Production Index & Personal Consumption Expenditures$')
        page.locator('.bbsel .row').nth(1).locator('[data-bb-move="1"]').click()
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

    def test_usa_models_include_the_new_york_fed_dsge(self):
        published = json.loads((ROOT / 'dsge_frbny.json').read_text(encoding='utf-8'))
        current, previous = published['table']['current'], published['table']['previous']
        number = lambda value: f'{round(value, 1) + 0:.1f}'.replace('.', ',')
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/usa.html?lang=es#modelos')
        tiles = page.locator('#model-tiles .model-tile')
        expect(tiles.locator('h2')).to_have_text(['FRB/US', 'DSGE FRB-NY', 'GDPNow', 'CPI Nowcasting'])
        page.locator('[data-open-model=dsge]').click()
        detail = page.locator('#model-dsge')
        expect(detail).to_be_visible()
        expect(page.locator('#model-gdpnow')).to_be_hidden()
        expect(detail.locator('#dsge-headline strong')).to_have_text(
            [f"{number(current['rows'][key][0][0])} %" for key in ('gdp', 'core_pce', 'rstar')])
        expect(detail.locator('#dsge-stamp')).to_contain_text('18 de septiembre de 2026')
        expect(detail).to_contain_text('aquí no se ejecuta el modelo')
        expect(detail.locator('#dsge-source')).to_have_attribute('href', published['source_url'])
        # A 2 x 3 gallery that opens with the two forecast-comparison charts.
        cards = detail.locator('#dsge-gallery > .card')
        expect(cards).to_have_count(6)
        self.assertEqual([cards.nth(i).get_attribute('data-dsge-chart') for i in range(6)],
                         ['rev-gdp', 'rev-core_pce', 'gdp', 'core_pce', 'rstar', 'effect'])
        boxes = [cards.nth(i).bounding_box() for i in range(6)]
        self.assertEqual(len({round(box['y']) for box in boxes}), 3)
        self.assertEqual(len({round(box['x']) for box in boxes}), 2)
        # The shock simulator sits to the right of the first box, on the same row.
        summary = detail.locator('.dsge-top > .gdp-detail').bounding_box()
        simulator_box = detail.locator('#dsge-sim').bounding_box()
        self.assertAlmostEqual(summary['y'], simulator_box['y'], delta=1)
        self.assertLessEqual(summary['x'] + summary['width'], simulator_box['x'])
        self.assertLess(simulator_box['y'] + simulator_box['height'], boxes[0]['y'])
        expect(detail.locator('#dsge-table-host [data-dsge-chart=table]')).to_be_visible()
        self.assertLess(boxes[0]['x'] + boxes[0]['width'], boxes[1]['x'])
        # Bands are switchable; the default shows 50, 68 and 90 percent.
        gdp = detail.locator('[data-dsge-chart=gdp]')
        expect(gdp.locator('[data-dsge-band]')).to_have_count(3)
        detail.get_by_role('button', name='80 %', exact=True).click()
        expect(detail.locator('[data-dsge-chart=gdp] [data-dsge-band]')).to_have_count(4)
        expect(detail.get_by_role('button', name='80 %', exact=True)).to_be_focused()
        detail.get_by_role('button', name='80 %', exact=True).click()
        # Hovering the last quarter reads the published mean and 68 percent band.
        fan = published['fans']['gdp']
        hit = gdp.locator('[data-dsge-hit]')
        box = hit.bounding_box()
        hit.hover(position={'x': box['width'] - 1, 'y': box['height'] / 2})
        readout = gdp.locator('[data-dsge-readout]')
        last = fan['dates'][-1]
        quarter = f"T{(int(last[5:7]) + 2) // 3} {last[:4]}"
        low, high = fan['bands']['68'][-1]
        expect(readout).to_contain_text(f"{quarter} · previsión {number(fan['forecast'][-1])}")
        expect(readout).to_contain_text(f"68 %: {number(low)} a {number(high)}")
        page.mouse.move(5, 5)
        expect(readout).to_contain_text('Pasa el cursor')
        # The period switch adds the history back to 2021.
        short = gdp.locator('[data-dsge-history]').get_attribute('d')
        detail.get_by_role('button', name='Desde 2021').click()
        self.assertGreater(len(detail.locator('[data-dsge-chart=gdp] [data-dsge-history]').get_attribute('d')), len(short))
        for chart in ('rev-gdp', 'rev-core_pce'):
            expect(detail.locator(f'[data-dsge-chart="{chart}"] [data-dsge-previous]')).to_have_count(1)
        # Every figure of the published table appears unchanged, next to the previous release.
        for key in ('gdp', 'core_pce', 'rstar'):
            for index, year in enumerate(current['years']):
                cells = detail.locator(f'[data-dsge-row="{key}-{year}"] td').all_inner_texts()
                expected = [str(year)] + [f'{number(row[0])} ({number(row[1])}; {number(row[2])})'
                                          for row in (current['rows'][key][index], previous['rows'][key][index])]
                self.assertEqual([cell.strip() for cell in cells], expected)
        scroll = detail.locator('.dsge-scroll')
        self.assertLessEqual(scroll.evaluate('el => el.scrollWidth'), scroll.evaluate('el => el.clientWidth'))
        page.locator('[data-lang=en]').click()
        expect(detail.locator('[data-dsge-chart=gdp] h2')).to_have_text('GDP growth')
        expect(detail.locator('#dsge-stamp')).to_contain_text('18 September 2026')
        detail.locator('[data-close-model]').click()
        expect(page.locator('#model-tiles')).to_be_visible()
        # A direct link opens the model, like the other two.
        page.goto(f'{ORIGIN}/usa.html?lang=es#dsge')
        expect(page.locator('#model-dsge')).to_be_visible()

    def test_usa_model_pages_drop_the_section_heading(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/usa.html?lang=en#modelos')
        heading = page.locator('#usa-models-host .sechead h2')
        expect(heading).to_have_text('Tracking and simulation models')
        expect(heading).to_be_visible()
        for model in ('gdpnow', 'frbus', 'dsge', 'cpinow'):
            with self.subTest(model=model):
                page.locator(f'[data-open-model={model}]').click()
                expect(page.locator(f'#model-{model}')).to_be_visible()
                expect(heading).to_be_hidden()
                page.locator(f'#model-{model} [data-close-model]').first.click()
                expect(heading).to_be_visible()
                # A direct link to the model hides it too.
                page.goto(f'{ORIGIN}/usa.html?lang=en#{model}')
                expect(page.locator(f'#model-{model}')).to_be_visible()
                expect(heading).to_be_hidden()
                page.goto(f'{ORIGIN}/usa.html?lang=en#modelos')
                expect(heading).to_be_visible()

    def test_usa_dsge_shock_simulator(self):
        published = json.loads((ROOT / 'dsge_frbny.json').read_text(encoding='utf-8'))
        irf = json.loads((ROOT / 'dsge_irf.json').read_text(encoding='utf-8'))
        number = lambda value: f'{round(value, 1) + 0:.1f}'.replace('.', ',')
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/usa.html?lang=es#dsge')
        detail = page.locator('#model-dsge')
        simulator = detail.locator('#dsge-sim')
        expect(simulator).to_be_visible()
        expect(simulator.locator('.dsge-slider')).to_have_count(len(irf['shocks']))
        expect(simulator).to_contain_text('Cálculo propio con Model1002')
        expect(simulator).to_contain_text('No es una previsión ni un escenario de la Fed de Nueva York')
        expect(simulator).to_contain_text('ocurren en T4 2026')
        expect(detail.locator('[data-dsge-scenario]')).to_have_count(0)

        def set_shock(name, size):
            slider = simulator.locator(f'[data-dsge-shock={name}]')
            slider.evaluate('(el, v) => { el.value = v; el.dispatchEvent(new Event("input", {bubbles: true})); }', str(size))
            return slider

        slider = set_shock('monetary', 1)
        expect(simulator.locator('[data-dsge-size=monetary]')).to_have_text('+1,00 d. t.')
        # The slider survives the redraw and five charts gain a scenario line.
        self.assertEqual(slider.evaluate('el => el.value'), '1')
        expect(detail.locator('[data-dsge-scenario]')).to_have_count(5)

        def quarter(date):
            return f"T{(int(date[5:7]) + 2) // 3} {date[:4]}"

        def read(chart, index, total):
            hit = detail.locator(f'[data-dsge-chart="{chart}"] [data-dsge-hit]')
            box = hit.bounding_box()
            hit.hover(position={'x': min(box['width'] - 1, max(1, box['width'] * index / (total - 1))), 'y': box['height'] / 2})
            return detail.locator(f'[data-dsge-chart="{chart}"] [data-dsge-readout]')

        response = irf['shocks']['monetary']['responses']
        # Quarterly annualised GDP growth: forecast + 4 x response, from the quarter after the release.
        revision = published['revisions']['gdp']
        start = next(i for i, value in enumerate(revision['current']) if value is not None)
        first = max(0, start - 12)
        dates = revision['dates'][first:]
        shock = revision['dates'].index('2026-12-31')
        for horizon in (0, 3):
            index = shock + horizon
            expected = revision['current'][index] + 4 * response['gdp_q'][horizon]
            readout = read('rev-gdp', index - first, len(dates))
            expect(readout).to_contain_text(quarter(revision['dates'][index]))
            expect(readout).to_contain_text(f'escenario {number(expected)}')
        # Four-quarter GDP growth: forecast + the sum of the last four quarterly responses.
        fan = published['fans']['gdp']
        start = next(i for i, value in enumerate(fan['forecast']) if value is not None)
        first = max(0, start - 12)
        index = fan['dates'].index('2027-09-30')
        horizon = index - fan['dates'].index('2026-12-31')
        expected = fan['forecast'][index] + sum(response['gdp_q'][horizon - lag] for lag in range(4))
        expect(read('gdp', index - first, len(fan['dates']) - first)).to_contain_text(f'escenario {number(expected)}')
        # No scenario value before the shock, and the natural rate does not react to monetary policy.
        before = read('gdp', fan['dates'].index('2026-09-30') - first, len(fan['dates']) - first)
        self.assertNotIn('escenario', before.inner_text())
        natural = published['fans']['rstar']
        index = natural['dates'].index('2027-03-31')
        expect(read('rstar', index - first, len(natural['dates']) - first)).to_contain_text(
            f"escenario {number(natural['forecast'][index])}")
        # Shocks add up: the rate effect is the sum of both responses.
        set_shock('credit_spread', -2)
        both = 4 * (response['ffr_q'][0] - 2 * irf['shocks']['credit_spread']['responses']['ffr_q'][0])
        effect_dates = fan['dates'][fan['dates'].index('2026-12-31') - 1:]
        expect(read('effect', 1, len(effect_dates))).to_contain_text(f'tipo oficial {number(both)} pp')
        # Reset clears every slider and removes the scenario.
        simulator.get_by_role('button', name='Restablecer').click()
        expect(detail.locator('[data-dsge-scenario]')).to_have_count(0)
        self.assertEqual(simulator.locator('[data-dsge-shock=monetary]').evaluate('el => el.value'), '0')
        expect(simulator.locator('[data-dsge-size=monetary]')).to_have_text('0,00 d. t.')

    def test_usa_cpi_nowcasting_shows_cleveland_fed_figures(self):
        published = json.loads((ROOT / 'inflation_nowcast.json').read_text(encoding='utf-8'))
        number = lambda value, digits=1: f'{round(value, digits) + 0:.{digits}f}'.replace('.', ',')
        last = lambda values: [v for v in values if v is not None][-1]
        measures = ['cpi', 'core_cpi', 'pce', 'core_pce']
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/usa.html?lang=es#modelos')
        tiles = page.locator('#model-tiles .model-tile')
        expect(tiles).to_have_count(4)
        # Two tiles per row: FRB/US and DSGE first, GDPNow and CPI Nowcasting below.
        boxes = [tiles.nth(i).bounding_box() for i in range(4)]
        self.assertAlmostEqual(boxes[0]['y'], boxes[1]['y'], delta=1)
        self.assertAlmostEqual(boxes[2]['y'], boxes[3]['y'], delta=1)
        self.assertGreater(boxes[2]['y'], boxes[0]['y'] + boxes[0]['height'] - 1)
        self.assertAlmostEqual(boxes[0]['x'], boxes[2]['x'], delta=1)
        tiles.nth(3).click()
        detail = page.locator('#model-cpinow')
        expect(detail).to_be_visible()
        month = published['months'][-1]
        def headline(entry):
            return [number(entry['yy']['actual'][k]['value'] if entry['yy']['actual'].get(k) else last(entry['yy']['nowcast'][k])) + ' %' for k in measures]
        expect(detail.locator('#cpinow-headline strong')).to_have_text(headline(month))
        expect(detail.locator('#cpinow-source')).to_have_attribute('href', published['source_url'])
        cards = detail.locator('#cpinow-gallery > article')
        expect(cards).to_have_count(4)
        # Two-column gallery, never a full-width chart.
        first, second, third = (cards.nth(i).bounding_box() for i in range(3))
        self.assertAlmostEqual(first['y'], second['y'], delta=1)
        self.assertGreater(third['y'], first['y'])
        self.assertLess(first['width'], 620)
        expect(cards.nth(0).locator('[data-cpinow-line]')).to_have_count(4)
        # Hovering the last day shows the published nowcast for that day.
        hit = cards.nth(0).locator('[data-cpinow-hit]')
        box = hit.bounding_box()
        hit.hover(position={'x': box['width'] - 1, 'y': box['height'] / 2})
        expect(cards.nth(0).locator('[data-cpinow-readout]')).to_contain_text('CPI ' + number(month['yy']['nowcast']['cpi'][-1], 2) if month['yy']['nowcast']['cpi'][-1] is not None else 'CPI')
        # Track record: mean absolute error recomputed from the file.
        pairs = [(r['yy']['core_pce']['nowcast'], r['yy']['core_pce']['actual']) for r in published['track']]
        errors = [abs(a - b) for a, b in pairs if a is not None and b is not None]
        detail.locator('[data-cpinow-measure=core_pce]').click()
        expect(cards.nth(3).locator('h2')).to_contain_text('PCE subyacente')
        expect(cards.nth(3).locator('.note')).to_contain_text(f'{number(sum(errors) / len(errors), 2)} pp en {len(errors)} meses')
        # Switching the reference month changes the headline.
        earlier = published['months'][0]
        detail.locator(f'[data-cpinow-period="{earlier["period"]}"]').click()
        expect(detail.locator('#cpinow-headline strong')).to_have_text(headline(earlier))
        expect(detail.locator(f'[data-cpinow-period="{earlier["period"]}"]')).to_have_attribute('aria-pressed', 'true')

    def test_usa_cpi_nowcasting_reloads_a_newer_update(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        newer = json.loads((ROOT / 'inflation_nowcast.json').read_text(encoding='utf-8'))
        newer['updated'] = '2026-12-30'
        month = newer['months'][-1]
        month['yy']['actual']['cpi'] = None
        month['yy']['nowcast']['cpi'][-1] = 9.87
        page.route('**/inflation_nowcast.json', lambda route: route.fulfill(json=newer))
        page.goto(f'{ORIGIN}/usa.html?lang=en#cpinow')
        detail = page.locator('#model-cpinow')
        expect(detail.locator('#cpinow-headline strong').first).to_have_text('9.9 %')
        expect(detail.locator('#cpinow-stamp')).to_contain_text('30 December 2026')

    def test_usa_dsge_reloads_a_newer_release(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        newer = json.loads((ROOT / 'dsge_frbny.json').read_text(encoding='utf-8'))
        newer['table']['previous'] = newer['table']['current']
        newer['table']['current'] = json.loads(json.dumps(newer['table']['current']))
        newer['table']['current']['release'] = newer['release'] = '2026-12-11'
        newer['table']['current']['rows']['gdp'][0] = [9.9, 8.8, 11.1]
        page.route('**/dsge_frbny.json', lambda route: route.fulfill(json=newer))
        page.goto(f'{ORIGIN}/usa.html?lang=es#dsge')
        detail = page.locator('#model-dsge')
        expect(detail.locator('#dsge-headline strong').first).to_have_text('9,9 %')
        expect(detail.locator('#dsge-stamp')).to_contain_text('11 de diciembre de 2026')
        expect(detail.locator('.dsge-table thead th')).to_have_text(['Año', 'dic 2026', 'sept 2026'])

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
        snapshot = json.loads((ROOT / 'drive_ingestion' / 'snapshots' / 'usa.json').read_text(encoding='utf-8'))
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        for lang, names in (
            ('es', ['Actividad', 'Empleo', 'Precios', 'Monetario', 'Financiero', 'Fiscal', 'Exterior', 'Vivienda']),
            ('en', ['Activity', 'Employment', 'Prices', 'Monetary', 'Financial', 'Fiscal', 'External', 'Housing']),
        ):
            with self.subTest(lang=lang):
                page.goto(f'{ORIGIN}/usa.html?lang={lang}#explorador')
                self.assert_blackboard(page, lang)
                groups = page.locator('.bbside .bbcatalog [data-catalog-group]')
                labels = groups.locator('> summary').all_inner_texts()
                self.assertEqual([re.sub(r' \(\d+\)$', '', label) for label in labels], names)
                # Every series sits in exactly one category and there are no nested subcategories.
                counts = [int(re.search(r'\((\d+)\)$', label).group(1)) for label in labels]
                self.assertEqual(sum(counts), len(snapshot['series']))
                expect(page.locator('.bbside [data-catalog-group] [data-catalog-group]')).to_have_count(0)
                groups.nth(3).locator('> summary').click()
                expect(groups.nth(3).locator('[data-catalog-pick]')).to_have_count(counts[3])
                self.assertGreaterEqual(counts[3], 3)

    def test_usa_titles_follow_the_country_and_ampersand_rule(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/usa.html?lang=es#explorador')
        self.assert_blackboard(page, 'es')
        page.locator('.bbside [data-bbrm]').nth(2).click()
        title = page.locator('figure.bbfig h3')
        expected = 'USA: Real GDP & Personal Consumption Expenditures'
        for mode in ('lines', 'dual', 'bars', 'stack', 'scatter'):
            page.locator(f'[data-bbm={mode}]').click()
            for transformation in ('original', 'yoy', 'b100'):
                with self.subTest(mode=mode, transformation=transformation):
                    page.locator('#board-transform').select_option(transformation)
                    expect(page.locator('#bbchart svg').first).to_be_visible()
                    expect(title).to_have_text(expected)
            page.locator('#board-transform').select_option('original')

    def test_usa_dual_axis_ticks_share_the_grid(self):
        page = self.start_page(viewport={'width': 1180, 'height': 900})
        page.goto(f'{ORIGIN}/usa.html?lang=es#explorador')
        self.assert_blackboard(page, 'es')
        page.locator('[data-bbm=dual]').click()
        for transformation in ('original', 'yoy'):
            for period in ('1a', '4a', 'todo'):
                with self.subTest(transformation=transformation, period=period):
                    page.locator('#board-transform').select_option(transformation)
                    page.locator(f'figure.bbfig [data-r="{period}"]').click()
                    if transformation == 'yoy':
                        # The growth rates all share the same unit, so they use one axis.
                        expect(page.locator('#bbchart [data-axis-tick=right]')).to_have_count(0)
                        expect(page.locator('#bbchart path[data-axis=left]')).to_have_count(3)
                        continue
                    expect(page.locator('#bbchart [data-axis-tick=right]').first).to_be_visible()
                    marks = page.locator('#bbchart svg').first.evaluate("""svg => ({
                        left: [...svg.querySelectorAll('[data-axis-tick=left]')].map(t => +t.getAttribute('y')),
                        right: [...svg.querySelectorAll('[data-axis-tick=right]')].map(t => +t.getAttribute('y')),
                        rightText: [...svg.querySelectorAll('[data-axis-tick=right]')].map(t => t.textContent),
                        paths: [...svg.querySelectorAll('path[data-axis=right]')].map(p => p.getBBox()).map(b => [b.y, b.y + b.height]),
                        plot: (() => { const hit = svg.querySelector('#hit'); return [+hit.getAttribute('y'), +hit.getAttribute('y') + +hit.getAttribute('height')]; })(),
                    })""")
                    # Same number of ticks, at the same heights as the left axis.
                    self.assertEqual(len(marks['left']), len(marks['right']))
                    for left, right in zip(marks['left'], marks['right']):
                        self.assertAlmostEqual(left, right, delta=0.5)
                    self.assertEqual(len(set(marks['rightText'])), len(marks['rightText']))
                    # The right-axis series stays inside the plot area.
                    for top, bottom in marks['paths']:
                        self.assertGreaterEqual(top, marks['plot'][0] - 0.5)
                        self.assertLessEqual(bottom, marks['plot'][1] + 0.5)


if __name__ == '__main__':
    unittest.main()
