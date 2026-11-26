const TURKEY_PRODUCER = {
  timezone: 'Europe/Istanbul',
  treasuryPage: 'https://en.hmb.gov.tr/public-finance',
  treasuryCatalogue: 'https://en.hmb.gov.tr/portal/v2/pages?slug=public-finance',
  budgetPage: 'https://muhasebat.hmb.gov.tr/merkezi-yonetim-butce-istatistikleri',
  budgetApi: 'https://muhasebat.hmb.gov.tr/portal/v2/',
  weekly: 'https://www.bddk.org.tr/BultenHaftalik',
  monthly: 'https://www.bddk.org.tr/BultenAylik/tr/',
  trade: 'https://ticaret.gov.tr/istatistikler/bakanlik-istatistikleri/dis-ticaret-istatistikleri/',
  tradeMirror: 'https://dabm.ticaret.gov.tr',
  verified: 'https://bbvaresearch-ortiz.github.io/MacroeconomicDashboard/drive_ingestion/snapshots/turkey-verified.json',
  xls: 'application/vnd.ms-excel'
};

const TURKEY_CASH_ITEMS = [
  ['CASH_REVENUE', 'Treasury cash revenue', 'Revenues'],
  ['CASH_EXPENDITURE', 'Treasury cash expenditure', 'Expenditures'],
  ['CASH_BALANCE', 'Treasury cash balance', 'Cash balance']
];
const TURKEY_MONTH_NAMES = 'January February March April May June July August September October November December'.toLowerCase().split(' ');
const TURKEY_MONTHLY_REPORTS = [
  ['TR_BDDK_M_LOANS', 'Total bank loans', 3, 'Toplam Krediler'],
  ['TR_BDDK_M_DEPOSITS', 'Total bank deposits', 9, 'Toplam Mevduat']
];
const TURKEY_WEEKLY_REPORTS = [
  ['LOANS', 'Total bank loans', '1.0.1', 'Toplam Krediler'],
  ['CONSUMER_LOANS', 'Consumer loans', '1.0.3', 'Tüketici Kredileri'],
  ['HOUSING_LOANS', 'Housing loans', '1.0.4', 'Konut'],
  ['VEHICLE_LOANS', 'Vehicle loans', '1.0.5', 'Taşıt'],
  ['PERSONAL_LOANS', 'Personal loans', '1.0.6', 'İhtiyaç'],
  ['PERSONAL_CREDIT_CARDS', 'Personal credit card balances', '1.0.8', 'Bireysel Kredi Kartları'],
  ['COMMERCIAL_LOANS', 'Commercial and other loans', '1.0.12', 'Ticari ve Diğer Krediler'],
  ['SME_LOANS', 'SME loans', '1.0.11', 'KOBİ Kredileri']
];
const TURKEY_TRADE_MONTHS = 'ocak subat mart nisan mayis haziran temmuz agustos eylul ekim kasim aralik'.split(' ');
const TURKEY_TRADE_ITEMS = [
  ['EXPORTS', 'Goods exports', 'ihracat', 'Millones de USD'],
  ['IMPORTS', 'Goods imports', 'ithalat', 'Millones de USD'],
  ['TURNOVER', 'Goods trade volume', 'dis ticaret hacmi', 'Millones de USD'],
  ['BALANCE', 'Goods trade balance', 'dis ticaret dengesi', 'Millones de USD'],
  ['COVERAGE', 'Export-to-import ratio', 'ihr./ ith. (%)', '%']
];
const TURKEY_TRADE_FILES = [
  ['01', '', '', 'dis ticaret verileri'],
  ['09', 'BEC_EXPORTS', 'Goods exports', 'genis ekonomik gruplarin siniflamasina gore ihracat'],
  ['10', 'BEC_IMPORTS', 'Goods imports', 'genis ekonomik gruplarin siniflamasina gore ithalat'],
  ['14', 'EX_ENERGY', 'excluding energy', 'enerji haric dis ticaret verileri'],
  ['15', 'EX_GOLD', 'excluding gold', 'altin haric dis ticaret verileri']
];
const TURKEY_TRADE_BEC_GROUPS = ['Capital goods', 'Intermediate goods', 'Consumer goods', 'Other goods'];
const TURKEY_BUDGET_REPORTS = [
  ['Bütçe Gelir Tabloları', 'gelirleri', [
    ['REVENUE', 'Central government budget revenue', 'merkezi yonetim gelirleri'],
    ['GENERAL_REVENUE', 'General budget revenue', 'genel butce gelirleri'],
    ['TAX', 'Tax revenue', 'i-vergi gelirleri'],
    ['INCOME_TAX', 'Personal income tax', 'a) gelir vergisi'],
    ['CORPORATE_TAX', 'Corporate income tax', 'b) kurumlar vergisi'],
    ['DOMESTIC_VAT', 'Domestic VAT', 'a) dahilde alinan katma deger vergisi'],
    ['IMPORT_VAT', 'Import VAT', 'b) ithalde alinan katma deger vergisi'],
    ['EXCISE', 'Special consumption tax', 'b) ozel tuketim vergisi'],
    ['CUSTOMS_DUTIES', 'Customs duties', 'a) gumruk vergileri'],
    ['ENTERPRISE_PROPERTY', 'Enterprise and property revenue', 'ii-tesebbus ve mulkiyet gelirleri'],
    ['CAPITAL_REVENUE', 'Capital revenue', 'v-sermaye gelirleri']
  ]],
  ['Bütçe Gider Tabloları', 'giderleri', [
    ['EXPENDITURE', 'Central government budget expenditure', 'merkezi yonetim butce giderleri (a+b)'],
    ['NON_INTEREST', 'Non-interest expenditure', 'a) faiz haric butce giderleri'],
    ['PERSONNEL', 'Personnel expenditure', '1. personel giderleri'],
    ['SOCIAL_PREMIUMS', 'Government social insurance contributions', '2. sosyal guvenlik kurumlarina devlet primi giderleri'],
    ['GOODS_SERVICES', 'Purchases of goods and services', '3. mal ve hizmet alim giderleri'],
    ['CURRENT_TRANSFERS', 'Current transfers', '4. cari transferler'],
    ['CAPITAL_EXPENDITURE', 'Capital expenditure', '5. sermaye giderleri'],
    ['CAPITAL_TRANSFERS', 'Capital transfers', '6. sermaye transferleri'],
    ['LENDING', 'Lending', '7. borc verme'],
    ['INTEREST', 'Interest expenditure', 'b. faiz giderleri'],
    ['DOMESTIC_INTEREST', 'Domestic debt interest', 'a) ic borc faiz odemeleri'],
    ['FOREIGN_INTEREST', 'External debt interest', 'b) dis borc faiz odemeleri']
  ]]
];

