const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const script = fs.readFileSync(path.join(root, 'series_transforms.js'), 'utf8');
const transforms = vm.runInNewContext(script + '\nSERIES_TRANSFORMS');
const snapshot = JSON.parse(fs.readFileSync(path.join(root, 'drive_ingestion/snapshots/spain.json'), 'utf8'));
const dates = [
  ['2025-01-01', 100], ['2025-02-01', 105],
  ['2026-01-01', 117], ['2026-02-01', 115]
];

function sourceSeries(label, metadata = {}) {
  return {label, data:dates, unit:'índice', freq:'M', ...metadata};
}

function spainCatalogue(codes) {
  return transforms.catalogue(codes.map(code => {
    const source = snapshot.series[code];
    return ['drive_es_' + code, {
      code,
      label: source.titulo_serie,
      original_name: source.subtitulo_descripcion,
      transform: source.transformacion_y_calculo,
      family: source.bloque,
      unit: source.unidad,
      freq: 'M',
      data: source.observaciones
    }];
  }), 'board');
}

function resolve(id, kind, catalogue, adjustment, baseDate) {
  return transforms.resolve(id, kind, catalogue, 0, Infinity, true, baseDate, adjustment);
}

test('the seasonal selector has two choices and treats unspecified series as unadjusted', () => {
  assert.deepEqual(Object.keys(transforms.adjustments), ['raw', 'adjusted']);
  const catalogue = transforms.catalogue([
    ['unknown', sourceSeries('Indicator')],
    ['adjusted', sourceSeries('Adjusted indicator', {original_name:'Datos ajustados de estacionalidad y calendario'})],
    ['unadjusted', sourceSeries('Not seasonally adjusted indicator')]
  ], 'board');
  assert.equal(resolve('unknown', 'original', catalogue, 'raw').origin, 'unknown');
  assert.equal(resolve('unknown', 'original', catalogue, 'adjusted').status, 'unavailable');
  assert.equal(resolve('adjusted', 'original', catalogue, 'adjusted').origin, 'adjusted');
  assert.equal(resolve('adjusted', 'original', catalogue, 'raw').status, 'unavailable');
  assert.equal(resolve('unadjusted', 'original', catalogue, 'raw').origin, 'unadjusted');
});

test('Spanish IPI switches between equivalent levels and reuses the published adjusted growth', () => {
  const catalogue = spainCatalogue(['IPI_GEN_RAW', 'IPI_GEN_CVEC_BBVA', 'IPI_GEN_CVEC_INE', 'IPI_GEN_CVEC_INE_AA']);
  const raw = 'drive_es_IPI_GEN_RAW';
  const adjusted = 'drive_es_IPI_GEN_CVEC_INE';
  assert.equal(resolve(raw, 'original', catalogue, 'adjusted').origin, adjusted);
  assert.equal(resolve(adjusted, 'original', catalogue, 'raw').origin, raw);
  assert.equal(resolve(raw, 'yoy', catalogue, 'adjusted').origin, 'drive_es_IPI_GEN_CVEC_INE_AA');
  assert.equal(resolve('drive_es_IPI_GEN_CVEC_INE_AA', 'original', catalogue, 'raw').status, 'unavailable');
});

test('Base 100 uses the chosen variant and base date', () => {
  const catalogue = spainCatalogue(['IASS_GEN_RAW', 'IASS_GEN_CVEC']);
  const id = 'drive_es_IASS_GEN_RAW';
  const selected = 'drive_es_IASS_GEN_CVEC';
  const date = catalogue.byId.get(selected).series.data.find(([, value]) => value > 0)[0];
  const result = resolve(id, 'b100', catalogue, 'adjusted', date);
  assert.equal(result.origin, selected);
  assert.equal(result.baseDate, date);
  assert.equal(result.series.data.find(([day]) => day === date)[1], 100);
});

