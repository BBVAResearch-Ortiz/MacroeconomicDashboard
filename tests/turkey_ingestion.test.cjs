const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const snapshot = name => JSON.parse(readFileSync(path.join(root, 'drive_ingestion/snapshots', name + '.json'), 'utf8')).series;
const series = snapshot('turkey');

test('the published Türkiye snapshot contains sourced observations and excludes workbook examples', () => {
  assert.ok(Object.keys(series).length > 0);
  for (const entries of [series, snapshot('turkey-verified')]) {
    for (const [id, entry] of Object.entries(entries)) {
      assert.doesNotMatch(entry.fuente, /Turkey_example_data\.xlsx/i, id);
      assert.equal(new URL(entry.source_url).protocol, 'https:', id);
      assert.ok(entry.observaciones.length > 0, id);
    }
  }
});

test('Apps Script strips examples before publishing a mixed workbook', () => {
  const script = readFileSync(path.join(root, 'drive_ingestion/apps_script/UploadToDashboard.gs'), 'utf8');
  const filter = vm.runInNewContext(script + '\nexcludeTurkeyExample_', {
    Utilities: {
      DigestAlgorithm: {SHA_256:'SHA_256'},
      Charset: {UTF_8:'UTF_8'},
      computeDigest: () => [],
      base64Encode: () => ''
    }
  });
  const [id, official] = Object.entries(series)[0];
  const input = {series: {[id]:official, example:{fuente:'Turkey_example_data.xlsx · Monthly!M', observaciones:[['2026-01-01', 100]]}}};
  const filtered = filter(input);
  assert.deepEqual(Object.keys(filtered.series), [id]);
  assert.equal(filtered.series[id], official);
  assert.equal(filtered.count, official.observaciones.length);
});