function previewTurkeyWorkbook() {
  runTurkeyWorkbook_(false);
}

function syncTurkeyWorkbook() {
  runTurkeyWorkbook_(true);
}

function cleanTurkeyWorkbook() {
  runTurkeyWorkbook_(true, true);
}

function installTurkeyWorkbookTrigger() {
  const oldTriggers = ScriptApp.getProjectTriggers().filter(trigger => trigger.getHandlerFunction() === 'syncTurkeyWorkbook');
  ScriptApp.newTrigger('syncTurkeyWorkbook').timeBased().everyDays(1).atHour(19)
    .inTimezone(TURKEY_PRODUCER.timezone).create();
  oldTriggers.forEach(trigger => ScriptApp.deleteTrigger(trigger));
}

function runTurkeyWorkbook_(publish, cleanupOnly = false) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(20000)) throw new Error('Turquía: otra sincronización está en curso.');
  try {
    const config = DASHBOARD_UPLOAD;
    const folders = listDashboardFiles_(config.root, config.folder).filter(folder => folder.name === config.areas.turkey);
    if (folders.length !== 1) throw new Error('Turquía: no se encontró una única carpeta Turkiye.');
    const folder = folders[0];
    const books = listDashboardFiles_(folder.id, config.xlsx);
    const book = selectDashboardMaster_('turkey', books);
    if (!book || books.length !== 1) throw new Error('Turquía: la carpeta debe contener solo ' + config.masters.turkey.name + '.');
    const master = DriveApp.getFileById(book.id).getBlob();
    const today = Utilities.formatDate(new Date(), TURKEY_PRODUCER.timezone, 'yyyy-MM-dd');

    withDashboardSpreadsheet_(master, book.name, workbook => {
      const dictionary = workbook.getSheetByName('DICTIONARY') || workbook.getSheetByName('DICCIONARIO');
      const observations = workbook.getSheetByName('LONG_DATA') || workbook.getSheetByName('DATOS_LARGO');
      if (!dictionary || !observations) throw new Error('Turquía: faltan las pestañas del Excel madre.');
      const dictionaryRows = dictionary.getDataRange().getValues();
      const observationRows = observations.getDataRange().getValues();
      const timezone = workbook.getSpreadsheetTimeZone();
      const previous = parseDashboardSheets_(dictionaryRows, observationRows, timezone);
      const examples = new Set(Object.entries(previous.series)
        .filter(([, entry]) => /\bTurkey_example_data\.xlsx\b/i.test(entry.fuente || '')).map(([id]) => id));
      const cleanDictionary = turkeyWithoutExamples_(dictionaryRows, examples);
      const cleanObservations = turkeyWithoutExamples_(observationRows, examples);
      const sources = cleanupOnly ? [] : [
        ['Tesoro', () => fetchTurkeyTreasury_(today)],
        ['Presupuesto central · Detay2', () => {
          try {
            return fetchTurkeyBudget_(today, previous.series);
          } catch (error) {
            console.log('Presupuesto central · acceso directo incompleto: ' + error.message);
            return fetchTurkeyVerifiedSeries_(previous.series, [], today, 'Presupuesto central',
              (id, row) => id.startsWith('TR_HMB_BUDGET_M_') && row.source_url === TURKEY_PRODUCER.budgetPage);
          }
        }],
        ['BDDK semanal', () => fetchTurkeyWeekly_(today, previous.series)],
        ['BDDK mensual', () => fetchTurkeyMonthly_(today, previous.series)],
        ['Comercio exterior · cifras principales', () => fetchTurkeyTrade_(today, previous.series)]
      ];
      const errors = [];
      const updates = sources.flatMap(([name, fetch]) => {
        try {
          const series = fetch();
          console.log('Turquía · ' + name + ': ' + series.map(({ id, data }) =>
            id + ' (' + data.length + ', ' + data.at(-1)[0] + ')').join(', '));
          return series;
        } catch (error) {
          errors.push(name + ': ' + error.message);
          return [];
        }
      });

      if (updates.length || examples.size) {
        const pending = updates.length
          ? mergeTurkeyWorkbookRows_(cleanDictionary.rows, cleanObservations.rows, updates, timezone)
          : { dictionary: new Set(), observations: new Set() };
        const next = parseDashboardSheets_(cleanDictionary.rows, cleanObservations.rows, timezone);
        if (examples.size) console.log('Turquía · ejemplos retirados del maestro: ' + examples.size + ' series, ' +
          cleanObservations.removed.length + ' observaciones.');
        const changed = Object.keys(next.hashes).some(key => next.hashes[key] !== previous.hashes[key]);
        console.log('Turquía · Excel: ' + Object.keys(next.series).length + ' series, ' + next.count + ' observaciones. ' +
          (changed ? (publish ? 'Cambios para guardar.' : 'Vista previa con cambios.') : 'Sin cambios.'));
        if (publish && changed) {
          turkeyDeleteRuns_(dictionary, cleanDictionary.removed, 'deleteRows');
          turkeyDeleteRuns_(observations, cleanObservations.removed, 'deleteRows');
          if (examples.size) cleanTurkeyAuxiliary_(workbook, dictionary, observations, examples);
          writeTurkeyRows_(dictionary, cleanDictionary.rows, pending.dictionary);
          writeTurkeyRows_(observations, cleanObservations.rows, pending.observations);
          SpreadsheetApp.flush();
          const exported = UrlFetchApp.fetch('https://www.googleapis.com/drive/v3/files/' + workbook.getId() +
            '/export?mimeType=' + encodeURIComponent(config.xlsx), {
            headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() }, muteHttpExceptions: true
          });
          const output = turkeyResponse_(exported, 'Exportación a XLSX').getBlob().setName(book.name).setContentType(config.xlsx);
          const current = Drive.Files.get(book.id, { fields: 'id,version,md5Checksum', supportsAllDrives: true });
          if ((current.md5Checksum || current.version) !== (book.md5Checksum || book.version)) {
            throw new Error('Turquía: el Excel madre cambió durante la actualización. Se volverá a intentar en la próxima ejecución.');
          }
          const saved = Drive.Files.update({}, book.id, output, { fields: 'id,version', supportsAllDrives: true });
          console.log('Turquía · Excel guardado en Drive. ID: ' + saved.id + ' · versión: ' + saved.version);
        }
      } else if (cleanupOnly) console.log('Turquía · el maestro ya está limpio.');
      if (errors.length) throw new Error('Turquía · fuentes con errores:\n' + errors.join('\n'));
    });
  } finally {
    lock.releaseLock();
  }
}

