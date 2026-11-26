const DASHBOARD_UPLOAD = {
  root: '1Ejg2KKXKKT1QOjTb0OZFcZ0y2vUry2cr',
  areas: { spain: 'Spain', global: 'Global Scenarios', turkey: 'Turkiye', usa: 'USA' },
  masters: { spain: { name: 'excel_madre.xlsx', language: 'es' }, turkey: { name: 'turkey_macro_master.xlsx', language: 'en' } },
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  folder: 'application/vnd.google-apps.folder',
  spreadsheet: 'application/vnd.google-apps.spreadsheet',
  repository: 'BBVAResearch-Ortiz/MacroeconomicDashboard',
  branch: 'main',
  tokenProperty: 'FOW_DASHBOARD_GITHUB_TOKEN',
  metadata: [
    'titulo_serie', 'subtitulo_descripcion', 'transformacion_y_calculo', 'fuente',
    'frecuencia_y_cobertura_temporal', 'tipo_grafico', 'bloque', 'área', 'frecuencia', 'unidad'
  ]
};

const DASHBOARD_ENGLISH_HEADERS = {
  id_serie: 'series_id', titulo_serie: 'series_title', subtitulo_descripcion: 'subtitle_description',
  transformacion_y_calculo: 'transformation_and_calculation', fuente: 'source',
  frecuencia_y_cobertura_temporal: 'frequency_and_coverage', tipo_grafico: 'chart_type',
  bloque: 'block', 'área': 'area', frecuencia: 'frequency', unidad: 'unit',
  fecha: 'date', valor: 'value'
};
const DASHBOARD_ENGLISH_FREQUENCIES = new Map([
  ['Daily', 'Diaria'], ['Weekly', 'Semanal'], ['Monthly', 'Mensual'], ['Quarterly', 'Trimestral']
]);
const DASHBOARD_ENGLISH_AREAS = new Map([
  ['consumption', 'consumo'], ['industry', 'industria'], ['opinion_surveys', 'encuestas_opinión'],
  ['business_activity', 'actividad_empresarial'], ['external_sector', 'sector_exterior']
]);

function previewDashboardUpload() {
  runDashboardUpload_(false);
}

function syncDashboardFromDrive() {
  runDashboardUpload_(true);
}

function installDashboardUploadTrigger() {
  const properties = PropertiesService.getScriptProperties();
  if (!properties.getProperty(DASHBOARD_UPLOAD.tokenProperty)) {
    throw new Error('Configura FOW_DASHBOARD_GITHUB_TOKEN antes de instalar el disparador.');
  }
  ScriptApp.getProjectTriggers()
    .filter(trigger => trigger.getHandlerFunction() === 'syncDashboardFromDrive')
    .forEach(trigger => ScriptApp.deleteTrigger(trigger));
  ScriptApp.newTrigger('syncDashboardFromDrive').timeBased().everyMinutes(15).create();
}

function runDashboardUpload_(publish) {
  const start = Date.now();
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;
  try {
    const config = DASHBOARD_UPLOAD;
    const properties = PropertiesService.getScriptProperties();
    const token = publish ? properties.getProperty(config.tokenProperty) : null;
    if (publish && !token) throw new Error('Falta FOW_DASHBOARD_GITHUB_TOKEN.');
    const folders = listDashboardFiles_(config.root, config.folder);
    const errors = [];
    const areas = Object.entries(config.areas);
    const cursorKey = 'FOW_UPLOAD_NEXT_AREA';
    const cursor = token ? (Number(properties.getProperty(cursorKey)) || 0) % areas.length : 0;
    for (let offset = 0; offset < areas.length; offset++) {
      if (Date.now() - start > 180000) {
        console.log('Las carpetas restantes se comprobarán en la próxima ejecución.');
        break;
      }
      const index = (cursor + offset) % areas.length;
      const [area, name] = areas[index];
      if (token) properties.setProperty(cursorKey, String((index + 1) % areas.length));
      try {
        const matches = folders.filter(folder => folder.name === name);
        if (!matches.length && area === 'usa') {
          console.log('usa: carpeta USA aún no creada en Drive.');
          continue;
        }
        if (matches.length !== 1) throw new Error('Se esperaba una carpeta llamada ' + name);
        syncDashboardArea_(area, matches[0].id, properties, token);
      } catch (error) {
        errors.push(name + ': ' + error.message);
      }
    }
    if (errors.length) throw new Error(errors.join('\n'));
  } finally {
    lock.releaseLock();
  }
}

