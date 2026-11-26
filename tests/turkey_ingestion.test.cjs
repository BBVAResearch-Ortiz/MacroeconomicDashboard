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

test('the trade bulletin reads its monthly rows and checks the reference period and units', () => {
  const script = readFileSync(path.join(root, 'drive_ingestion/apps_script/UploadTurkeyData.gs'), 'utf8');
  const { read, readBec, link } = vm.runInNewContext(script + '\n({read:readTurkeyTrade_,readBec:readTurkeyTradeBec_,link:turkeyTradeWorkbookLink_})');
  const rows = [
    ['Dış Ticaret Verileri (Milyon Dolar)'],
    ['Dış Ticaret', '', 'İhracat', 'İthalat', 'Dış Ticaret Hacmi', 'Dış Ticaret Dengesi', 'İhr./ İth. (%)'],
    ['Ekim', 2025, 17, 20, 37, -3, 85],
    ['', 2026, 24, 30, 54, -6, 80],
    ['Ocak-Ekim', 2026, 240, 300, 540, -60, 80]
  ];
  const input = [['01-Ana Rakam Dış Ticaret', rows]];
  const result = read(input, 2026, 10);
  assert.equal(JSON.stringify(result[3]), JSON.stringify([['2025-10-01', -3], ['2026-10-01', -6]]));
  assert.throws(() => read(input, 2025, 10), /años/);
  rows[3][5] = 6;
  assert.throws(() => read(input, 2026, 10), /inconsistentes/);
  const official = 'https://ticaret.gov.tr/data/123abc/01_Ana_Rakam.XLSX';
  assert.equal(link(`<a href="${official}">Reporte</a>`), official);
  const becUrl = 'https://ticaret.gov.tr/data/123abc/09_GEG_İhr.XLSX';
  assert.equal(link(`<a href="${becUrl}">Reporte</a>`, '09'), 'https://ticaret.gov.tr/data/123abc/09_GEG_%C4%B0hr.XLSX');
  assert.throws(() => link('<a href="https://example.org/data/123abc/01_Ana_Rakam.XLSX">Reporte</a>'), /único Excel/);
  const becRows = [
    ['Geniş Ekonomik Grupların Sınıflamasına Göre İhracat (Milyon Dolar)'],
    ['GEG Kodu', 'GEG Açıklaması', 'Ocak-Ekim', '', 'Ekim'],
    ['', '', 2025, 2026, 2025, 2026],
    [1, 'Capital', 100, 110, 10, 11], [2, 'Intermediate', 200, 220, 20, 22],
    [3, 'Consumer', 300, 330, 30, 33], [4, 'Other', 400, 440, 40, 44]
  ];
  const bec = readBec([['GEG', becRows]], 2026, 10, 'genis ekonomik gruplarin siniflamasina gore ihracat');
  assert.equal(JSON.stringify(bec[3]), JSON.stringify([['2025-10-01', 40], ['2026-10-01', 44]]));
});
