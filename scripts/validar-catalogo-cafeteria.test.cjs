const { test } = require('node:test');
const assert = require('node:assert/strict');
const { parseCsv, validate } = require('./validar-catalogo-cafeteria.cjs');
const header = 'referencia,nombre,categoria,unidad,precio_venta,costo_manual,unidades_por_bolsa\n';
test('acepta unidades y bolsas sin costo y textos con comas', () => {
  assert.deepEqual(validate(header + 'P01,"Pan, tradicional",Panes,bolsa,5000,,10\nQ01,Queso,Lácteos,kg,20000,15000,\n'), []);
});
test('detecta datos inválidos y referencias repetidas', () => {
  const result = validate(header + 'A,Café,Bebidas,unidad,0,-1,2\na,Pan,Panes,bolsa,5000,,0\n');
  assert.ok(result.some(x => x.includes('precio_venta')));
  assert.ok(result.some(x => x.includes('costo_manual')));
  assert.ok(result.some(x => x.includes('duplicada')));
  assert.ok(result.filter(x => x.includes('unidades_por_bolsa')).length === 2);
});
test('detecta catálogo vacío y cabecera incorrecta', () => {
  assert.ok(validate(header).length);
  assert.ok(validate('nombre,precio\nPan,1000\n').length);
});
test('analiza comillas escapadas y rechaza comillas malformadas', () => {
  assert.equal(parseCsv('"Pan ""especial""",1')[0][0], 'Pan "especial"');
  assert.throws(() => parseCsv('"sin cerrar'));
});
