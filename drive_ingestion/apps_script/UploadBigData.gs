const DASHBOARD_BIG_DATA = {
  exportsFolder: '1thGWH7iyzwmC3YDjMHf1J_vwmPfNpm8H',
  workbookFolder: '1U8giN5bJ4tJLAtVf_rjlxLu9s6qGr3u2',
  workbookId: '1lqU0EbQHoDATmfNNOl7yodFTve6MYxCHLjCoRczsVy8',
  destination: 'drive_ingestion/snapshots/bigdata/',
  stateKey: 'FOW_BIG_DATA_V1',
  sheets: [
    ['ESP_Consumo', 'Consumo', ['Type %', 'Isocode', 'Date', 'EN', 'ES']],
    ['Inversion_España', 'Inversión', ['Type', 'Date', 'Country']],
    ['España_Activ_Sectorial', 'Actividad sectorial', ['Type', 'Date']]
  ],
  categories: ['Food & Beverage', 'Alcohol & Tobacco', 'Clothing & FootWear', 'Housing & Utilities',
    'Furnishing & House Equipment', 'Health', 'Transport', 'Info & Communication', 'Leisure',
    'Education', 'Restaurant & Hotels', 'Insurance & Fin. Service', 'Other'],
  territories: { ccaa: 'CCAA', provincia: 'Provincial', ciudad: 'Urbano' }
};

function previewDashboardBigData() {
  runDashboardBigData_(false);
}

function syncDashboardBigData() {
  runDashboardBigData_(true);
}

function installDashboardBigDataTrigger() {
  const properties = PropertiesService.getScriptProperties();
  if (!properties.getProperty(DASHBOARD_UPLOAD.tokenProperty)) {
    throw new Error('Falta FOW_DASHBOARD_GITHUB_TOKEN.');
  }
  const previous = ScriptApp.getProjectTriggers()
    .filter(trigger => trigger.getHandlerFunction() === 'syncDashboardBigData');
  ScriptApp.newTrigger('syncDashboardBigData')
    .timeBased()
    .everyWeeks(1)
    .onWeekDay(ScriptApp.WeekDay.WEDNESDAY)
    .atHour(18)
    .nearMinute(0)
    .inTimezone('Europe/Madrid')
    .create();
  previous.forEach(trigger => ScriptApp.deleteTrigger(trigger));
}

function runDashboardBigData_(publish) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(25000)) {
    console.log('Big Data: otra sincronización está en curso.');
    return;
  }
  try {
    const config = DASHBOARD_BIG_DATA;
    const properties = PropertiesService.getScriptProperties();
    const token = publish ? properties.getProperty(DASHBOARD_UPLOAD.tokenProperty) : null;
    if (publish && !token) throw new Error('Falta FOW_DASHBOARD_GITHUB_TOKEN.');

    const exports = listDashboardFiles_(config.exportsFolder, 'text/csv');
    const locate = name => {
      const files = exports.filter(file => file.name === name);
      if (files.length !== 1) throw new Error('Se esperaba un archivo ' + name);
      return files[0];
    };
    const report = locate('Datos_informe.csv');
    const monitor = locate('Tabla_monitor.csv');
    const workbook = listDashboardFiles_(config.workbookFolder, DASHBOARD_UPLOAD.spreadsheet)
      .find(file => file.id === config.workbookId);
    if (!workbook) throw new Error('No se encuentra Alta Frecuencia - España.');

    const revision = JSON.stringify([workbook, report, monitor].map(file => [
      file.id, file.md5Checksum || file.version
    ]));
    const stateKey = config.stateKey + '_' + DASHBOARD_UPLOAD.branch;
    if (publish && revision === properties.getProperty(stateKey)) {
      console.log('Big Data: fuentes sin cambios.');
      return;
    }
    const csv = file => Utilities.parseCsv(
      DriveApp.getFileById(file.id).getBlob().getDataAsString('UTF-8').replace(/^\uFEFF/, '')
    );
    const sheet = SpreadsheetApp.openById(workbook.id);
    const sources = config.sheets.map(([name]) => dashboardWorkbookRows_(sheet, name));
    const national = readBigDataNational_(sources, sheet.getSpreadsheetTimeZone());
    const updated = readBigDataReport_(csv(report), national);
    const heatmap = readBigDataMonitor_(csv(monitor));
    const files = [
      ['bigdata.json', { source: 'BBVA Research', series: national }],
      ['bigdata_heatmap.json', heatmap],
      ...updated.files
    ];
    if (publish) {
      commitDashboardFiles_(files.map(([path, data]) => ({
        path: config.destination + path, content: JSON.stringify(data) + '\n'
      })), 'Update Spain Big Data from Drive', token);
      properties.setProperty(stateKey, revision);
    }
    console.log('Big Data: ' + national.length + ' series nacionales, ' + updated.count +
      ' territorios y ' + heatmap.rows.length + ' filas en el mapa de calor.');
  } finally {
    lock.releaseLock();
  }
}

