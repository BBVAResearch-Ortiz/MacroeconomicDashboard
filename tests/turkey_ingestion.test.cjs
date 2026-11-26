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

test('a ministry timeout imports the verified trade series without overwriting saved revisions', () => {
  const script = readFileSync(path.join(root, 'drive_ingestion/apps_script/UploadTurkeyData.gs'), 'utf8');
  const verified = snapshot('turkey-verified');
  const calls = [];
  const fetch = vm.runInNewContext(script + '\nfetchTurkeyTrade_', {
    dashboardDate_: value => /^\d{4}-\d{2}-\d{2}$/.test(value),
    UrlFetchApp: {
      fetch(url) {
        calls.push(url);
        if (url.endsWith('turkey-verified.json')) {
          return { getResponseCode: () => 200, getContentText: () => JSON.stringify({series: verified}) };
        }
        throw Error('Tiempo de espera');
      }
    }
  });
  const id = 'TR_TRADE_M_EXPORTS';
  const latest = verified[id].observaciones.at(-1)[0];
  const saved = {[id]: {...verified[id], observaciones: [[latest, 999]]}};
  const rows = fetch('2026-11-26', saved);
  assert.equal(rows.length, 23);
  const points = Object.entries(verified).filter(([key]) => key.startsWith('TR_TRADE_M_'))
    .reduce((total, [, row]) => total + row.observaciones.length, 0);
  assert.equal(rows.flatMap(row => row.data).length, points - 1);
  assert.ok(rows.every(row => row.entry.source_url.startsWith('https://ticaret.gov.tr/')));
  assert.ok(rows.find(row => row.id === id).data.every(([day]) => day !== latest));
  assert.equal(calls.length, 3);
  assert.match(calls[0], /^https:\/\/dabm\.ticaret\.gov\.tr\//);
});

test('trade history validates consecutive months and the expected publication month', () => {
  const script = readFileSync(path.join(root, 'drive_ingestion/apps_script/UploadTurkeyData.gs'), 'utf8');
  const read = vm.runInNewContext(script + '\nreadTurkeyTradeHistory_');
  const header = [
    ['Aylara Göre Dış Ticaret (Milyon Dolar)'],
    ['Yıl', 'AY', 'İhracat', 'İthalat', 'Hacim', 'Denge', 'Karşılama Oranı(%)']
  ];
  const rows = [['Monthly', [...header, [2013, 1, 10, 15, 25, -5, 66.7], [2013, 2, 20, 15, 35, 5, 133.3]]]];
  assert.equal(JSON.stringify(read(rows, '2013-02-01')[3]), JSON.stringify([['2013-01-01', -5], ['2013-02-01', 5]]));
  assert.throws(() => read(rows, '2013-03-01'), /omite el mes/);
  rows[0][1][3][1] = 3;
  assert.throws(() => read(rows, '2013-03-01'), /falta o se repite/);
});

test('weekly BDDK rejects incorrect sectors and selects the total of the requested indicator', () => {
  const script = readFileSync(path.join(root, 'drive_ingestion/apps_script/UploadTurkeyData.gs'), 'utf8');
  const {chart, bulletin} = vm.runInNewContext(script + '\n({chart:readTurkeyWeeklyBank_,bulletin:readTurkeyWeeklyBulletin_})', {
    dashboardDate_: () => true
  });
  const report = {Baslik:'Tüketici Kredileri (TRY) [Toplam] [Sektör]', XEkseni:['20.11.2026'], YEkseni:[1234]};
  assert.equal(chart(report, '2026-11-26', 'Tüketici Kredileri')[0][1], 1234);
  assert.throws(() => chart({...report, Baslik:report.Baslik.replace('Sektör', 'Bankalar')}, '2026-11-26', 'Tüketici Kredileri'));
  const row = `Milyon TL <td data-label="TOPLAM" onclick="ShowModalGraph('1.0.3','TRY',3)">1.234,5</td>`;
  assert.equal(bulletin(row, '20.11.2026', '2026-11-26', '1.0.3')[1], 1234.5);
  assert.throws(() => bulletin(row, '20.11.2026', '2026-11-26', '1.0.4'));
});

test('the central government budget converts thousands of TRY and excludes totals and future months', () => {
  const script = readFileSync(path.join(root, 'drive_ingestion/apps_script/UploadTurkeyData.gs'), 'utf8');
  const read = vm.runInNewContext(script + '\nreadTurkeyBudget_');
  const report = ['Bütçe Gelir Tabloları', 'gelirleri', [['REVENUE', 'Budget revenue', 'merkezi yonetim gelirleri']]];
  const months = 'Ocak Şubat Mart Nisan Mayıs Haziran Temmuz Ağustos Eylül Ekim Kasım Aralık'.split(' ');
  const rows = [['', '2026 YILI MERKEZİ YÖNETİM BÜTÇE GELİRLERİ'], ['', '(Bin TL)'],
    ['', '', ...months, 'TOPLAM'], ['', 'Merkezi Yönetim Gelirleri', 2000, 3500, ...Array(10).fill(''), 5500]];
  assert.equal(JSON.stringify(read([['Detay2',rows]],report,2026,'2026-01-29')), JSON.stringify([[['2026-01-01',2]]]));
  rows[1][1] = '(Milyon TL)';
  assert.throws(() => read([['Detay2',rows]],report,2026,'2026-01-29'), /unidad distinta/);
});

test('cleaning the Türkiye master removes exact example IDs and keeps adjacent official observations', () => {
  const script = readFileSync(path.join(root, 'drive_ingestion/apps_script/UploadTurkeyData.gs'), 'utf8');
  const { prune, remove } = vm.runInNewContext(script + '\n({prune:turkeyWithoutExamples_,remove:turkeyDeleteRuns_})');
  const rows = [['date', 'series_id', 'value'], ['2026-01-01', 'example', 1], ['2026-02-01', 'example', 2],
    ['2026-01-01', 'official', 42], ['2026-03-01', 'example', 3], ['2026-02-01', 'official', 43]];
  const result = prune(rows, new Set(['example']));
  assert.equal(JSON.stringify(result.rows), JSON.stringify([rows[0], rows[3], rows[5]]));
  const actual = rows.slice(), calls = [];
  const sheet = {deleteRows(start, count) { calls.push([start, count]); actual.splice(start - 1, count); }};
  remove(sheet, result.removed, 'deleteRows');
  assert.deepEqual(calls, [[5, 1], [2, 2]]);
  assert.equal(JSON.stringify(actual), JSON.stringify(result.rows));
});

test('auxiliary sheets lose example rows and columns while preserving official data', () => {
  const script = readFileSync(path.join(root, 'drive_ingestion/apps_script/UploadTurkeyData.gs'), 'utf8');
  const clean = vm.runInNewContext(script + '\ncleanTurkeyAuxiliary_');
  const sheet = (id, name, rows) => ({
    getSheetId: () => id, getName: () => name, rows,
    getDataRange: () => ({getValues: () => rows.map(row => row.slice())}),
    deleteRows(start, count) { rows.splice(start - 1, count); },
    deleteColumns(start, count) { rows.forEach(row => row.splice(start - 1, count)); }
  });
  const dictionary = sheet(1, 'DICTIONARY', [['series_id'], ['example'], ['official']]);
  const data = sheet(2, 'LONG_DATA', [['series_id'], ['example'], ['official']]);
  const activity = sheet(3, 'GDP_EXPENDITURE', [['series_id'], ['example']]);
  const coverage = sheet(4, 'COVERAGE', [['series_id', 'n'], ['example', 3], ['official', 2]]);
  const panel = sheet(5, 'KEY_PANEL', [['date', 'example', 'official'], ['2026-01-01', 8, 22]]);
  const readme = sheet(6, 'README', [['Master'], ['Source: Turkey_example_data.xlsx'], ['Editor note']]);
  const tabs = [dictionary, data, activity, coverage, panel, readme];
  clean({getSheets: () => tabs.slice(), deleteSheet(tab) { tabs.splice(tabs.indexOf(tab), 1); }},
    dictionary, data, new Set(['example']));
  assert.deepEqual(tabs.map(tab => tab.getName()), ['DICTIONARY', 'LONG_DATA', 'COVERAGE', 'KEY_PANEL', 'README']);
  assert.deepEqual(dictionary.rows, [['series_id'], ['example'], ['official']]);
  assert.deepEqual(coverage.rows, [['series_id', 'n'], ['official', 2]]);
  assert.deepEqual(panel.rows, [['date', 'official'], ['2026-01-01', 22]]);
  assert.deepEqual(readme.rows, [['Master'], ['Editor note']]);
});