function turkeyWithoutExamples_(rows, examples) {
  const column = rows[0]?.findIndex(value => value === 'series_id' || value === 'id_serie');
  const removed = [];
  const kept = rows.filter((row, i) => {
    if (!i || !examples.has(row[column])) return true;
    removed.push(i + 1);
    return false;
  });
  return { rows: kept, removed };
}

function turkeyDeleteRuns_(sheet, positions, method) {
  for (let i = positions.length - 1; i >= 0;) {
    const end = positions[i];
    let start = end;
    while (positions[--i] === start - 1) start--;
    sheet[method](start, end - start + 1);
  }
}

function cleanTurkeyAuxiliary_(workbook, dictionary, observations, examples) {
  for (const sheet of workbook.getSheets()) {
    if ([dictionary.getSheetId(), observations.getSheetId()].includes(sheet.getSheetId())) continue;
    const rows = sheet.getDataRange().getValues();
    const { rows: kept, removed } = turkeyWithoutExamples_(rows, examples);
    if (removed.length && kept.slice(1).every(row => row.every(value => value === ''))) {
      workbook.deleteSheet(sheet);
      continue;
    }
    turkeyDeleteRuns_(sheet, removed, 'deleteRows');
    if (/^(date|fecha)$/i.test(rows[0]?.[0])) {
      const columns = rows[0].flatMap((id, i) => examples.has(id) ? [i + 1] : []);
      if (columns.length && rows[0].slice(1).every(value => value === '' || examples.has(value))) {
        workbook.deleteSheet(sheet);
        continue;
      }
      turkeyDeleteRuns_(sheet, columns, 'deleteColumns');
    }
    if (/^(README|LEEME)$/i.test(sheet.getName())) {
      const notes = kept.flatMap((row, i) => i && row.some(value => /\bTurkey_example_data\.xlsx\b/i.test(String(value))) ? [i + 1] : []);
      turkeyDeleteRuns_(sheet, notes, 'deleteRows');
    }
  }
}

function turkeyResponse_(response, name) {
  if (response.getResponseCode() !== 200) throw new Error(name + ': HTTP ' + response.getResponseCode());
  return response;
}

function turkeySeries_(id, title, description, frequency, block, area, source, url, data, unit = 'Millones de TRY') {
  const byDate = new Map();
  for (const [date, value] of data) {
    if (!dashboardDate_(date, 'UTC') || !Number.isFinite(value) || byDate.has(date)) {
      throw new Error(id + ': fecha, valor o duplicado inválido (' + date + ').');
    }
    byDate.set(date, value);
  }
  if (!byDate.size) throw new Error(id + ': sin observaciones.');
  return {
    id, data: [...byDate].sort(([a], [b]) => a.localeCompare(b)), entry: {
      titulo_serie: title, subtitulo_descripcion: description,
      transformacion_y_calculo: 'Dato publicado en su frecuencia original.', fuente: source,
      frecuencia_y_cobertura_temporal: frequency, tipo_grafico: 'Line chart', bloque: block,
      'área': area, frecuencia: frequency, unidad: unit, source_url: url
    }
  };
}

function turkeyTradeText_(value) {
  return String(value).normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ı/g, 'i')
    .trim().toLowerCase().replace(/\s+/g, ' ');
}

function turkeyTradeWorkbookLink_(html, fileNumber = '01') {
  const pattern = /href\s*=\s*["'](https:\/\/ticaret\.gov\.tr\/data\/[a-f0-9]+\/(\d\d)_[^"'<>/#?]+\.xlsx)["']/gi;
  const matches = new Set([...html.matchAll(pattern)].filter(match => match[2] === fileNumber).map(match => match[1]));
  if (matches.size !== 1) throw new Error('No se encontró un único Excel para la tabla ' + fileNumber + '.');
  return encodeURI([...matches][0]).replace(/%25([a-f0-9]{2})/gi, '%$1');
}

function turkeyTradeRows_(sheets, heading) {
  const matches = sheets.filter(([, rows]) => rows.some(row => row.some(cell =>
    turkeyTradeText_(cell) === heading + ' (milyon dolar)')));
  if (matches.length !== 1) throw new Error('No se encontró una hoja del cuadro solicitado en millones de USD.');
  return matches[0][1];
}

function turkeyTradePoint_(year, month, value) {
  return [year + '-' + String(month).padStart(2, '0') + '-01', value];
}

function readTurkeyTrade_(sheets, year, month, heading = 'dis ticaret verileri') {
  const rows = turkeyTradeRows_(sheets, heading);
  const headers = TURKEY_TRADE_ITEMS.map(([, , label]) => label);
  const header = rows.find(row => headers.every(label => row.some(cell => turkeyTradeText_(cell) === label)));
  if (!header) throw new Error('Comercio exterior: faltan columnas del cuadro principal.');
  const columns = headers.map(label => header.findIndex(cell => turkeyTradeText_(cell) === label));
  const monthRow = rows.findIndex((row, index) => index > rows.indexOf(header) &&
    turkeyTradeText_(row[0]) === TURKEY_TRADE_MONTHS[month - 1]);
  const prior = rows[monthRow], current = rows[monthRow + 1];
  if (monthRow < 0 || !current || Number(prior[1]) !== year - 1 || Number(current[1]) !== year) {
    throw new Error('Comercio exterior: el mes o los años del Excel no coinciden con la publicación.');
  }
  for (const row of [prior, current]) {
    const [exports, imports, volume, balance, coverage] = columns.map(column => row[column]);
    if (![exports, imports, volume, balance, coverage].every(Number.isFinite) || exports < 0 || imports <= 0 ||
        Math.abs(volume - exports - imports) > 0.05 || Math.abs(balance - exports + imports) > 0.05 || coverage < 0) {
      throw new Error('Comercio exterior: cifras principales inconsistentes.');
    }
  }
  return columns.map(column => [turkeyTradePoint_(year - 1, month, prior[column]), turkeyTradePoint_(year, month, current[column])]);
}

