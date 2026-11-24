const DASHBOARD_UPLOAD = {
  root: '1Ejg2KKXKKT1QOjTb0OZFcZ0y2vUry2cr',
  areas: { spain: 'Spain', global: 'Global Scenarios', turkey: 'Turkiye' },
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  folder: 'application/vnd.google-apps.folder',
  spreadsheet: 'application/vnd.google-apps.spreadsheet',
  repository: 'BBVAResearch-Ortiz/MacroeconomicDashboard',
  branch: 'drive_processing',
  tokenProperty: 'FOW_DASHBOARD_GITHUB_TOKEN',
  metadata: [
    'titulo_serie', 'subtitulo_descripcion', 'transformacion_y_calculo', 'fuente',
    'frecuencia_y_cobertura_temporal', 'tipo_grafico', 'bloque', 'área', 'frecuencia', 'unidad'
  ]
};

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
  if (!books.length) {
    console.log(area + ': carpeta sin Excel.');
    return;
  }
  if (books.length !== 1) throw new Error('Se esperaba un Excel. Encontrados: ' + books.length);
  const book = books[0];
  const key = 'FOW_UPLOAD_V1_' + area;
  const previous = JSON.parse(properties.getProperty(key) || '{}');
  const revision = book.id + ':' + (book.md5Checksum || book.version);
  if (token && revision === previous.revision) {
    console.log(area + ': Excel sin cambios.');
    return;
  }

  const parsed = readDashboardWorkbook_(book);
  if (area === 'spain') {
    const supported = ['D', 'M', 'Q', 'Diaria', 'Mensual', 'Trimestral'];
    for (const [id, entry] of Object.entries(parsed.series)) {
      if (!supported.includes(entry.frecuencia)) {
        throw new Error('Frecuencia fuera de las admitidas en el Blackboard: ' + id);
      }
    }
  }
  const changed = Object.keys(parsed.hashes).filter(name => parsed.hashes[name] !== (previous.hashes || {})[name]);
  if (changed.length && token) {
    const payload = { origen: { name: book.name }, series: parsed.series };
    commitDashboardSnapshot_(area, JSON.stringify(payload) + '\n', token);
  }
  if (token) properties.setProperty(key, JSON.stringify({ revision, hashes: parsed.hashes }));
  console.log(area + ': ' + Object.keys(parsed.series).length + ' series y ' + parsed.count +
    ' observaciones. Hojas con cambios: ' + (changed.join(', ') || 'ninguna'));
}

function dashboardWorkbookRows_(workbook, name) {
  const sheet = workbook.getSheetByName(name);
  if (!sheet) throw new Error('Falta la hoja ' + name);
  return sheet.getDataRange().getValues();
}

function readDashboardWorkbook_(book) {
  const blob = DriveApp.getFileById(book.id).getBlob();
  const temporary = Drive.Files.create({
    name: 'FoW temporal – ' + book.name,
    mimeType: DASHBOARD_UPLOAD.spreadsheet
  }, blob, { fields: 'id' });
  try {
    const workbook = SpreadsheetApp.openById(temporary.id);
    return parseDashboardSheets_(
      dashboardWorkbookRows_(workbook, 'DICCIONARIO'),
      dashboardWorkbookRows_(workbook, 'DATOS_LARGO'),
      workbook.getSpreadsheetTimeZone()
    );
  } finally {
    Drive.Files.update({ trashed: true }, temporary.id);
  }
}

function dashboardColumns_(rows, expected, name) {
  const headers = rows[0] || [];
  const columns = Object.create(null);
  for (const field of expected) {
    const index = headers.indexOf(field);
    if (index < 0 || index !== headers.lastIndexOf(field)) {
      throw new Error(name + ': falta la columna ' + field + ' o está duplicada.');
    }
    columns[field] = index;
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
    entry.fuente = String(entry.fuente || '').split(' | Archivo interno:')[0];
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
  const config = DASHBOARD_UPLOAD;
  const ref = '/heads/' + encodeURIComponent(config.branch);
  const head = dashboardGithub_('/git/ref' + ref, 'get', null, token).object.sha;
  dashboardGithub_('/contents/.github/workflows/drive-preview.yml?ref=' + head, 'get', null, token);
  const blob = Utilities.newBlob(content, 'application/json');
  const sha = dashboardGithub_('/git/blobs', 'post', {
    content: Utilities.base64Encode(blob.getBytes()), encoding: 'base64'
  }, token).sha;
  const base = dashboardGithub_('/git/commits/' + head, 'get', null, token).tree.sha;
  const tree = dashboardGithub_('/git/trees', 'post', { base_tree: base, tree: [
    { path: 'drive_ingestion/snapshots/' + area + '.json', mode: '100644', type: 'blob', sha }
  ] }, token).sha;
  if (base === tree) return;
  const commit = dashboardGithub_('/git/commits', 'post', {
    message: 'Update Drive data for ' + area, tree, parents: [head]
  }, token);
  dashboardGithub_('/git/refs' + ref, 'patch', { sha: commit.sha, force: false }, token);
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
