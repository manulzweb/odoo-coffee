# Importacion del catalogo a Odoo 18

Origen: planilla manuscrita "Mi Cafeteria - Producto en venta" (columnas costo y venta), transcrita el 12 de noviembre de 2026.

- `../catalogo-cafeteria.csv`: transcripcion validada con `node scripts/validar-catalogo-cafeteria.cjs docs/catalogo-cafeteria.csv`.
- `product.template.csv`: archivo para Punto de venta > Productos > Importar registros, con el modulo `pos_order_integrity` instalado y un usuario del grupo "Punto de venta: gerente de tienda" o administrador. Los identificadores externos (`cafeteria_catalogo.caf_NNN`) hacen la importacion repetible: reimportar actualiza, no duplica.

Decisiones de mapeo:

- `list_price` = precio de venta; `pos_manual_cost` = costo (el modulo marca el costo como conocido). `standard_price` se deja sin cargar a proposito.
- `taxes_id/id` vacio: los precios de la planilla se cobran tal cual, sin impuesto anadido. Confirmar con el contador.
- Todos los productos entran como venta por unidad (`pos_sale_mode = unit`).

Pendiente de confirmar con don Efrain antes de produccion:

1. Lecturas dudosas por tachones: costo de Vaso 5.5 (1833), venta de Mantequilla (1400), venta de Chocolisto (2100).
2. Aromatica pequena, Vaso 3 y Tostada no tienen precio en la planilla y no se cargaron.
3. Presentacion de cada producto (unidad, bolsa, paquete) y categorias; las categorias del CSV son una propuesta.
4. Nombres normalizados respecto a la planilla: "Juan Valdes" a "Juan Valdez", "Istacren" a "Instacrem".

No verificado: la importacion no se ha ejecutado en Odoo.