test('quarterly growth sums monthly flows and uses end-of-quarter values for stocks', () => {
  const budget = 'TR_HMB_BUDGET_M_REVENUE';
  const loans = 'TR_BDDK_M_LOANS';
  const data = [10, 20, 30, 30, 20, 40].map((value, i) => [`2025-0${i + 1}-01`, value]);
  const catalogue = transforms.catalogue([budget, loans].map(code => [
    'drive_tr_' + code, sourceSeries(code, {code, data, unit:'Millones de TRY', source:'Official source'})
  ]), 'board');
  const flow = resolve('drive_tr_' + budget, 'qoq', catalogue);
  const stock = resolve('drive_tr_' + loans, 'qoq', catalogue);
  assert.equal(flow.status, 'calculated');
  assert.equal(flow.series.data[0][0], '2025-04-01');
  assert.equal(flow.series.data[0][1], 50);
  assert.ok(Math.abs(stock.series.data[0][1] - 100 / 3) < 1e-9);
  assert.match(flow.series.transform, /^Calculated here.*Sum of the three months/);
  assert.match(stock.series.transform, /Level in the last month/);
  assert.equal(flow.series.source, 'Official source');
});

test('differences of published growth rates use percentage points and keep the source', () => {
  const catalogue = transforms.catalogue([
    ['growth', sourceSeries('Published growth', {unit:'Var. a/a (%)', source:'Statistics office'})]
  ], 'board');
  const change = resolve('growth', 'delta', catalogue);
  assert.equal(change.series.unit, 'pp');
  assert.equal(change.series.data[0][1], 5);
  assert.equal(change.series.data[1][1], 12);
  assert.equal(change.series.source, 'Statistics office');
  assert.match(change.series.transform, /previous available observation/);
  assert.equal(resolve('growth', 'mom', catalogue).status, 'unavailable');
});

test('published employment growth stays interannual even when the matching level can be transformed', () => {
  const source = JSON.parse(fs.readFileSync(path.join(root, 'data.json'), 'utf8')).series;
  const catalogue = transforms.catalogue(['ocup_epa', 'ocup_epa_yoy'].map(id => [id, source[id]]), 'board');
  const result = resolve('ocup_epa_yoy', 'qoq', catalogue);
  assert.equal(result.status, 'unavailable');
  assert.equal(result.publishedFallback.origin, 'ocup_epa_yoy');
  assert.equal(result.publishedFallback.series, source.ocup_epa_yoy);
  assert.equal(resolve('ocup_epa', 'qoq', catalogue).status, 'calculated');
  assert.equal(resolve('ocup_epa', 'yoy', catalogue).origin, 'ocup_epa_yoy');
});

test('published monthly rates produce means across three or twelve consecutive months', () => {
  const data = Array.from({length:14}, (_,i) => [new Date(Date.UTC(2025,i,1)).toISOString().slice(0,10),i+1]);
  const catalogue = transforms.catalogue([
    ['mom', sourceSeries('Monthly growth', {unit:'% m/m', data})],
    ['gap', sourceSeries('With a missing month', {unit:'% m/m', data:data.filter((_,i)=>i!==1)})],
    ['qoq', sourceSeries('Quarterly growth', {unit:'% q/q', freq:'Q', data})]
  ], 'board');
  const quarter = resolve('mom', 'qoq', catalogue);
  assert.equal(quarter.series.freq, 'Q');
  assert.equal(quarter.series.unit, '% m/m');
  assert.equal(quarter.series.data[0][1], 2);
  assert.match(quarter.series.label, /Quarterly average/);
  const year = resolve('mom', 'yoy', catalogue);
  assert.equal(year.series.freq, 'M');
  assert.equal(year.series.data[0][0], '2025-12-01');
  assert.equal(year.series.data[0][1], 6.5);
  assert.equal(resolve('gap', 'qoq', catalogue).series.data[0][0], '2025-04-01');
  assert.equal(resolve('gap', 'yoy', catalogue).series.data.length, 1);
  assert.equal(resolve('qoq', 'mom', catalogue).status, 'unavailable');
  assert.equal(resolve('qoq', 'yoy', catalogue).status, 'unavailable');
});

