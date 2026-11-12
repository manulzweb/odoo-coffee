# Catálogo inicial: recopilación y validación

Usar `catalogo-cafeteria-plantilla.csv` para recopilar los datos. Esta plantilla es de trabajo: **no es un archivo de importación directa a Odoo**. El mapeo definitivo, los impuestos, la unidad de medida y el comportamiento del costo deben comprobarse en una base de pruebas.

Una fila por presentación vendida: pan individual y bolsa se registran por separado, cada una con su precio y costo propios. `unidades_por_bolsa` documenta el contenido de la bolsa; no crea conversiones ni descuenta inventario. No inventar productos ni costos. El costo vacío significa desconocido, no costo cero; una ganancia no puede calcularse con fiabilidad si falta.

| Columna | Contenido |
| --- | --- |
| referencia | Código interno único acordado para identificar la presentación. |
| nombre | Nombre legible para el cajero. |
| categoria | Categoría comercial, por ejemplo Panes o Bebidas. |
| unidad | `unidad`, `bolsa` o `kg`. |
| precio_venta | Precio por unidad, bolsa o kilogramo en COP, positivo. |
| costo_manual | Costo por esa misma unidad en COP; dejar vacío si se desconoce. |
| unidades_por_bolsa | Entero positivo solo para bolsas. |

Guardar UTF-8 con separador coma. Las cifras usan punto para decimales, sin signo de moneda ni separadores de miles. Si un nombre lleva coma, el editor CSV debe entrecomillarlo. No incluir datos de clientes ni ventas en el catálogo.

Desde la raíz del proyecto, validar sin importar ni modificar datos:

```powershell
node scripts/validar-catalogo-cafeteria.cjs docs/catalogo-cafeteria-plantilla.csv
node --test scripts/validar-catalogo-cafeteria.test.cjs
```

La plantilla vacía se rechaza hasta que se agregue al menos un producto. Conservar una copia de la información original; probar importación y resultados en base aislada antes de usar datos en producción.