function listDashboardFiles_(parent, mediaType) {
  const options = {
    q: "'" + parent + "' in parents and trashed = false and mimeType = '" + mediaType + "'",
    fields: 'nextPageToken,files(id,name,md5Checksum,version)',
    includeItemsFromAllDrives: true,
    supportsAllDrives: true
  };
  const files = [];
  do {
    const page = Drive.Files.list(options);
    files.push(...(page.files || []));
    options.pageToken = page.nextPageToken;
  } while (options.pageToken);
  return files;
}

function syncDashboardArea_(area, folder, properties, token) {
  const books = listDashboardFiles_(folder, DASHBOARD_UPLOAD.xlsx);
  const master = DASHBOARD_UPLOAD.masters[area];
  const book = selectDashboardMaster_(area, books);
  if (!book) {
    console.log(area + ': carpeta sin Excel.');
    return;
  }
  const key = 'FOW_UPLOAD_V1_' + DASHBOARD_UPLOAD.branch + '_' + area;
  const previous = JSON.parse(properties.getProperty(key) || '{}');
  const revision = book.id + ':' + (book.md5Checksum || book.version);
  const localizationVersion = area === 'turkey' ? 2 : master ? 1 : null;
  if (token && revision === previous.revision &&
      (!master || previous.name === book.name && previous.localizationVersion === localizationVersion)) {
    console.log(area + ': Excel sin cambios.');
    return;
  }

  const workbook = readDashboardWorkbook_(book);
  const parsed = area === 'turkey' ? excludeTurkeyExample_(workbook) : workbook;
  if (!parsed.count) {
    console.log('turkey · ' + book.name + ': sin series fuera del Excel de ejemplo. Se conserva la instantánea publicada.');
    return;
  }
  if (area === 'spain') {
    const supported = ['D', 'M', 'Q', 'Diaria', 'Mensual', 'Trimestral'];
    for (const [id, entry] of Object.entries(parsed.series)) {
      if (!supported.includes(entry.frecuencia)) {
        throw new Error('Frecuencia fuera de las admitidas en el Blackboard: ' + id);
      }
    }
  }
  const changed = Object.keys(parsed.hashes).filter(name => parsed.hashes[name] !== (previous.hashes || {})[name]);
  const localized = master ? localizeDashboardSeries_(parsed.series, master.language) : null;
  const translationsChanged = localized?.hash && localized.hash !== previous.translationHash;
  const masterChanged = master && previous.name !== book.name;
  if (token && (changed.length || translationsChanged || masterChanged)) {
    const origen = { name: book.name };
    if (area === 'turkey') origen.updated_at = new Date().toISOString();
    const payload = { origen, series: parsed.series };
    const commit = commitDashboardSnapshot_(area, JSON.stringify(payload) + '\n', token);
    if (commit) console.log(area + ': commit en GitHub ' + commit);
  }
  if (token) properties.setProperty(key, JSON.stringify({ revision, name: book.name, hashes: parsed.hashes,
    localizationVersion: localized?.complete ? localizationVersion : null, translationHash: localized?.hash }));
  console.log(area + ' · ' + book.name + ': ' + Object.keys(parsed.series).length + ' series y ' + parsed.count +
    ' observaciones. Hojas con cambios: ' + (changed.join(', ') || 'ninguna') +
    (localized ? ' · Traducción del catálogo: ' + (localized.complete ? 'completa' : 'pendiente') : ''));
}