function bigDataValue_(value) {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  let text = String(value ?? '').trim().replace(/\s/g, '');
  if (!text) return null;
  if (text.includes(',') && text.includes('.')) {
    text = text.lastIndexOf(',') > text.lastIndexOf('.') ? text.replace(/\./g, '') : text.replace(/,/g, '');
  }
  const parsed = Number(text.replace(',', '.'));
  return Number.isFinite(parsed) ? parsed : null;
}

function bigDataSeries_(id, label, group, source, values) {
  return {
    id, label, group, source, unit: 'valor original de la hoja', freq: 'D',
    data: [...values].sort(([a], [b]) => a.localeCompare(b)).map(([day, value]) => [day, value, 0])
  };
}

function readBigDataNational_(worksheets, timezone) {
  return worksheets.flatMap(([header, ...rows], sheetIndex) => {
    const [name, group, excluded] = DASHBOARD_BIG_DATA.sheets[sheetIndex];
    const dayCol = header.findIndex(cell => String(cell).trim().toLowerCase() === 'date');
    const typeCol = header.findIndex(cell => String(cell).trim().toLowerCase().startsWith('type'));
    if (dayCol < 0 || typeCol < 0) throw new Error(name + ': faltan columnas Date o Type.');
    const columns = header.map((cell, col) => [String(cell).trim(), col])
      .filter(([label, col]) => label && col !== typeCol && col !== dayCol && !excluded.includes(label));
    const groups = new Map();
    for (const row of rows) {
      const type = String(row[typeCol]).trim();
      if (type !== 'Real' && type !== 'Nominal') continue;
      const day = dashboardDate_(row[dayCol], timezone);
      if (!day) continue;
      for (const [label, col] of columns) {
        const value = bigDataValue_(row[col]);
        if (value === null) continue;
        const key = group + ' · ' + label + ' · ' + type;
        if (!groups.has(key)) groups.set(key, new Map());
        groups.get(key).set(day, value);
      }
    }
    if (!groups.size) throw new Error(name + ': la hoja no tiene datos nacionales válidos.');
    return [...groups].map(([label, values], i) =>
      bigDataSeries_(name + '_' + i, label, group, 'BBVA Research', values));
  });
}

function readBigDataReport_(rows, national) {
  const config = DASHBOARD_BIG_DATA;
  const cols = dashboardColumns_(rows, ['fecha', 'nivel', 'codigo', 'nombre_mostrado', 'valor'],
    'Datos_informe.csv');
  const consumption = new Map();
  const territories = new Map();
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    const level = row[cols.nivel];
    const code = row[cols.codigo];
    const label = row[cols.nombre_mostrado] || code;
    const categoryCode = /^CAT(\d+)$/.exec(code || '');
    const category = code === 'ES' ? 'Total coicops' : categoryCode && config.categories[Number(categoryCode[1]) - 1];
    const group = Object.prototype.hasOwnProperty.call(config.territories, level) ? config.territories[level] : null;
    const isNational = (level === 'nacional' || level === 'categoria') && category;
    if (!group && !isNational) continue;
    const day = dashboardDate_(row[cols.fecha], 'UTC');
    const value = bigDataValue_(row[cols.valor]);
    if (!code || !day || value === null) throw new Error('Datos_informe.csv, fila ' + (i + 1) + ': dato inválido.');
    if (isNational) {
      if (!consumption.has(category)) consumption.set(category, new Map());
      consumption.get(category).set(day, value);
    } else {
      const key = group + '|' + code;
      if (!territories.has(key)) territories.set(key, { group, code, label, values: new Map() });
      territories.get(key).values.set(day, value);
    }
  }
  if (!consumption.has('Total coicops') || !territories.size) throw new Error('Datos_informe.csv incompleto.');
  for (const [category, values] of consumption) {
    const label = 'Consumo · ' + category + ' · Real';
    const previous = national.find(item => item.label === label);
    const observations = new Map(previous ? previous.data.map(([day, value]) => [day, value]) : []);
    for (const [day, value] of values) observations.set(day, value);
    const updated = bigDataSeries_(previous?.id || 'drive_' + bigDataId_(label), label,
      'Consumo', 'BBVA Research · Datos_informe.csv', observations);
    if (previous) Object.assign(previous, updated); else national.push(updated);
  }
  const groups = Object.fromEntries(Object.values(config.territories).map(group => [group, []]));
  const files = [];
  for (const entry of territories.values()) {
    const { group, code, label, values } = entry;
    const id = bigDataId_(group + '|' + code);
    const path = group.toLowerCase() + '/real/' + id + '.json';
    const series = bigDataSeries_('drive_geo_' + id, group + ' · ' + label + ' · Total Consumo · Real',
      group, 'BBVA Research · Datos_informe.csv', values);
    groups[group].push({ id: code, label, files: [path], series: [{ id: series.id, label: series.label }] });
    files.push(['bigdata_geo/' + path, { series: [series] }]);
  }
  for (const entries of Object.values(groups)) {
    if (!entries.length) throw new Error('Datos_informe.csv: falta uno de los niveles territoriales.');
    entries.sort((a, b) => a.label.localeCompare(b.label, 'es'));
  }
  files.push(['bigdata_geo/index.json', { groups }]);
  return { files, count: territories.size };
}