function readTurkeyTradeBec_(sheets, year, month, heading) {
  const rows = turkeyTradeRows_(sheets, heading);
  const headerIndex = rows.findIndex(row => turkeyTradeText_(row[0]) === 'geg kodu');
  const monthColumn = headerIndex < 0 ? -1 : rows[headerIndex].findIndex(cell => turkeyTradeText_(cell) === TURKEY_TRADE_MONTHS[month - 1]);
  const years = rows[headerIndex + 1];
  if (monthColumn < 0 || Number(years?.[monthColumn]) !== year - 1 || Number(years?.[monthColumn + 1]) !== year) {
    throw new Error('Comercio exterior BEC: mes o años inesperados.');
  }
  return TURKEY_TRADE_BEC_GROUPS.map((_, index) => {
    const matched = rows.slice(headerIndex + 2).filter(row => Number(row[0]) === index + 1);
    if (matched.length !== 1) throw new Error('Comercio exterior BEC: falta la categoría ' + (index + 1) + ' o está duplicada.');
    const prior = matched[0][monthColumn], current = matched[0][monthColumn + 1];
    if (![prior, current].every(value => Number.isFinite(value) && value >= 0)) {
      throw new Error('Comercio exterior BEC: valor inválido para la categoría ' + (index + 1) + '.');
    }
    return [turkeyTradePoint_(year - 1, month, prior), turkeyTradePoint_(year, month, current)];
  });
}

function readTurkeyTradeHistory_(sheets, through) {
  const rows = turkeyTradeRows_(sheets, 'aylara gore dis ticaret');
  const headings = ['yil', 'ay', 'ihracat', 'ithalat', 'hacim', 'denge', 'karsilama orani(%)'];
  const header = rows.findIndex(row => headings.every((heading, index) => turkeyTradeText_(row[index]) === heading));
  if (header < 0) throw new Error('Comercio exterior: columnas inesperadas en el histórico.');
  const points = rows.slice(header + 1).filter(([year]) => Number.isInteger(year)).map(([year, month, ...values]) => {
    if (!Number.isInteger(month) || month < 1 || month > 12 || year < 2013 || values.length < 5 ||
        !values.slice(0, 5).every(Number.isFinite)) throw new Error('Comercio exterior: fila mensual inválida.');
    const day = turkeyTradePoint_(year, month, 0)[0];
    return [day, values.slice(0, 5)];
  }).filter(([day]) => day <= through).sort(([a], [b]) => a.localeCompare(b));
  let expected = '2013-01-01';
  for (const [day] of points) {
    if (day !== expected) throw new Error('Comercio exterior: falta o se repite el mes ' + expected + '.');
    const [year, month] = day.split('-').map(Number);
    expected = new Date(Date.UTC(year, month, 1)).toISOString().slice(0, 10);
  }
  if (points.at(-1)?.[0] !== through) throw new Error('Comercio exterior: el histórico omite el mes del boletín.');
  return TURKEY_TRADE_ITEMS.map((_, i) => points.map(([day, values]) => [day, values[i]]));
}

function loadTurkeyTradeHistory_(page, live, previous, year, month) {
  const summary = TURKEY_TRADE_ITEMS.map(([code]) => live.find(series => series.id === 'TR_TRADE_M_' + code));
  if (summary.some(series => !series)) return;
  if (summary.every(series => previous[series.id]?.observaciones[0]?.[0] === '2013-01-01')) return;
  const url = turkeyTradeWorkbookLink_(page.html, '02').replace('https://ticaret.gov.tr', page.host);
  const blob = turkeyResponse_(UrlFetchApp.fetch(url, { muteHttpExceptions: true }), 'Excel de comercio por mes')
    .getBlob().setContentType(DASHBOARD_UPLOAD.xlsx);
  const history = withDashboardSpreadsheet_(blob, 'Foreign trade by month', workbook => readTurkeyTradeHistory_(
    workbook.getSheets().map(sheet => [sheet.getName(), sheet.getDataRange().getValues()]), turkeyTradePoint_(year, month, 0)[0]));
  summary.forEach((series, i) => {
    const known = new Set([...(previous[series.id]?.observaciones || []), ...series.data].map(([day]) => day));
    series.data = [...history[i].filter(([day]) => !known.has(day)), ...series.data].sort(([a], [b]) => a.localeCompare(b));
  });
}

function fetchTurkeyTradeFile_(page, bulletin, file, year, month) {
  const [number, variant, qualifier, heading] = file;
  const url = turkeyTradeWorkbookLink_(page.html, number).replace('https://ticaret.gov.tr', page.host);
  const blob = turkeyResponse_(UrlFetchApp.fetch(url, { muteHttpExceptions: true }), 'Excel de comercio exterior ' + number)
    .getBlob().setContentType(DASHBOARD_UPLOAD.xlsx);
  const bec = variant.startsWith('BEC_');
  const data = withDashboardSpreadsheet_(blob, 'Foreign trade ' + number, workbook => {
    const sheets = workbook.getSheets().map(sheet => [sheet.getName(), sheet.getDataRange().getValues()]);
    return bec ? readTurkeyTradeBec_(sheets, year, month, heading) : readTurkeyTrade_(sheets, year, month, heading);
  });
  const catalogue = bec
    ? TURKEY_TRADE_BEC_GROUPS.map((group, i) => [variant + '_' + (i + 1), qualifier + ' · ' + group, '', 'Millones de USD'])
    : TURKEY_TRADE_ITEMS.map(([code, title, label, unit]) =>
      [variant ? variant + '_' + code : code, qualifier ? title + ' ' + qualifier : title, label, unit]);
  return catalogue.map(([code, title, , unit], i) => turkeySeries_(
    'TR_TRADE_M_' + code, title, 'General Trade System · Ministry of Trade monthly bulletin (preliminary for the latest reference month).',
    'Monthly', 'EXTERNAL_TRADE', 'external_sector', 'Ministerio de Comercio de Türkiye · Boletín de comercio exterior',
    bulletin, data[i], unit));
}