function excludeTurkeyExample_(workbook) {
  const records = Object.entries(workbook.series).filter(([, entry]) => !/\bTurkey_example_data\.xlsx\b/i.test(entry.fuente || ''));
  if (records.length === Object.keys(workbook.series).length) return workbook;
  console.log('turkey: excluidas ' + (Object.keys(workbook.series).length - records.length) + ' series del Excel de ejemplo.');
  const dictionary = records.map(([id, { observaciones, ...metadata }]) => [id, metadata]);
  const observations = records.map(([id, entry]) => [id, entry.observaciones]);
  return { series: Object.fromEntries(records), count: observations.reduce((total, [, points]) => total + points.length, 0),
    hashes: { DICCIONARIO: dashboardHash_(dictionary), DATOS_LARGO: dashboardHash_(observations) } };
}

function selectDashboardMaster_(area, books) {
  const master = DASHBOARD_UPLOAD.masters[area];
  const matches = master ? books.filter(book => book.name.trim().toLowerCase() === master.name) : books;
  if (!books.length) return null;
  if (matches.length !== 1) throw new Error(master
    ? 'Se esperaba un único ' + master.name + ' (encontrados: ' + matches.length + ').'
    : 'Se esperaba un Excel. Encontrados: ' + books.length);
  return matches[0];
}