function bigDataId_(value) {
  return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, value, Utilities.Charset.UTF_8)
    .map(byte => (byte & 255).toString(16).padStart(2, '0')).join('').slice(0, 20);
}

function normalizeBigDataLabel_(value) {
  return value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ').trim();
}

function bigDataMonitorColumns_(header) {
  const months = 'ene feb mar abr may jun jul ago sep oct nov dic'.split(' ');
  const columns = new Map();
  const iso = (year, month, day) => [year, month, day].map(v => String(v).padStart(2, '0')).join('-');
  let anchor = null;
  for (let i = 1; i < header.length; i++) {
    const match = normalizeBigDataLabel_(header[i]).match(/^([a-z]{3}) (\d{2}|\d{4})$/);
    if (!match || !months.includes(match[1])) continue;
    const year = Number(match[2]) + (match[2].length === 2 ? 2000 : 0);
    const date = iso(year, months.indexOf(match[1]) + 1, 1);
    if (!anchor || anchor < date) anchor = date;
    columns.set(i, ['monthly', date.slice(0, 7)]);
  }
  if (!anchor) throw new Error('Tabla_monitor.csv: faltan columnas mensuales.');
  const [anchorYear, anchorMonth] = anchor.split('-').map(Number);
  let previous = null;
  for (let i = 1; i < header.length; i++) {
    if (columns.has(i) || !header[i].trim()) continue;
    const match = normalizeBigDataLabel_(header[i]).match(/^\d{1,2}(?: [a-z]{3})? (\d{1,2}) ([a-z]{3})$/);
    if (!match || !months.includes(match[2])) throw new Error('Periodo semanal inválido: ' + header[i]);
    const month = months.indexOf(match[2]) + 1;
    const year = previous ? previous.year + Number(month < previous.month)
      : anchorYear + Math.floor((anchorMonth - month + 6) / 12);
    const date = dashboardDate_(iso(year, month, Number(match[1])), 'UTC');
    const gap = previous ? (Date.parse(date) - Date.parse(previous.date)) / 86400000 : 1;
    if (!date || gap <= 0 || gap > 31) throw new Error('Semanas fuera de secuencia: ' + header[i]);
    columns.set(i, ['weekly', date]);
    previous = { year, month, date };
  }
  return columns;
}

function readBigDataMonitor_(input) {
  const names = {
    'consumo privado nacional ine': 'Consumo de los hogares (INE)',
    'indice de comercio al por menor ine': 'Índice de comercio al por menor (INE)',
    'indicador big data de consumo total': 'Indicador Big Data de consumo total',
    'energia del hogar luz agua gas': 'Energía del hogar',
    'mobiliario electrodomesticos y mantenimiento vivienda': 'Mobiliario y mantenimiento del hogar',
    'cuidado personal proteccion social y bienes y servicios diver': 'Otros bienes y servicios'
  };
  const rows = [];
  let group = null;
  let columns = null;
  for (let cells of input) {
    if (cells.length === 1 && cells[0].includes(',"')) {
      const index = cells[0].indexOf(',"');
      cells = cells[0].startsWith('"') ? Utilities.parseCsv(cells[0])[0]
        : [cells[0].slice(0, index), ...Utilities.parseCsv(cells[0].slice(index + 1))[0]];
    }
    const raw = (cells[0] || '').replace(/\t/g, '   ');
    if (!raw.trim()) continue;
    const key = raw.trim().toLowerCase();
    if (key === 'nacional' || key === 'ccaa / provincias / ciudades') {
      group = key === 'nacional' ? 'nacional' : 'territorial';
      columns = bigDataMonitorColumns_(cells);
      continue;
    }
    if (!columns || ![...columns.keys()].some(i => cells[i]?.trim())) continue;
    const indent = raw.length - raw.trimStart().length;
    const level = group === 'territorial' ? Math.min(2, Math.floor(indent / 3)) : Number(indent > 0);
    let label = raw.trim().replace(/\*+$/, '').trim();
    if (group === 'nacional') label = names[normalizeBigDataLabel_(label)] || label;
    const row = { label, group, level, source: label.endsWith('(INE)') ? 'INE' : 'BBVA Research',
      monthly: {}, weekly: {} };
    for (const [i, [frequency, period]] of columns) {
      const value = bigDataValue_(cells[i]);
      row[frequency][period] = value === null ? null : Math.round(value * 1e8) / 1e6;
    }
    rows.push(row);
  }
  if (!rows.some(row => Object.values(row.monthly).some(value => value !== null))) {
    throw new Error('Tabla_monitor.csv: no hay observaciones válidas.');
  }
  return { title: 'España: Indicadores de consumo', unit: '%',
    note: 'Indicador real; variación interanual de la media móvil de 28 días. Cierre de mes y semana.', rows };
}
