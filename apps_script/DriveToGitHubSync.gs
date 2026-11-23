/**
 * Sync CSV files from one Google Drive folder to the public manual_csv/ folder
 * in marcos-laserna/fow_alvaro. Store credentials in Script Properties only.
 *
 * Required Script Properties:
 *   DRIVE_FOLDER_ID  Google Drive folder ID containing CSV files
 *   GITHUB_TOKEN     Fine-grained token with Contents: Read and write
 */
const CONFIG = {
  owner: 'BBVAResearch-Ortiz',
  repo: 'MacroeconomicDashboard',
  branch: 'drive_processing',
  githubFolder: 'manual_csv'
};

function syncDriveToGitHub() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(1000)) return;
  try {
    const props = PropertiesService.getScriptProperties();
    const folderId = props.getProperty('DRIVE_FOLDER_ID');
    const token = props.getProperty('GITHUB_TOKEN');
    if (!folderId || !token) throw new Error('Set DRIVE_FOLDER_ID and GITHUB_TOKEN in Script Properties.');

    const folder = DriveApp.getFolderById(folderId);
    const iterator = folder.getFiles();
    const manifestFiles = [];
    const seenIds = {};
    let latestDriveUpdate = null;

    while (iterator.hasNext()) {
      const driveFile = iterator.next();
      const originalName = driveFile.getName();
      if (!/\.csv$/i.test(originalName)) continue;

      const csv = driveFile.getBlob().getDataAsString('UTF-8').replace(/^\uFEFF/, '');
      const parsed = parseSeriesCsv_(csv, originalName);
      if (seenIds[parsed.id]) throw new Error('Two Drive files produce the same series ID: ' + parsed.id);
      seenIds[parsed.id] = true;

      const githubName = parsed.id + '.csv';
      const githubPath = CONFIG.githubFolder + '/' + githubName;
      putGithubFile_(githubPath, csv, 'Sync Drive CSV: ' + parsed.id, token);

      const updated = driveFile.getLastUpdated();
      if (!latestDriveUpdate || updated.getTime() > latestDriveUpdate.getTime()) latestDriveUpdate = updated;
      manifestFiles.push({
        id: parsed.id,
        file: githubName,
        label: parsed.label,
        unit: parsed.unit,
        freq: parsed.freq,
        block: parsed.block,
        source: 'Google Drive · CSV',
        updated_at: updated.toISOString()
      });
    }

    manifestFiles.sort(function (a, b) { return a.id.localeCompare(b.id); });
    const manifest = {
      version: 1,
      updated_at: latestDriveUpdate ? latestDriveUpdate.toISOString() : null,
      files: manifestFiles
    };
    putGithubFile_(CONFIG.githubFolder + '/manifest.json', JSON.stringify(manifest, null, 2) + '\n', 'Update manual CSV manifest', token);
    Logger.log('Manual CSV sync complete: ' + manifestFiles.length + ' series.');
  } finally {
    lock.releaseLock();
  }
}

/** Run once in Apps Script to create a five-minute Drive polling trigger. */
function installDriveSyncTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (trigger) {
    if (trigger.getHandlerFunction() === 'syncDriveToGitHub') ScriptApp.deleteTrigger(trigger);
  });
  ScriptApp.newTrigger('syncDriveToGitHub').timeBased().everyMinutes(5).create();
}

function parseSeriesCsv_(text, fileName) {
  const firstLine = text.split(/\r?\n/).find(function (line) { return line.trim(); }) || '';
  const delimiter = firstLine.split(';').length > firstLine.split(',').length ? ';' : ',';
  const rows = Utilities.parseCsv(text, delimiter).filter(function (row) {
    return row.some(function (cell) { return String(cell).trim() !== ''; });
  });
  if (rows.length < 2) throw new Error(fileName + ' needs a header and at least one observation.');

  const norm = function (value) {
    return String(value || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '');
  };
  const headers = rows[0].map(norm);
  const index = function (names) { return headers.findIndex(function (header) { return names.indexOf(header) >= 0; }); };
  const dateIndex = index(['date', 'fecha', 'period', 'periodo']);
  const valueIndex = index(['value', 'valor', 'observation', 'observacion']);
  if (dateIndex < 0 || valueIndex < 0) throw new Error(fileName + ' needs fecha/date and valor/value columns.');

  const metadata = function (names) {
    const ix = index(names);
    if (ix < 0) return '';
    for (let i = 1; i < rows.length; i++) {
      const value = String(rows[i][ix] || '').trim();
      if (value) return value;
    }
    return '';
  };
  const observations = [];
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    if (!String(row[dateIndex] || '').trim() && !String(row[valueIndex] || '').trim()) continue;
    const date = normalizeDate_(row[dateIndex]);
    const value = parseNumber_(row[valueIndex], delimiter);
    if (!date || value === null) throw new Error(fileName + ' has an invalid date or value on row ' + (i + 1) + '.');
    observations.push({ date: date, value: value });
  }
  if (!observations.length) throw new Error(fileName + ' contains no usable observations.');
  observations.sort(function (a, b) { return a.date.localeCompare(b.date); });

  const stem = fileName.replace(/\.csv$/i, '');
  const id = slug_(metadata(['id', 'seriesid', 'serieid']) || stem);
  const label = metadata(['label', 'etiqueta', 'seriesname', 'nombre']) || stem.replace(/[_-]+/g, ' ');
  const unit = metadata(['unit', 'unidad']) || 'valor';
  const frequency = (metadata(['freq', 'frequency', 'frecuencia', 'periodicity', 'periodicidad']) || inferFrequency_(observations)).toUpperCase();
  if (['D', 'M', 'Q'].indexOf(frequency) < 0) throw new Error(fileName + ' frequency must be D, M, or Q.');
  const allowedBlocks = ['actividad', 'coyuntura', 'empleo', 'precios', 'vivienda', 'publico', 'exterior', 'financiero', 'credito', 'manual'];
  const requestedBlock = metadata(['block', 'bloque']).toLowerCase();
  const block = allowedBlocks.indexOf(requestedBlock) >= 0 ? requestedBlock : 'manual';
  return { id: id, label: label, unit: unit, freq: frequency, block: block };
}