function localizeDashboardSeries_(series, source) {
  const target = source === 'es' ? 'en' : 'es';
  const texts = new Map();
  const fields = ['titulo_serie', 'subtitulo_descripcion'];
  Object.values(series).forEach(entry => fields.forEach(field => {
    const text = typeof entry[field] === 'string' ? entry[field].trim() : '';
    if (text && !texts.has(text)) texts.set(text, 'fow-locale-' + dashboardHash_([source, target, text]));
  }));
  const deadline = Date.now() + 45000;
  const translated = {};
  try {
    const cache = CacheService.getScriptCache();
    Object.assign(translated, cache.getAll([...texts.values()]));
    const pending = [...texts].filter(([, key]) => !translated[key]);
    while (pending.length && Date.now() < deadline) {
      const batch = [];
      let length = 0;
      while (pending.length && batch.length < 16 && (!batch.length || length + pending[0][0].length <= 3500)) {
        const item = pending.shift();
        length += item[0].length;
        batch.push(item);
      }
      const input = batch.map(([text], i) => '<p id="fow' + i + '">' + text.replace(/[&<>]/g,
        ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[ch]) + '</p>').join('');
      const output = LanguageApp.translate(input, source, target, { contentType: 'html' });
      const values = {};
      for (const match of output.matchAll(/<p\b[^>]*\bid=["']?fow(\d+)["']?[^>]*>([\s\S]*?)<\/p>/gi)) {
        const item = batch[Number(match[1])];
        const text = match[2].replace(/<[^>]+>/g, '').replace(/&(#x[\da-f]+|#\d+|amp|lt|gt|quot|apos|nbsp);/gi,
          (entity, name) => {
            if (name[0] !== '#') return ({ amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' })[name.toLowerCase()];
            const value = /^#x/i.test(name) ? parseInt(name.slice(2), 16) : Number(name.slice(1));
            return value > 0 && value <= 0x10ffff ? String.fromCodePoint(value) : entity;
          }).trim();
        if (item && text) values[item[1]] = text;
      }
      for (const [text, key] of batch) {
        if (!values[key] && Date.now() < deadline) {
          const value = LanguageApp.translate(text, source, target).trim();
          if (value) values[key] = value;
        }
      }
      Object.assign(translated, values);
      if (Object.keys(values).length) cache.putAll(values, 21600);
      if (!Object.keys(values).length) break;
    }
  } catch (error) {
    console.log('Traducción del catálogo ' + source + ' → ' + target + ' pendiente.');
  }

  const localized = [];
  Object.entries(series).forEach(([id, entry]) => {
    const text = {};
    fields.forEach(field => {
      const original = typeof entry[field] === 'string' ? entry[field].trim() : '';
      const value = translated[texts.get(original)];
      if (value) text[field] = value;
    });
    if (Object.keys(text).length) {
      entry.translations = { [target]: text };
      localized.push([id, text]);
    }
  });
  return { complete: [...texts.values()].every(key => translated[key]),
    hash: localized.length ? dashboardHash_(localized) : null };
}

function dashboardWorkbookRows_(workbook, name) {
  const sheet = workbook.getSheetByName(name);
  if (!sheet) throw new Error('Falta la hoja ' + name);
  return sheet.getDataRange().getValues();
}

function readDashboardWorkbook_(book) {
  const blob = DriveApp.getFileById(book.id).getBlob();
  return withDashboardSpreadsheet_(blob, book.name, workbook => parseDashboardSheets_(
    dashboardWorkbookRows_(workbook, workbook.getSheetByName('DICTIONARY') ? 'DICTIONARY' : 'DICCIONARIO'),
    dashboardWorkbookRows_(workbook, workbook.getSheetByName('LONG_DATA') ? 'LONG_DATA' : 'DATOS_LARGO'),
    workbook.getSpreadsheetTimeZone()
  ));
}

function withDashboardSpreadsheet_(blob, name, read) {
  const temporary = Drive.Files.create({
    name: 'FoW temporal – ' + name,
    mimeType: DASHBOARD_UPLOAD.spreadsheet
  }, blob, { fields: 'id' });
  try {
    return read(SpreadsheetApp.openById(temporary.id));
  } finally {
    Drive.Files.update({ trashed: true }, temporary.id);
  }
}

function dashboardColumns_(rows, expected, name) {
  const headers = rows[0] || [];
  const columns = Object.create(null);
  for (const field of expected) {
    const alternatives = [field, DASHBOARD_ENGLISH_HEADERS[field]].filter(Boolean);
    const indexes = headers.flatMap((header, index) => alternatives.includes(header) ? [index] : []);
    if (indexes.length !== 1) {
      throw new Error(name + ': falta la columna ' + field + ' o está duplicada.');
    }
    columns[field] = indexes[0];
  }
  return columns;
}

function dashboardDate_(value, timezone) {
  const day = value instanceof Date ? Utilities.formatDate(value, timezone, 'yyyy-MM-dd') : String(value);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return null;
  const parsed = new Date(day + 'T00:00:00Z');
  return !isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === day ? day : null;
}

function dashboardHash_(data) {
  return Utilities.base64Encode(Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256, JSON.stringify(data), Utilities.Charset.UTF_8
  ));
}

function parseDashboardSheets_(dictionary, observations, timezone) {
  const fields = DASHBOARD_UPLOAD.metadata;
  const metadata = dashboardColumns_(dictionary, ['id_serie', ...fields], 'DICCIONARIO');
  const sourceUrl = dictionary[0].includes('source_url')
    ? dashboardColumns_(dictionary, ['source_url'], 'DICCIONARIO').source_url : -1;
  const values = dashboardColumns_(observations, ['id_serie', 'fecha', 'valor'], 'DATOS_LARGO');
  const seriesMetadata = Object.create(null);
  const seriesData = Object.create(null);
  for (let i = 1; i < dictionary.length; i++) {
    const row = dictionary[i];
    if (row.every(value => value === '')) continue;
    const id = row[metadata.id_serie];
    if (typeof id !== 'string' || !/^[A-Za-z0-9_-]+$/.test(id) || id in seriesMetadata) {
      throw new Error('DICCIONARIO, fila ' + (i + 1) + ': ID inválido o duplicado.');
    }
    for (const field of ['titulo_serie', 'frecuencia', 'unidad']) {
      if (typeof row[metadata[field]] !== 'string' || !row[metadata[field]].trim()) {
        throw new Error('DICCIONARIO, fila ' + (i + 1) + ': falta ' + field);
      }
    }
    const entry = Object.fromEntries(fields.map(field => [field, row[metadata[field]]]));
    entry.fuente = String(entry.fuente || '').split(/ \| (?:Archivo interno|Internal file):/)[0];
    if (sourceUrl >= 0 && /^https:\/\//i.test(String(row[sourceUrl] || ''))) entry.source_url = String(row[sourceUrl]);
    entry.frecuencia = DASHBOARD_ENGLISH_FREQUENCIES.get(entry.frecuencia) || entry.frecuencia;
    entry['área'] = DASHBOARD_ENGLISH_AREAS.get(entry['área']) || entry['área'];
    seriesMetadata[id] = entry;
    seriesData[id] = new Map();
  }
  let count = 0;
  for (let i = 1; i < observations.length; i++) {
    const row = observations[i];
    if (row.every(value => value === '')) continue;
    const id = row[values.id_serie];
    const day = dashboardDate_(row[values.fecha], timezone);
    const value = row[values.valor];
    if (!(id in seriesData) || !day || !Number.isFinite(value) || seriesData[id].has(day)) {
      throw new Error('DATOS_LARGO, fila ' + (i + 1) + ': ID, fecha o valor inválido o duplicado.');
    }
    seriesData[id].set(day, value);
    count++;
  }
  const ids = Object.keys(seriesMetadata).sort();
  if (!ids.length) throw new Error('El Excel no contiene series.');
  const rows = ids.map(id => {
    if (!seriesData[id].size) throw new Error('Sin observaciones para ' + id);
    return [id, [...seriesData[id]].sort(([a], [b]) => a.localeCompare(b))];
  });
  const hashes = {
    DICCIONARIO: dashboardHash_(ids.map(id => [id, seriesMetadata[id]])),
    DATOS_LARGO: dashboardHash_(rows)
  };
  const series = Object.fromEntries(rows.map(([id, data]) => [
    id, { ...seriesMetadata[id], observaciones: data }
  ]));
  return { hashes, series, count };
}

function commitDashboardSnapshot_(area, content, token) {
  return commitDashboardFiles_([{ path: 'drive_ingestion/snapshots/' + area + '.json', content }],
    'Update Drive data for ' + area, token);
}

function commitDashboardFiles_(files, message, token) {
  const config = DASHBOARD_UPLOAD;
  const ref = '/heads/' + encodeURIComponent(config.branch);
  const head = dashboardGithub_('/git/ref' + ref, 'get', null, token).object.sha;
  dashboardGithub_('/contents/.github/workflows/drive-preview.yml?ref=' + head, 'get', null, token);
  const base = dashboardGithub_('/git/commits/' + head, 'get', null, token).tree.sha;
  const entries = files.map(({ path, content }) => {
    const entry = { path, mode: '100644', type: 'blob' };
    if (content.length < 65536) return { ...entry, content };
    const blob = Utilities.newBlob(content, 'application/json');
    const { sha } = dashboardGithub_('/git/blobs', 'post', {
      content: Utilities.base64Encode(blob.getBytes()), encoding: 'base64'
    }, token);
    return { ...entry, sha };
  });
  const tree = dashboardGithub_('/git/trees', 'post', { base_tree: base, tree: entries }, token).sha;
  if (base === tree) return;
  const commit = dashboardGithub_('/git/commits', 'post', {
    message, tree, parents: [head]
  }, token);
  dashboardGithub_('/git/refs' + ref, 'patch', { sha: commit.sha, force: false }, token);
  return commit.sha;
}

function dashboardGithub_(path, method, body, token) {
  const response = UrlFetchApp.fetch('https://api.github.com/repos/' + DASHBOARD_UPLOAD.repository + path, {
    method,
    headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' },
    ...(body ? { contentType: 'application/json', payload: JSON.stringify(body) } : {}),
    muteHttpExceptions: true
  });
  if (response.getResponseCode() >= 300) {
    throw new Error('GitHub ' + method + ' ' + path + ': HTTP ' + response.getResponseCode());
  }
  return JSON.parse(response.getContentText());
}
