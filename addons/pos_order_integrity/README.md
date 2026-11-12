# Cafetería: controles de servidor para el POS (prototipo, no instalable)

Estado: rediseño escrito por análisis estático para Odoo 18. **No se ha instalado, ni cargado, ni ejecutado ninguna prueba en Odoo.** El manifest mantiene `installable: False` a propósito. Lo único comprobado es que los `.py` compilan (`py_compile`) y que los `.xml` están bien formados. No afirmar que funciona.

## Qué intenta hacer

Reglas del lado servidor (el navegador no cuenta):

| Regla | Dónde |
| --- | --- |
| El cajero no cambia precios: el precio de la línea debe coincidir con el de lista (o el de la tarifa del pedido) | `models/pos_order_line.py` |
| El cajero no aplica descuentos | idem |
| El cajero no devuelve (línea con `refunded_orderline_id`), no cancela, no elimina ni modifica pedidos confirmados | `pos_order.py`, `pos_order_line.py` |
| Devoluciones y correcciones de ventas confirmadas: solo gerente, con autor y fecha (motivo opcional) en `pos.order.audit.log` | `pos_audit.py` |
| Cantidad positiva; unidad y bolsa enteras; peso positivo con máximo 3 decimales (sin redondeo silencioso) | constraint en `pos_order_line.py` |
| Modos de venta unidad / bolsa / peso por producto; peso exige UdM en kg; bolsa exige unidades por bolsa | `models/product_template.py` |
| 0,250 kg x 20.000 COP/kg = 5.000 | `tests/test_price_validation.py` |
| Confirmación exige líneas, total positivo y pagos reales que sumen el total; `pos.payment` guardado | `pos_order.py`, `pos_payment.py` |
| Tarifa, posición fiscal e impuestos de línea validados contra la caja y el producto | `pos_order.py`, `pos_order_line.py` |
| Total del pedido y subtotales de línea recalculados en servidor (no se confía en `amount_*` ni `price_subtotal*` del cliente) | `pos_order.py`, `pos_order_line.py` |
| Costo manual por producto con indicador explícito de "costo conocido" | `product_template.py` |
| Costo histórico conservado en la línea al confirmar (`pos_unit_cost`, `pos_cost_known`, `pos_cost_date`) | `pos_order_line.py`, `pos_order.py` |

### Quién queda restringido

Se **deniega por defecto**: restringido es todo usuario que no esté en `Punto de venta: gerente de tienda` ni en `base.group_system`, aunque no tenga el grupo de cajero. Así olvidar asignar el grupo no abre el control. `env.su` (uid 1 y todo `sudo()` del código del servidor, incluido el de Odoo) nunca se restringe; un cliente RPC no puede activarlo. El grupo `Punto de venta: cajero restringido` sigue existiendo (implica `point_of_sale.group_pos_user`) para identificar cuentas de cajero. No asignar gerente y cajero a la misma cuenta; no compartir cuentas.

## Por qué ahora no se bloquean las escrituras internas de Odoo

El diseño anterior prohibía cualquier `write` sobre líneas de pedidos no borrador, y Odoo escribe `total_cost` e `is_total_cost_computed` después de marcar el pedido pagado, con el usuario de la sesión y sin `sudo`. Eso rompía el flujo. Soluciones descartadas y motivo:

- **Bandera en el contexto** (`with_context(...)`): el cliente controla el contexto en cualquier llamada RPC; un cajero la enviaría. Hay una prueba que lo intenta con varias claves.
- **Aceptar todo con `sudo`/`env.su`**: sirve para código nuestro, pero no para el código de Odoo que corre con el usuario del cajero.
- **Detectar la pila de llamadas**: frágil y suplantable.

Enfoque adoptado: control **por nombre de campo**, no por estado. Sobre una línea confirmada el cajero solo puede escribir `total_cost` e `is_total_cost_computed` (lista `LINE_SYSTEM_FIELDS`), y solo mientras el costo nativo aún no esté calculado (una vez por línea). Cualquier otro campo (`price_unit`, `qty`, `discount`, producto, impuestos, pedido) se rechaza. Esos dos campos no permiten alterar dinero cobrado, y el margen que usa el negocio sale de la instantánea propia (`pos_*`), que solo se escribe con `sudo` desde nuestro código y que nadie, ni el gerente, puede sobrescribir por RPC. Lo mismo en `pos.order` con `ORDER_SYSTEM_FIELDS` y transiciones de estado permitidas (`paid -> done/invoiced`, necesarias para cierre y facturación).

Riesgo residual: antes de que Odoo calcule el costo nativo, un cajero podría escribir `total_cost` con una llamada directa. Solo afectaría el costo nativo de Odoo, no el costo histórico propio.