function fetchTurkeyTradePage_(bulletin) {
  const errors = [];
  for (const host of [TURKEY_PRODUCER.tradeMirror, 'https://ticaret.gov.tr']) {
    try {
      const url = bulletin.replace('https://ticaret.gov.tr', host);
      const html = turkeyResponse_(UrlFetchApp.fetch(url, { muteHttpExceptions: true }), 'Boletín de comercio exterior').getContentText();
      turkeyTradeWorkbookLink_(html);
      return { html, host };
    } catch (error) {
      errors.push(error.message);
    }
  }
  throw new Error(errors.join(' | '));
}

function fetchTurkeyVerifiedSeries_(previous, live, today, topic, accepts) {
  const response = turkeyResponse_(UrlFetchApp.fetch(TURKEY_PRODUCER.verified, { muteHttpExceptions: true }), 'Copia verificada de Türkiye');
  const records = JSON.parse(response.getContentText()).series || {};
  const byId = new Map(live.map(series => [series.id, series]));
  const verified = Object.entries(records).filter(([id, row]) => accepts(id, row));
  if (!verified.length) throw new Error('La copia verificada no contiene series de ' + topic + '.');
  let latest = '';
  for (const [id, row] of verified) {
    const current = byId.get(id), saved = previous[id];
    const known = new Set([...(saved?.observaciones || []), ...(current?.data || [])].map(([day]) => day));
    const data = row.observaciones.filter(([day]) => day <= today && !known.has(day));
    const verifiedDate = row.observaciones.at(-1)?.[0] || '';
    if (verifiedDate > latest) latest = verifiedDate;
    if (!data.length) continue;
    const verifiedSeries = turkeySeries_(id, row.titulo_serie, row.subtitulo_descripcion, 'Monthly', row.bloque, row['área'],
      row.fuente, row.source_url, data, row.unidad);
    if (row.transformacion_y_calculo) verifiedSeries.entry.transformacion_y_calculo = row.transformacion_y_calculo;
    const savedDate = saved?.observaciones?.at(-1)?.[0];
    const entry = current?.entry || (savedDate > verifiedDate ? saved : verifiedSeries.entry);
    byId.set(id, { id, entry, data: [...verifiedSeries.data, ...(current?.data || [])].sort(([a], [b]) => a.localeCompare(b)) });
  }
  console.log(topic + ' · copia verificada hasta ' + latest + '. Se conservan las observaciones ya guardadas.');
  return [...byId.values()];
}

function fetchTurkeyTrade_(today, previous = {}) {
  const [year, month] = today.split('-').map(Number);
  const errors = [];
  for (let offset = 1; offset <= 3; offset++) {
    const period = new Date(Date.UTC(year, month - 1 - offset, 1));
    const reportYear = period.getUTCFullYear(), reportMonth = period.getUTCMonth() + 1;
    const slug = TURKEY_TRADE_MONTHS[reportMonth - 1] + '-ayi-dis-ticaret-istatistik';
    const bulletin = TURKEY_PRODUCER.trade + slug + 'leri/' + slug + '-tablolari';
    let live = [];
    try {
      const page = fetchTurkeyTradePage_(bulletin);
      live = TURKEY_TRADE_FILES.flatMap(file => {
        try {
          return fetchTurkeyTradeFile_(page, bulletin, file, reportYear, reportMonth);
        } catch (error) {
          errors.push(file[0] + ': ' + error.message);
          return [];
        }
      });
      try {
        loadTurkeyTradeHistory_(page, live, previous, reportYear, reportMonth);
      } catch (error) {
        console.log('Comercio exterior · histórico: ' + error.message);
      }
      if (live.length === TURKEY_TRADE_ITEMS.length * 3 + TURKEY_TRADE_BEC_GROUPS.length * 2) return live;
    } catch (error) {
      errors.push(reportYear + '-' + String(reportMonth).padStart(2, '0') + ': ' + error.message);
    }
    if (offset === 1 || live.length) {
      console.log('Comercio exterior · acceso directo incompleto: ' + errors.join(' | '));
      try {
        return fetchTurkeyVerifiedSeries_(previous, live, today, 'Comercio exterior',
          (id, row) => /^TR_TRADE_M_[A-Z0-9_]+$/.test(id) && row.bloque === 'EXTERNAL_TRADE' && row.source_url?.startsWith(TURKEY_PRODUCER.trade));
      } catch (error) {
        errors.push(error.message);
      }
    }
    if (live.length) return live;
  }
  throw new Error(errors.join(' | '));
}

function turkeyBudgetGroup_(html, year) {
  const section = new RegExp(String.raw`data-name="${year} Merkezi Yönetim Konsolide Bütçe İstatistikleri"[^>]*>[^<]*</a>([\s\S]*?)(?=data-name="\d{4} |$)`, 'i');
  const block = html.match(section)?.[1] || '';
  return TURKEY_BUDGET_REPORTS.map(([label]) => {
    const id = new RegExp('data-name="' + label + '"\\s+data-id="(\\d+)"').exec(block)?.[1];
    if (!id) throw new Error('Presupuesto ' + year + ': falta ' + label + '.');
    return id;
  });
}