function normalizeDate_(value) {
  const s = String(value || '').trim();
  let m;
  if ((m = s.match(/^(\d{4})[-/](\d{1,2})(?:[-/](\d{1,2}))?$/))) {
    const year = Number(m[1]), month = Number(m[2]), day = Number(m[3] || 1);
    if (month < 1 || month > 12 || day < 1 || day > 31) return '';
    return m[1] + '-' + ('0' + month).slice(-2) + '-' + ('0' + day).slice(-2);
  }
  if ((m = s.match(/^(\d{4})\s*[- ]?[QqTt]([1-4])$/))) {
    const month = (Number(m[2]) - 1) * 3 + 1;
    return m[1] + '-' + ('0' + month).slice(-2) + '-01';
  }
  if ((m = s.match(/^(\d{1,2})[/.](\d{1,2})[/.](\d{4})$/))) {
    const day = Number(m[1]), month = Number(m[2]);
    if (month < 1 || month > 12 || day < 1 || day > 31) return '';
    return m[3] + '-' + ('0' + month).slice(-2) + '-' + ('0' + day).slice(-2);
  }
  return '';
}

function parseNumber_(value, delimiter) {
  let text = String(value || '').trim().replace(/[\s\u00a0]/g, '');
  if (!text) return null;
  if (delimiter === ';' && text.indexOf(',') >= 0) text = text.replace(/\./g, '').replace(',', '.');
  else if (text.indexOf(',') >= 0 && text.indexOf('.') >= 0) text = text.replace(/,/g, '');
  else if (text.indexOf(',') >= 0) text = text.replace(',', '.');
  const number = Number(text);
  return isFinite(number) ? number : null;
}

function inferFrequency_(observations) {
  if (observations.length < 2) return 'M';
  const gaps = [];
  for (let i = 1; i < observations.length; i++) {
    gaps.push((new Date(observations[i].date) - new Date(observations[i - 1].date)) / 86400000);
  }
  gaps.sort(function (a, b) { return a - b; });
  const median = gaps[Math.floor(gaps.length / 2)];
  return median <= 7 ? 'D' : median <= 45 ? 'M' : 'Q';
}

function slug_(value) {
  const slug = String(value).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9_-]+/g, '_').replace(/^[_-]+|[_-]+$/g, '').slice(0, 60);
  if (!slug) throw new Error('CSV filename or id must produce a valid series ID.');
  return slug;
}

function putGithubFile_(path, text, message, token) {
  const existing = getGithubFile_(path, token);
  if (existing && existing.text === text) return false;
  const payload = {
    message: message,
    content: Utilities.base64Encode(Utilities.newBlob(text, 'text/plain').getBytes()),
    branch: CONFIG.branch
  };
  if (existing) payload.sha = existing.sha;
  const response = UrlFetchApp.fetch(githubContentsUrl_(path), {
    method: 'put', contentType: 'application/json',
    headers: githubHeaders_(token), payload: JSON.stringify(payload), muteHttpExceptions: true
  });
  const status = response.getResponseCode();
  if (status < 200 || status >= 300) throw new Error('GitHub could not update ' + path + ' (HTTP ' + status + '): ' + response.getContentText().slice(0, 300));
  return true;
}

function getGithubFile_(path, token) {
  const response = UrlFetchApp.fetch(githubContentsUrl_(path) + '?ref=' + encodeURIComponent(CONFIG.branch), {
    method: 'get', headers: githubHeaders_(token), muteHttpExceptions: true
  });
  const status = response.getResponseCode();
  if (status === 404) return null;
  if (status < 200 || status >= 300) throw new Error('GitHub could not read ' + path + ' (HTTP ' + status + ').');
  const result = JSON.parse(response.getContentText());
  const encoded = String(result.content || '').replace(/\s/g, '');
  const text = Utilities.newBlob(Utilities.base64Decode(encoded)).getDataAsString('UTF-8');
  return { sha: result.sha, text: text };
}

function githubContentsUrl_(path) {
  const encodedPath = path.split('/').map(encodeURIComponent).join('/');
  return 'https://api.github.com/repos/' + CONFIG.owner + '/' + CONFIG.repo + '/contents/' + encodedPath;
}

function githubHeaders_(token) {
  return {
    Authorization: 'Bearer ' + token,
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28'
  };
}