## Costo desconocido no es cero

Un `Float` vacío vuelve como `0.0`, por eso hay dos campos en el producto: `pos_cost_known` (Boolean, por defecto desmarcado) y `pos_manual_cost`. Escribir un costo sin indicar nada lo marca como conocido; desmarcar el indicador lo reinicia a 0. Costo 0 con indicador marcado es "costo cero real". En la línea, `_pos_line_margin()` devuelve `None` si el costo era desconocido (no 100 % de margen). Ambos campos solo los leen/escriben gerente y administrador técnico (grupos a nivel de campo). Los reportes futuros deben filtrar por `pos_cost_known` y no sumar el margen de líneas sin costo como si fuera cero.

## Verificado y NO verificado

**Verificado (solo esto):**
- Sintaxis Python (`python3 -m py_compile`) de modelos y pruebas.
- XML bien formado (`xml.dom.minidom`) y manifest evaluable con `ast.literal_eval`.

**NO verificado:**
- Instalación del módulo, carga de vistas/xpath, grupos y ACL.
- Ejecución de cualquier prueba de `tests/` (escritas, no ejecutadas; los fixtures de sesión/config POS son conjeturas).
- Que el flujo real de venta (sincronización desde la interfaz, `add_payment`, `action_pos_order_paid`, cálculo de costo, cierre de sesión, facturación, impresión) no sea rechazado por las listas de campos y estados permitidos. Hay un test omitido (`test_full_odoo_payment_flow_with_cashier`) para esto.
- Si Odoo 18 crea el pedido ya en `paid` desde la interfaz (hoy se exige `draft` al crear; ver `ORDER_CREATE_STATES`).
- Si los campos `amount_*` y `price_subtotal*` son calculados o enviados por el cliente en Odoo 18 (se recalculan igualmente).
- Precios con tarifa, impuestos incluidos, posiciones fiscales y combos (los combos se rechazan; precio con tarifa usa API por confirmar; nombres de campos de pos.config para tarifas y posición fiscal por confirmar).
- Que el flujo de pago nativo (incluida la línea `is_change`) cumpla las nuevas exigencias de pagos al confirmar.
- Operación sin conexión: pedidos fabricados offline se validan al sincronizar, pero no se probó.

**Fuera de alcance de este módulo (no implementado):** cierre ciego de caja y ocultar totales al cajero; reglas de registro para que el cajero no lea historial, reportes ni costos de pedidos; registro de intentos rechazados (la excepción revierte la transacción, y registrar intentos exige un cursor aparte); asistente para capturar el motivo (ver limitaciones de la auditoría); relación bolsa/unidades con inventario.

## Puntos de atención al probar

- La precisión decimal `product.decimal_product_uom` se sube a 3 (`data/decimal_precision.xml`); es un cambio global de la base. Comprobar también el redondeo de la UdM kg en la interfaz del POS (TODO-VERIFICAR).
- Todo producto medido en kg debe tener modo "Peso"; por defecto los productos son "Unidad" (cantidad entera).
- Los gerentes siguen sujetos a las reglas de cantidad; las devoluciones deben llevar el enlace a la línea original.
- Borrar un pedido cancelado que tenga auditoría falla (`ondelete=restrict`) a propósito.

## Pruebas

`tests/` usa `TransactionCase` con etiquetas `post_install`, `-at_install`. Archivos: `test_price_validation`, `test_quantities_and_modes`, `test_confirmed_orders`, `test_refunds_corrections`, `test_cost_snapshot`, `test_internal_writes`, `test_payments`, `test_cash_helper`. Nunca se han ejecutado.

Entorno aislado: `__manifest__.py` es un archivo compartido y el compose principal monta `./addons` en lectura/escritura, así que **no se cambia `installable` en este repositorio**. Para probar, copiar `addons/` (o solo este módulo) a un directorio aparte, montar esa copia en el Odoo de pruebas (`dev/cafeteria/compose.yml` u otro aislado), poner `installable: True` solo en la copia y ejecutar `odoo -d <base_prueba> -i pos_order_integrity --test-tags /pos_order_integrity --stop-after-init`.

## Cobro, tarifa e impuestos (correcciones de revisión)

