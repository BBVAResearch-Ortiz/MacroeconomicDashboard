/* Public observations published by the Türkiye Macro Monitor. */
const TURKEY_PUBLIC = (() => {
  const site = 'https://batuhan-barlas.github.io/turkey-macro-dashboard/';
  const endpoint = site + 'drive_ingestion/snapshots/turkey.json';
  const blocks = {
    INTEREST_RATES: 'Tipos de interés',
    INFLATION: 'Inflación',
    BALANCE_OF_PAYMENTS: 'Balanza de pagos',
    EXTERNAL_TRADE: 'Comercio exterior'
  };
  const catalogue = new Map();
  const translations = {
    'Tipos de interés': 'Interest rates',
    'Inflación': 'Inflation',
    'Balanza de pagos': 'Balance of payments',
    'Comercio exterior': 'External trade',
    'Préstamos y depósitos': 'Loans and deposits',
    'Diferenciales': 'Spreads',
    'Financiación y repos': 'Funding and repos',
    'IPC interanual': 'Annual CPI inflation',
    'Tendencia del IPC': 'CPI trend',
    'Flujo mensual': 'Monthly flow',
    'Acumulado de 12 meses': '12-month total'
  };
  function add(id, label, english, block, family, freq, unit, required = true) {
    catalogue.set('TR_' + id, {label, block, family, freq, unit, required});
    translations[label] = english;
  }
  [
    ['GPL', 'Crédito personal', 'Personal loan rate'],
    ['AUTO', 'Crédito para automóviles', 'Auto loan rate'],
    ['MORTGAGE', 'Crédito hipotecario', 'Mortgage rate'],
    ['COMMERCIAL', 'Crédito comercial', 'Commercial loan rate'],
    ['CONSUMER', 'Crédito al consumo', 'Consumer loan rate'],
    ['DEPOSIT', 'Depósitos en liras turcas', 'Turkish lira deposit rate']
  ].forEach(row => add(...row, 'INTEREST_RATES', 'Préstamos y depósitos', 'W', '%'));
  [
    ['COMM_SPREAD', 'Diferencial de crédito comercial', 'Commercial loan spread'],
    ['CONS_SPREAD', 'Diferencial de crédito al consumo', 'Consumer loan spread']
  ].forEach(row => add(...row, 'INTEREST_RATES', 'Diferenciales', 'W', '%'));
  [
    ['FUNDING', 'Tipo de financiación del banco central', 'Central bank funding rate', true],
    ['REPO', 'Tipo repo', 'Repo rate', true],
    ['LOWER_BAND', 'Límite inferior del corredor', 'Lower corridor bound', false],
    ['UPPER_BAND', 'Límite superior del corredor', 'Upper corridor bound', false]
  ].forEach(([id, es, en, required]) => add(id, es, en, 'INTEREST_RATES', 'Financiación y repos', 'D', '%', required));
  [
    ['HEADLINE', 'CPI', 'general', 'headline CPI'],
    ['CORE_B', 'CORE_B', 'subyacente B', 'core CPI B'],
    ['CORE_C', 'CORE_C', 'subyacente C', 'core CPI C'],
    ['GOODS', 'GOODS', 'de bienes', 'goods CPI'],
    ['SERVICES', 'SERVICES', 'de servicios', 'services CPI']
  ].forEach(([annualId, trendId, es, en]) => {
    add('CPI_' + annualId, 'IPC ' + es + ' · interanual', en + ' · year on year', 'INFLATION', 'IPC interanual', 'M', '% y/y');
    add('TREND_' + trendId, 'IPC ' + es + ' · tendencia', en + ' · trend', 'INFLATION', 'Tendencia del IPC', 'M', '% m/m');
  });
  [
    ['BOP_CAD', 'Cuenta corriente', 'Current account', 'BALANCE_OF_PAYMENTS'],
    ['BOP_FIN', 'Cuenta financiera', 'Financial account', 'BALANCE_OF_PAYMENTS'],
    ['BOP_NEO', 'Errores y omisiones netos', 'Net errors and omissions', 'BALANCE_OF_PAYMENTS'],
    ['BOP_RES', 'Transacciones de reservas', 'Reserve transactions', 'BALANCE_OF_PAYMENTS'],
    ['TRADE_EXPORT', 'Exportaciones de bienes', 'Goods exports', 'EXTERNAL_TRADE'],
    ['TRADE_IMPORT', 'Importaciones de bienes', 'Goods imports', 'EXTERNAL_TRADE'],
    ['TRADE_BALANCE', 'Saldo comercial de bienes', 'Goods trade balance', 'EXTERNAL_TRADE']
  ].forEach(([id, es, en, block]) => {
    add(id, es + ' · mensual', en + ' · monthly', block, 'Flujo mensual', 'M', 'USD bn');
    add(id + '_12M', es + ' · 12 meses', en + ' · 12 months', block, 'Acumulado de 12 meses', 'M', 'USD bn');
  });
  const frequencies = {Diaria: 'D', Semanal: 'W', Mensual: 'M', D: 'D', W: 'W', M: 'M'};
  const idFor = id => 'public_tr_' + id;
  const isoDay = day => {
    if (typeof day !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(day)) return false;
    const date = new Date(day + 'T00:00:00Z');
    return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === day;
  };
  function parse(snapshot) {
    const updated = snapshot?.origen?.updated_at;
    const rows = snapshot?.series;
    if (typeof updated !== 'string' || !/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC$/.test(updated) ||
        !rows || typeof rows !== 'object' || Array.isArray(rows)) {
      throw new Error('Invalid Türkiye source snapshot');
    }
    const series = {};
    let latest = '';
    for (const [id, meta] of catalogue) {
      const entry = rows[id];
      if (!entry && !meta.required) continue;
      if (!entry || entry.bloque !== meta.block || frequencies[entry.frecuencia] !== meta.freq ||
          entry.unidad !== meta.unit || typeof entry.fuente !== 'string' || !entry.fuente.trim() ||
          !Array.isArray(entry.observaciones) || !entry.observaciones.length) {
        throw new Error('Missing or incompatible Türkiye series: ' + id);
      }
      let last = '';
      const data = entry.observaciones.map(point => {
        if (!Array.isArray(point) || !isoDay(point[0]) || point[0] <= last ||
            (meta.freq === 'M' && !point[0].endsWith('-01')) || !Number.isFinite(point[1])) {
          throw new Error('Invalid observation in Türkiye series: ' + id);
        }
        last = point[0];
        return [last, point[1], 0];
      });
      latest = latest > last ? latest : last;
      series[idFor(id)] = {
        label: meta.label, unit: meta.unit, freq: meta.freq, block: meta.block, family: meta.family,
        source: entry.fuente, code: id, link: site,
        transform: typeof entry.transformacion_y_calculo === 'string' ? entry.transformacion_y_calculo : '',
        data
      };
    }
    return {version: updated, latest, series};
  }
  async function load(previousVersion) {
    const response = await fetch(endpoint, {cache: 'no-store', credentials: 'omit', signal: AbortSignal.timeout(12000)});
    if (!response.ok) throw new Error('Türkiye source HTTP ' + response.status);
    const snapshot = await response.json();
    if (previousVersion && snapshot?.origen?.updated_at === previousVersion) return null;
    return parse(snapshot);
  }
  return {site, endpoint, blocks, translations, idFor, parse, load};
})();

if (typeof module === 'object' && typeof require === 'function') {
  module.exports = TURKEY_PUBLIC;
  if (require.main === module) {
    TURKEY_PUBLIC.load().then(({version, latest, series}) => {
      console.log(`Türkiye source: ${Object.keys(series).length} valid series. Publication: ${version}. Latest observation: ${latest}.`);
    }).catch(error => {
      console.error(error.message);
      process.exitCode = 1;
    });
  }
}
