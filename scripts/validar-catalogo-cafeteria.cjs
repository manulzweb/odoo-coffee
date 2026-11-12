#!/usr/bin/env node
// Validación local previa; no importa datos ni modifica Odoo.
const fs = require('node:fs');
const required = ['referencia', 'nombre', 'categoria', 'unidad', 'precio_venta', 'costo_manual', 'unidades_por_bolsa'];

function parseCsv(source) {
  const rows = []; let row = [], field = '', quoted = false, afterQuote = false, start = true;
  source = source.replace(/^\uFEFF/, '');
  for (let i = 0; i < source.length; i++) {
    const c = source[i];
    if (quoted) {
      if (c === '"' && source[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') { quoted = false; afterQuote = true; }
      else field += c;
      continue;
    }
    if (afterQuote && ![',', '\r', '\n'].includes(c)) throw new Error('Caracteres después de cierre de comillas.');
    if (c === '"') { if (!start) throw new Error('Comillas en campo sin entrecomillar.'); quoted = true; start = false; }
    else if (c === ',') { row.push(field); field = ''; start = true; afterQuote = false; }
    else if (c === '\r' || c === '\n') {
      if (c === '\r' && source[i + 1] === '\n') i++;
      row.push(field); rows.push(row); row = []; field = ''; start = true; afterQuote = false;
    } else { field += c; start = false; }
  }
  if (quoted) throw new Error('Campo entre comillas sin cerrar.');
  if (row.length || field || !start) { row.push(field); rows.push(row); }
  return rows;
}

function validate(source) {
  const rows = parseCsv(source), errors = [];
  if (!rows.length || rows[0].length !== required.length || !required.every((h, i) => h === rows[0][i].trim())) {
    return ['Cabecera inválida. Usa exactamente la plantilla, sin cambiar el orden.'];
  }
  const seen = new Set(); let count = 0;
  rows.slice(1).forEach((r, index) => {
    if (r.every(x => !x.trim())) return;
    count++; const line = index + 2;
    if (r.length !== required.length) { errors.push(`Fila ${line}: se esperaban ${required.length} columnas, se recibieron ${r.length}.`); return; }
    const [ref, name, category, unit, price, cost, pack] = r.map(x => x.trim());
    if (!ref || !name || !category) errors.push(`Fila ${line}: referencia, nombre y categoría son obligatorios.`);
    const key = ref.toLocaleLowerCase('es');
    if (ref && seen.has(key)) errors.push(`Fila ${line}: referencia duplicada.`);
    if (ref) seen.add(key);
    if (!['unidad', 'bolsa', 'kg'].includes(unit)) errors.push(`Fila ${line}: unidad debe ser unidad, bolsa o kg.`);
    const money = /^(?:0|[1-9]\d*)(?:\.\d{1,2})?$/;
    if (!money.test(price) || Number(price) <= 0) errors.push(`Fila ${line}: precio_venta debe ser un número positivo con punto decimal, sin separador de miles.`);
    if (cost && (!money.test(cost) || Number(cost) < 0)) errors.push(`Fila ${line}: costo_manual debe ser vacío o un número no negativo con punto decimal.`);
    if (unit === 'bolsa' && (!/^[1-9]\d*$/.test(pack) || !Number.isSafeInteger(Number(pack)))) errors.push(`Fila ${line}: una bolsa debe indicar unidades_por_bolsa como entero positivo.`);
    if (unit !== 'bolsa' && pack) errors.push(`Fila ${line}: unidades_por_bolsa solo se usa para bolsas.`);
  });
  if (!count) errors.push('El catálogo no contiene productos.');
  return errors;
}

if (require.main === module) {
  if (process.argv.length !== 3) { console.error('Uso: node scripts/validar-catalogo-cafeteria.cjs ruta.csv'); process.exitCode = 2; }
  else try {
    const errors = validate(fs.readFileSync(process.argv[2], 'utf8'));
    if (errors.length) { console.error(errors.join('\n')); process.exitCode = 1; }
    else console.log('Validación local correcta. La importación a Odoo aún requiere comprobar el mapeo y la configuración.');
  } catch (error) { console.error(`No se pudo validar: ${error.message}`); process.exitCode = 2; }
}
module.exports = { parseCsv, validate };