function readTurkeyBudget_(sheets, report, year, today) {
  const [, kind, items] = report;
  const title = year + ' yili merkezi yonetim butce ' + kind;
  const found = sheets.filter(([, rows]) => rows.some(row =>
    row.some(cell => turkeyTradeText_(cell).startsWith(title))));
  if (found.length !== 1) throw new Error('Presupuesto ' + year + ': título o año inesperado.');
  const rows = found[0][1];
  if (!rows.some(row => row.some(cell => turkeyTradeText_(cell) === '(bin tl)'))) {
    throw new Error('Presupuesto ' + year + ': unidad distinta de miles de TRY.');
  }
  const header = rows.find(row => TURKEY_TRADE_MONTHS.every(month => row.some(cell => turkeyTradeText_(cell) === month)));
  if (!header) throw new Error('Presupuesto ' + year + ': faltan los encabezados mensuales.');
  const columns = TURKEY_TRADE_MONTHS.map(month => header.findIndex(cell => turkeyTradeText_(cell) === month));
  return items.map(([, , label]) => {
    const matched = rows.filter(row => turkeyTradeText_(row[1]) === label);
    if (matched.length !== 1) throw new Error('Presupuesto ' + year + ': partida ausente o duplicada: ' + label);
    return columns.flatMap((column, i) => {
      const value = matched[0][column];
      const day = turkeyTradePoint_(year, i + 1, 0)[0];
      if (day > today || value == null || value === '') return [];
      if (!Number.isFinite(value)) throw new Error('Presupuesto ' + year + ': importe inválido en ' + day);
      return [[day, value / 1000]];
    });
  });
}

