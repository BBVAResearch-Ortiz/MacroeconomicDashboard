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