test('the current account ratio compares quarter ends in percentage points', () => {
  const source = JSON.parse(fs.readFileSync(path.join(root, 'data.json'), 'utf8')).series.cc_pib;
  const catalogue = transforms.catalogue([['cc_pib', source]], 'board');
  const result = resolve('cc_pib', 'qoq', catalogue);
  assert.equal(result.status, 'calculated');
  assert.equal(result.series.freq, 'Q');
  assert.equal(result.series.unit, 'pp');
  assert.equal(result.series.source, source.source);
  assert.equal(resolve('cc_pib', 'mom', catalogue).status, 'unavailable');
  assert.match(result.series.transform, /last month of each quarter.*percentage points/);
  const byQuarter = new Map(result.series.data.map(([day, value]) => [day, value]));
  assert.ok(Math.abs(byQuarter.get('2026-04-01') - (2.70 - 3.16)) < 1e-9);
  assert.equal(byQuarter.has('2026-07-01'), false);
});

test('a published quarterly rate wins and a quarterly-only series has no monthly result', () => {
  const data = [['2025-01-01', 100], ['2025-04-01', 110]];
  const catalogue = transforms.catalogue([
    ['pib_yoy', sourceSeries('GDP annual growth', {data, unit:'% a/a', freq:'Q'})],
    ['pib_qoq', sourceSeries('GDP quarterly growth', {data, unit:'%', freq:'Q'})],
    ['quarterly_ratio', sourceSeries('Unemployment rate', {data, unit:'%', freq:'Q'})]
  ], 'board');
  const published = resolve('pib_yoy', 'qoq', catalogue);
  assert.equal(published.origin, 'pib_qoq');
  assert.equal(published.status, 'documented');
  assert.equal(resolve('quarterly_ratio', 'mom', catalogue).status, 'unavailable');
  assert.equal(resolve('quarterly_ratio', 'qoq', catalogue).series.data[0][1], 10);
});

test('weekly banking stocks can be compared month to month using the last reported value', () => {
  const date = (month, day) => `2025-${month}-${day}`;
  const days = ['03', '10', '17', '24', '31'].map(day => date('01', day))
    .concat(['07', '14', '21', '28'].map(day => date('02', day)), ['07', '14', '21'].map(day => date('03', day)));
  const data = days.map((day, i) => [day, 100 + i]);
  const id = 'drive_tr_TR_BDDK_W_LOANS';
  const catalogue = transforms.catalogue([[id, sourceSeries('Bank loans', {
    code:'TR_BDDK_W_LOANS', unit:'Millones de TRY', freq:'W', data
  })]], 'board');
  const result = resolve(id, 'mom', catalogue);
  assert.equal(result.status, 'calculated');
  assert.equal(result.series.data.length, 1);
  assert.equal(result.series.data[0][0], '2025-02-01');
  assert.ok(Math.abs(result.series.data[0][1] - 100 * (108 / 104 - 1)) < 1e-9);
});

test('growth falls back to the underlying level if the published rate misses the chosen period', () => {
  const catalogue = transforms.catalogue([
    ['paro_reg', sourceSeries('Unemployment', {unit:'miles'})],
    ['paro_reg_yoy', sourceSeries('Published growth', {unit:'% a/a', data:[['2025-01-01', 20]]})]
  ], 'board');
  assert.equal(resolve('paro_reg', 'yoy', catalogue).origin, 'paro_reg_yoy');
  const result = transforms.resolve('paro_reg', 'yoy', catalogue, Date.parse('2026-01-01'), Infinity, true);
  assert.equal(result.status, 'calculated');
  assert.equal(result.origin, 'paro_reg');
  assert.ok(Math.abs(result.series.data[0][1] - 17) < 1e-9);
});