function fetchTurkeyBudget_(today, previous = {}) {
  const config = TURKEY_PRODUCER;
  const catalogueUrl = config.budgetApi + 'pages?slug=merkezi-yonetim-butce-istatistikleri';
  const catalogue = JSON.parse(turkeyResponse_(UrlFetchApp.fetch(catalogueUrl, { muteHttpExceptions: true }), 'Catálogo presupuesto').getContentText());
  const content = catalogue[0]?.content?.rendered || '';
  const year = +today.slice(0, 4);
  const years = previous.TR_HMB_BUDGET_M_REVENUE?.observaciones[0]?.[0] <= (year - 1) + '-01-01' ? [year] : [year - 1, year];
  const series = {};
  const source = 'Ministerio de Tesoro y Finanzas de Türkiye (HMB) · Presupuesto del Gobierno central';
  for (const reportYear of years) {
    const ids = turkeyBudgetGroup_(content, reportYear);
    TURKEY_BUDGET_REPORTS.forEach((report, index) => {
      const [label, kind, fields] = report;
      const endpoint = config.budgetApi + 'files?id=' + ids[index] + '&name=' + encodeURIComponent(label);
      const listing = JSON.parse(turkeyResponse_(UrlFetchApp.fetch(endpoint, { muteHttpExceptions: true }), 'Catálogo Detay2').getContentText());
      const urls = new Set((listing.content || '').match(/https:\/\/ms\.hmb\.gov\.tr\/uploads\/[\w/.-]*Detay2[\w.-]*\.xlsx?(?=["'])/gi) || []);
      if (urls.size !== 1) throw new Error('Presupuesto ' + reportYear + ': falta el Excel Detay2 de ' + kind + '.');
      const url = [...urls][0];
      const file = turkeyResponse_(UrlFetchApp.fetch(url, { muteHttpExceptions: true }), 'Presupuesto Detay2').getBlob()
        .setContentType(/\.xlsx$/i.test(url) ? DASHBOARD_UPLOAD.xlsx : config.xls);
      const data = withDashboardSpreadsheet_(file, 'Central government budget', workbook => readTurkeyBudget_(
        workbook.getSheets().map(sheet => [sheet.getName(), sheet.getDataRange().getValues()]), report, reportYear, today));
      fields.forEach(([key, title], i) => {
        const target = series[key] ||= { title, data: [] };
        target.data.push(...data[i]);
      });
    });
  }
  for (const [key, title, expenses] of [['BALANCE', 'Budget balance', 'EXPENDITURE'],
    ['PRIMARY_BALANCE', 'Primary budget balance', 'NON_INTEREST']]) {
    const spending = new Map(series[expenses].data);
    series[key] = { title, data: series.REVENUE.data.filter(([day]) => spending.has(day))
      .map(([day, value]) => [day, value - spending.get(day)]) };
  }
  return Object.entries(series).map(([id, { title, data }]) => {
    const derived = ['BALANCE', 'PRIMARY_BALANCE'].includes(id);
    const result = turkeySeries_('TR_HMB_BUDGET_M_' + id, title,
      'Central government budget · monthly actuals (Detay2)', 'Monthly', 'CENTRAL_GOVERNMENT_BUDGET', 'public_finances',
      source, config.budgetPage, data);
    if (derived) result.entry.transformacion_y_calculo = id === 'BALANCE'
      ? 'Ingresos menos gastos.' : 'Ingresos menos gastos sin intereses.';
    return result;
  });
}

function fetchTurkeyTreasury_(today) {
  const config = TURKEY_PRODUCER;
  const catalogue = JSON.parse(turkeyResponse_(UrlFetchApp.fetch(config.treasuryCatalogue, { muteHttpExceptions: true }), 'Tesoro').getContentText());
  const content = catalogue[0]?.content?.rendered || '';
  const urls = new Set(content.match(/https:\/\/ms\.hmb\.gov\.tr\/uploads\/[\w/.-]+\/Treasury-Cash-Realizations-\d{4}-\d{4}-[\da-f]+\.xlsx?(?=["'\s<])/gi) || []);
  if (urls.size !== 1) throw new Error('No se pudo identificar un único Excel oficial de caja del Tesoro.');
  const url = [...urls][0];
  const file = turkeyResponse_(UrlFetchApp.fetch(url, { muteHttpExceptions: true }), 'Excel del Tesoro').getBlob();
  file.setContentType(url.endsWith('.xlsx') ? DASHBOARD_UPLOAD.xlsx : config.xls);
  return withDashboardSpreadsheet_(file, 'Treasury cash', workbook => {
    const years = workbook.getSheets().filter(sheet => /^20\d{2}$/.test(sheet.getName()));
    const data = readTurkeyTreasury_(years.map(sheet => [sheet.getName(), sheet.getDataRange().getValues()]), today);
    return TURKEY_CASH_ITEMS.map(([key, title, row], i) => turkeySeries_('TR_HMB_M_' + key, title,
      'Treasury Cash Realizations · ' + row, 'Monthly', 'TREASURY_CASH', 'public_finances',
      'Ministerio de Tesoro y Finanzas de Türkiye (HMB) · Estadísticas de caja del Tesoro', config.treasuryPage, data[i]));
  });
}

function readTurkeyTreasury_(sheets, today) {
  const result = TURKEY_CASH_ITEMS.map(() => []);
  const monthIndex = cell => TURKEY_MONTH_NAMES.indexOf(String(cell).replace(/\s*\(\d+\)\s*$/, '').trim().toLowerCase());
  for (const [year, rows] of sheets) {
    if (!rows.some(row => row.some(cell => /\(Million TL\)/i.test(String(cell))))) throw new Error('Tesoro ' + year + ': unidad inesperada.');
    const months = rows.find(row => row.some(cell => monthIndex(cell) === 0));
    if (!months) throw new Error('Tesoro ' + year + ': faltan los meses.');
    const columns = months.map(monthIndex);
    TURKEY_CASH_ITEMS.forEach(([, , label], index) => {
      const prefix = new RegExp('^\\s*\\d+\\.\\s*' + label + '\\s*(?:\\(|$)', 'i');
      const row = rows.find(cells => cells.some(cell => typeof cell === 'string' && prefix.test(cell)));
      if (!row) throw new Error('Tesoro ' + year + ': falta ' + label + '.');
      columns.forEach((month, col) => {
        if (month < 0 || row[col] === '' || row[col] == null) return;
        const day = year + '-' + String(month + 1).padStart(2, '0') + '-01';
        if (day <= today) result[index].push([day, row[col]]);
      });
    });
  }
  return result;
}

function turkeyBankRequest_(url, payload) {
  const form = Object.entries(payload).map(([key, value]) => encodeURIComponent(key) + '=' + encodeURIComponent(String(value))).join('&');
  return { url, method: 'post', contentType: 'application/x-www-form-urlencoded; charset=UTF-8', payload: form,
    headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest',
      Origin: 'https://www.bddk.org.tr', Referer: url.split('/Home/')[0] + '/' }, muteHttpExceptions: true };
}

function fetchTurkeyWeekly_(today, previous) {
  const source = TURKEY_PRODUCER.weekly;
  const page = turkeyResponse_(UrlFetchApp.fetch(source, { muteHttpExceptions: true }), 'BDDK semanal').getContentText();
  const release = page.match(/"tarih":\s*'(\d{2}\.\d{2}\.\d{4})'/)?.[1];
  if (!release) throw new Error('BDDK semanal: falta la fecha del boletín.');
  const endpoint = source + '/tr/Home/KiyaslamaJsonGetir';
  const requests = TURKEY_WEEKLY_REPORTS.map(([, , id]) => turkeyBankRequest_(endpoint,
    { dil: 'tr', tarih: release, id, parabirimi: 'TRY', sutun: 3, tarafKodu: '10001', gun: 90 }));
  let responses = [];
  try {
    responses = UrlFetchApp.fetchAll(requests);
  } catch (error) {
    console.log('BDDK semanal · histórico no disponible: ' + error.message);
  }
  const series = TURKEY_WEEKLY_REPORTS.flatMap(([key, title, code, label], index) => {
    const id = 'TR_BDDK_W_' + key;
    let data;
    try {
      if (!responses[index]) throw new Error('Histórico no disponible.');
      const response = turkeyResponse_(responses[index], 'BDDK histórico semanal');
      data = readTurkeyWeeklyBank_(JSON.parse(response.getContentText()), today, label);
      if (!data.length || data.some(([, value]) => !Number.isFinite(value))) throw new Error('Histórico sin valores válidos.');
    } catch (error) {
      try {
        const point = readTurkeyWeeklyBulletin_(page, release, today, code);
        data = [previous[id]?.observaciones.find(([day]) => day === point[0]) || point];
      } catch (bulletinError) {
        console.log(id + ' · ' + error.message + ' ' + bulletinError.message);
        return [];
      }
    }
    return [turkeySeries_(id, title, 'Banking sector · ' + label + ' (' + code + ')',
      'Weekly', 'BANKING', 'banking', 'Agencia de Regulación y Supervisión Bancaria (BDDK) · Boletín semanal', source, data)];
  });
  if (!series.length) throw new Error('BDDK semanal: no se pudo validar ninguna serie.');
  return series;
}

function turkeyWeekDate_(date) {
  const parts = /^(\d{1,2})\.(\d{1,2})\.(\d{4})$/.exec(date);
  if (!parts) throw new Error('BDDK semanal: fecha no reconocida.');
  const day = parts[3] + '-' + parts[2].padStart(2, '0') + '-' + parts[1].padStart(2, '0');
  if (!dashboardDate_(day, 'UTC')) throw new Error('BDDK semanal: fecha no válida.');
  return day;
}

function readTurkeyWeeklyBulletin_(page, release, today, code) {
  const date = turkeyWeekDate_(release);
  const graph = "ShowModalGraph\\(\\s*'" + code.replace(/\./g, '\\.') + "'\\s*,\\s*'TRY'\\s*,\\s*3\\s*\\)";
  const pattern = new RegExp('<td\\b(?=[^>]*\\bdata-label="TOPLAM")(?=[^>]*' + graph + ')[^>]*>([^<]+)</td>', 'i');
  const cell = page.match(pattern)?.[1]?.trim();
  if (!cell || !/Milyon TL/.test(page) || date > today || !/^(?:\d+|\d{1,3}(?:\.\d{3})+)(?:,\d+)?$/.test(cell)) {
    throw new Error('BDDK semanal: no se pudo verificar el último dato de ' + code + '.');
  }
  return [date, Number(cell.replace(/\./g, '').replace(',', '.'))];
}

function readTurkeyWeeklyBank_(report, today, label) {
  const { Baslik: title, XEkseni: dates, YEkseni: values } = report;
  const name = turkeyTradeText_(title || '');
  if (!name.includes(turkeyTradeText_(label)) || !/\(try\).*\[toplam\].*\[sektor\]/.test(name) ||
      !Array.isArray(dates) || !Array.isArray(values) || dates.length !== values.length) {
    throw new Error('BDDK semanal: respuesta inesperada para el crédito total del sector.');
  }
  return dates.map((date, i) => [turkeyWeekDate_(date), values[i]]).filter(([date]) => date <= today);
}

function fetchTurkeyMonthly_(today, previous) {
  const endpoint = TURKEY_PRODUCER.monthly + 'Home/BasitRaporGetir';
  const count = TURKEY_MONTHLY_REPORTS.every(([id]) => previous[id]) ? 3 : 12;
  const requests = Array.from({ length: count }, (_, i) => {
    const period = new Date(Date.UTC(+today.slice(0, 4), +today.slice(5, 7) - i - 2, 1));
    const day = period.toISOString().slice(0, 10);
    return TURKEY_MONTHLY_REPORTS.map(([, , table], report) => ({ day, report, request: turkeyBankRequest_(endpoint,
      { tabloNo: table, yil: period.getUTCFullYear(), ay: period.getUTCMonth() + 1, paraBirimi: 'TL', taraf: '10001' }) }));
  }).flat();
  const data = TURKEY_MONTHLY_REPORTS.map(() => []);
  for (let i = 0; i < requests.length; i += 6) {
    const chunk = requests.slice(i, i + 6);
    let responses;
    try {
      responses = UrlFetchApp.fetchAll(chunk.map(item => item.request));
    } catch (error) {
      console.log('BDDK mensual · lote fallido: se comprueban los meses por separado.');
    }
    chunk.forEach(({ day, report, request }, index) => {
      const [, , table, label] = TURKEY_MONTHLY_REPORTS[report];
      try {
        const { url, ...options } = request;
        const response = responses?.[index] || UrlFetchApp.fetch(url, options);
        const value = readTurkeyMonthlyBank_(JSON.parse(turkeyResponse_(response, 'BDDK ' + day).getContentText()), label);
        if (value !== null) data[report].push([day, value]);
      } catch (error) {
        console.log('BDDK mensual · ' + day + ' · tabla ' + table + ': ' + error.message);
      }
    });
  }
  if (!data.some(rows => rows.length)) throw new Error('Ningún periodo de crédito o depósitos pudo verificarse.');
  return TURKEY_MONTHLY_REPORTS.flatMap(([id, title, table, label], i) => {
    if (!data[i].length) {
      console.log('BDDK mensual · ' + id + ': se conserva cualquier histórico existente.');
      return [];
    }
    return [turkeySeries_(id, title, 'Banking sector · table ' + table + ' · ' + label, 'Monthly', 'BANKING', 'banking',
      'Agencia de Regulación y Supervisión Bancaria (BDDK) · Boletín mensual', TURKEY_PRODUCER.monthly, data[i])];
  });
}

function readTurkeyMonthlyBank_(report, label) {
  const table = report.Json;
  if (report.success === false && /^\d{4} yılının en son \d{1,2} ayına ait veri bulunmaktadır!?$/i.test(report.error || '')) return null;
  if (!report.success || !Array.isArray(table?.data?.rows)) throw new Error('BDDK mensual: respuesta inesperada.');
  if (!table.data.rows.length) return null;
  const columns = (table.colNames || []).flatMap((name, col) => name === 'Toplam' ? [col] : []);
  const matches = table.data.rows.filter(({ cell }) => cell[0] === 'Sektör' && cell[2] === label);
  if (columns.length !== 1 || matches.length !== 1 || !Number.isFinite(matches[0].cell[columns[0]])) {
    throw new Error('BDDK mensual: no se pudo validar el total sectorial de ' + label + '.');
  }
  return matches[0].cell[columns[0]];
}

function mergeTurkeyWorkbookRows_(dictionary, observations, updates, timezone) {
  const fields = DASHBOARD_UPLOAD.metadata;
  const metadata = dashboardColumns_(dictionary, ['id_serie', ...fields], 'Turquía · diccionario');
  const dates = dashboardColumns_(observations, ['id_serie', 'fecha', 'valor'], 'Turquía · observaciones');
  const header = dictionary[0];
  const changed = { dictionary: new Set(), observations: new Set() };
  if (!header.includes('source_url')) { header.push('source_url'); changed.dictionary.add(0); }
  const sourceUrl = header.indexOf('source_url');
  const seriesRows = new Map(dictionary.slice(1).map((row, index) => [row[metadata.id_serie], index + 1]));
  const dataRows = new Map(observations.slice(1).map((row, index) =>
    [row[dates.id_serie] + '|' + dashboardDate_(row[dates.fecha], timezone), index + 1]));
  for (const { id, entry, data } of updates) {
    const rowIndex = seriesRows.get(id) ?? dictionary.length;
    const seriesRow = dictionary[rowIndex] || Array(header.length).fill('');
    const columns = [[metadata.id_serie, id], [sourceUrl, entry.source_url], ...fields.map(field => [metadata[field], entry[field]])];
    if (columns.some(([col, value]) => seriesRow[col] !== value)) {
      columns.forEach(([col, value]) => { seriesRow[col] = value; });
      dictionary[rowIndex] = seriesRow;
      changed.dictionary.add(rowIndex);
    }
    for (const [day, value] of data) {
      const index = dataRows.get(id + '|' + day);
      if (index === undefined) {
        const row = Array(observations[0].length).fill('');
        row[dates.id_serie] = id;
        row[dates.fecha] = day;
        row[dates.valor] = value;
        changed.observations.add(observations.length);
        observations.push(row);
      } else if (observations[index][dates.valor] !== value) {
        observations[index][dates.valor] = value;
        changed.observations.add(index);
      }
    }
  }
  return changed;
}

function writeTurkeyRows_(sheet, rows, changed) {
  if (!changed.size) return;
  const width = rows[0].length;
  if (sheet.getMaxRows() < rows.length) sheet.insertRowsAfter(sheet.getMaxRows(), rows.length - sheet.getMaxRows());
  if (sheet.getMaxColumns() < width) sheet.insertColumnsAfter(sheet.getMaxColumns(), width - sheet.getMaxColumns());
  const indexes = [...changed].sort((a, b) => a - b);
  for (let i = 0; i < indexes.length;) {
    const start = indexes[i];
    let end = start;
    while (indexes[++i] === end + 1) end++;
    const values = rows.slice(start, end + 1).map(row => Array.from({ length: width }, (_, col) => row[col] ?? ''));
    sheet.getRange(start + 1, 1, values.length, width).setValues(values);
  }
}