- **Confirmar un pedido (borrador a pagado) exige**, para usuarios restringidos: al menos una línea, `amount_total` mayor que cero, total igual a la suma de las líneas, al menos un pago y suma de `pos.payment` igual al total (con la tolerancia del redondeo de efectivo de la caja). La condición se evalúa siempre, también sin líneas. Un pedido vacío con total negativo se rechaza al crearlo.
- **`pos.payment`** (`models/pos_payment.py`): para restringidos, el pago debe ser positivo, de un método de la caja del pedido y de un pedido en borrador. La única excepción es la línea nativa de cambio (`is_change`, negativa y en efectivo); el cambio no puede superar los pagos en efectivo. Pagos de pedidos confirmados: no se crean, modifican ni eliminan por restringidos. Cuando un gerente cambia pagos de un pedido confirmado se registra en la auditoría.
- **Cancelar un borrador** (`state = cancel`, como puede hacer `remove_from_ui` antes de eliminar) se permite al cajero solo si no hay pagos. TODO-VERIFICAR la secuencia real en Odoo 18.
- **Tarifa y posición fiscal**: la tarifa del pedido debe ser la de la caja (o una de sus tarifas permitidas si la caja usa varias); la posición fiscal debe ser la predeterminada de la caja y un restringido no puede cambiarla. Las líneas deben llevar exactamente los impuestos del producto. Recomendación operativa: una sola tarifa y sin posiciones fiscales en la caja, para que el precio sea el de lista.

## Metodo de pago en efectivo: helper unico

Toda decision de "es efectivo" (linea de cambio, cambio contra efectivo cobrado) pasa por `is_cash_method` en `models/guard.py`: usa `payment_method.type == 'cash'` si el campo existe en el modelo, si no `is_cash_count`, y si no existe ninguno falla cerrado con un `UserError` claro. `pos_blind_cash_closing` tiene su propio helper equivalente (resuelve efectivo con `type == 'cash'` y fallback): como ese modulo depende de este y no al reves, no puede importarse en sentido contrario, asi que ambas reglas deben mantenerse alineadas a mano. `tests/test_cash_helper.py` prueba ambos caminos con un metodo simulado y el caso sin campos. Los tests de efectivo con cambio y de pago mixto (efectivo + Nequi) estan en `tests/test_payments.py`; sus fixtures (diario de efectivo, metodos de pago) son conjeturas por verificar.

## Decisión sobre permisos del gerente (A6)

El grupo gerente **no** implica `point_of_sale.group_pos_manager` (daría administración de la caja y de la configuración, más de lo que pide el alcance). Para que aun así funcione: el menú de auditoría cuelga de la raíz del POS (no de Informes) y tiene `groups`; el costo manual y los modos de venta del producto se editan con ACL propias de este módulo (lectura, escritura y creación de `product.template` y `product.product`, sin borrado). No se verificó que eso baste en Odoo 18 (reglas de registro, otras ACL de producto, menús de reportes nativos); si no basta, la alternativa es implicar `group_pos_manager`, decisión de Manuel.

## Limitaciones conocidas de la auditoría (M8)

- **El motivo casi nunca se registrará con la interfaz estándar.** Solo viaja por la clave de contexto `pos_audit_reason`, que la interfaz de Odoo y del POS no envía. En la práctica el motivo queda vacío salvo llamadas RPC o código que lo pasen. Hace falta un asistente o campo en la interfaz del gerente (no implementado). Como el motivo es opcional, esto no impide registrar autor y fecha.
- Autor y fecha sí se guardan siempre, pero solo para cambios hechos por usuarios no restringidos y no `sudo` sobre pedidos confirmados (pedido, líneas y pagos). Cambios con `sudo` desde código del servidor o shell no se registran.
- Los intentos rechazados no se registran (la excepción revierte la transacción).

## Ajustes globales de datos

- `data/decimal_precision.xml`: precisión `Product Unit of Measure` a 3 decimales.
- `data/uom_rounding.xml`: `uom.product_uom_kgm` con `rounding = 0.001` para que la interfaz no redondee 0,125 kg a 0,13 kg (TODO-VERIFICAR xmlid y campo).
- Ambos van en `noupdate="1"`: se aplican al instalar y no se revierten en cada actualización si el dueño los ajusta a mano. Son cambios globales de la base de la cafetería; confirmar con las demás unidades de medida antes de instalar.

## Lista de TODO-VERIFICAR

Se encuentra con `grep -rn TODO-VERIFICAR addons/pos_order_integrity`. Incluye: xmlids (`point_of_sale.group_pos_user`, `product.decimal_product_uom`, `uom.product_uom_categ_kgm/unit`, `point_of_sale.menu_point_rep`, `product.product_template_form_view`), campos nativos (`total_cost`, `is_total_cost_computed`, `refunded_orderline_id`, `tax_ids_after_fiscal_position`, `combo_parent_id`, `nb_print`, `account_move`, `session_move_id`, `cash_rounding`, `rounding_method`), firmas (`pricelist._get_product_price`, `account.tax.compute_all`), ACL de `group_pos_user`, creación de `pos.session` en pruebas y comportamiento de campos con `groups=` en la creación de productos.
