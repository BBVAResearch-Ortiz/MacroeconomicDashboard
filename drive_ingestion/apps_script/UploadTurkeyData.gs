const TURKEY_PRODUCER = {
  timezone: 'Europe/Istanbul',
  treasuryPage: 'https://en.hmb.gov.tr/public-finance',
  treasuryCatalogue: 'https://en.hmb.gov.tr/portal/v2/pages?slug=public-finance',
  weekly: 'https://www.bddk.org.tr/BultenHaftalik',
  monthly: 'https://www.bddk.org.tr/BultenAylik/tr/',
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

function previewTurkeyWorkbook() {
  runTurkeyWorkbook_(false);
}

function syncTurkeyWorkbook() {
  runTurkeyWorkbook_(true);
}

function installTurkeyWorkbookTrigger() {
  const oldTriggers = ScriptApp.getProjectTriggers().filter(trigger => trigger.getHandlerFunction() === 'syncTurkeyWorkbook');
  ScriptApp.newTrigger('syncTurkeyWorkbook').timeBased().everyDays(1).atHour(19)
    .inTimezone(TURKEY_PRODUCER.timezone).create();
  oldTriggers.forEach(trigger => ScriptApp.deleteTrigger(trigger));
}

function runTurkeyWorkbook_(publish) {
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
      const sources = [
        ['Tesoro', () => fetchTurkeyTreasury_(today)],
        ['BDDK semanal', () => fetchTurkeyWeekly_(today)],
        ['BDDK mensual', () => fetchTurkeyMonthly_(today, previous.series)]
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

      if (updates.length) {
        const pending = mergeTurkeyWorkbookRows_(dictionaryRows, observationRows, updates, timezone);
        const next = parseDashboardSheets_(dictionaryRows, observationRows, timezone);
        const changed = Object.keys(next.hashes).some(key => next.hashes[key] !== previous.hashes[key]);
        console.log('Turquía · Excel: ' + Object.keys(next.series).length + ' series, ' + next.count + ' observaciones. ' +
          (changed ? (publish ? 'Cambios para guardar.' : 'Vista previa con cambios.') : 'Sin cambios.'));
        if (publish && changed) {
          writeTurkeyRows_(dictionary, dictionaryRows, pending.dictionary);
          writeTurkeyRows_(observations, observationRows, pending.observations);
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
      }
      if (errors.length) throw new Error('Turquía · fuentes con errores:\n' + errors.join('\n'));
    });
  } finally {
    lock.releaseLock();
  }
}

function turkeyResponse_(response, name) {
  if (response.getResponseCode() !== 200) throw new Error(name + ': HTTP ' + response.getResponseCode());
  return response;
}

function turkeySeries_(id, title, description, frequency, block, area, source, url, data) {
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
      'área': area, frecuencia: frequency, unidad: 'Millones de TRY', source_url: url
    }
  };
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
      'Tesoro de Turquía (HMB) · Treasury Cash Realizations', config.treasuryPage, data[i]));
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
  return { url, method: 'post', payload, headers: { Accept: 'application/json' }, muteHttpExceptions: true };
}

function fetchTurkeyWeekly_(today) {
  const source = TURKEY_PRODUCER.weekly;
  const page = turkeyResponse_(UrlFetchApp.fetch(source, { muteHttpExceptions: true }), 'BDDK semanal').getContentText();
  const release = page.match(/"tarih":\s*'(\d{2}\.\d{2}\.\d{4})'/)?.[1];
  if (!release) throw new Error('BDDK semanal: falta la fecha del boletín.');
  const endpoint = source + '/tr/Home/KiyaslamaJsonGetir';
  const { url, ...options } = turkeyBankRequest_(endpoint,
    { dil: 'tr', tarih: release, id: '1.0.1', parabirimi: 'TRY', sutun: 3, tarafKodu: '10001', gun: 90 });
  const response = turkeyResponse_(UrlFetchApp.fetch(url, options), 'BDDK histórico semanal');
  const data = readTurkeyWeeklyBank_(JSON.parse(response.getContentText()), today);
  return [turkeySeries_('TR_BDDK_W_LOANS', 'Total bank loans', 'Banking sector · Toplam Krediler (1.0.1)',
    'Weekly', 'BANKING', 'banking', 'BDDK / BRSA · boletín semanal', source, data)];
}

function readTurkeyWeeklyBank_(report, today) {
  const { Baslik: title, XEkseni: dates, YEkseni: values } = report;
  if (!/^Toplam Krediler\b.*\(TRY\).*\[Toplam\].*\[Sektör\]/.test(title || '') ||
      !Array.isArray(dates) || !Array.isArray(values) || dates.length !== values.length) {
    throw new Error('BDDK semanal: respuesta inesperada para el crédito total del sector.');
  }
  return dates.map((date, i) => {
    const parts = /^(\d{1,2})\.(\d{1,2})\.(\d{4})$/.exec(date);
    if (!parts) throw new Error('BDDK semanal: fecha no reconocida.');
    return [parts[3] + '-' + parts[2].padStart(2, '0') + '-' + parts[1].padStart(2, '0'), values[i]];
  }).filter(([date]) => date <= today);
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
    UrlFetchApp.fetchAll(chunk.map(item => item.request)).forEach((response, index) => {
      const { day, report } = chunk[index];
      const value = readTurkeyMonthlyBank_(JSON.parse(turkeyResponse_(response, 'BDDK ' + day).getContentText()),
        TURKEY_MONTHLY_REPORTS[report][3]);
      if (value !== null) data[report].push([day, value]);
    });
  }
  return TURKEY_MONTHLY_REPORTS.map(([id, title, table, label], i) => turkeySeries_(id, title,
    'Banking sector · table ' + table + ' · ' + label, 'Monthly', 'BANKING', 'banking',
    'BDDK / BRSA · boletín mensual', TURKEY_PRODUCER.monthly, data[i]));
}

function readTurkeyMonthlyBank_(report, label) {
  const table = report.Json;
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
