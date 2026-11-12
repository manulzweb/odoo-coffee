# Cafetería: cierre de caja ciego (pos_blind_cash_closing)

Estado: **no instalable** (`installable: False`; el manifiesto es compartido, ver la prueba manual para trabajar con una copia). Análisis estático solamente: no se ha instalado, cargado ni ejecutado nada en Odoo 18, y las pruebas de `tests/` están escritas pero no ejecutadas. Depende de `pos_order_integrity`, que también es no instalable. No afirmar que funciona hasta pasar la lista de verificación de abajo en una base aislada.

## Dependencia de otro módulo (grupos)

Los grupos los define `pos_order_integrity` (otro agente). Este módulo solo referencia sus ids XML y no los redefine ni edita ese módulo:

- `pos_order_integrity.group_pos_store_manager`: Efraín (gerente). Ve diferencias de caja, totales y costos.
- `base.group_system`: Manuel (administrador técnico). Ve lo mismo.
- `pos_order_integrity.group_cashier_restricted`: cajero. Solo se usa en pruebas; la restricción no depende de tener este grupo.

Alcance de la restricción: está ciego todo usuario con `point_of_sale.group_pos_user` (que el grupo de cajero del guard implica) que no sea gerente de la cafetería ni administrador técnico, tenga o no el grupo de cajero. Un POS manager nativo sin el grupo de gerente de la cafetería también queda ciego (deliberado). Los usuarios sin ningún grupo POS (p. ej. contabilidad) no se ven afectados por las reglas ni por los filtros: si no deben ver ventas, no darles acceso a modelos pos.*. Si el guard renombra esos ids, hay que actualizar `models/blind_common.py`, `security/`, `views/` y `hooks.py`.

## Qué hace

1. **Cierre ciego.** El cajero abre con efectivo inicial y cierra informando el efectivo contado. `get_closing_control_data` devuelve al cajero solo nombres de medios de pago con importes en cero, sin llamar a `super()`. `post_closing_cash_details` y `close_session_from_ui` calculan en el servidor el efectivo esperado (inicial + pagos en efectivo + entradas/salidas) y guardan la diferencia en el modelo `pos.blind.cash.closing`, que no devuelven. Existe además `pos_blind_close(counted_cash, notes)` como punto de entrada único.
2. **Registro de diferencias.** `pos.blind.cash.closing`: efectivo inicial, ventas en efectivo, esperado, contado, diferencia, cajero y fechas. Inmutable (solo `sudo()` del servidor escribe), sin ACL para el cajero (ni lectura). Menú "Cierres de caja" solo para gerente y administrador. Incluye un control cruzado con el esperado nativo de la sesión (`odoo_mismatch`).
3. **Reglas de registro globales** (`security/security_rules.xml` y `hooks.py`): el cajero solo ve su propia sesión abierta y solo la venta en curso (pedido en borrador de esa sesión, con sus líneas y pagos). No ve sesiones anteriores, pedidos cobrados, pagos por medio, movimientos de caja de sesiones POS ni el reporte `report.pos.order`. Esto cubre `read`, `search_read`, `read_group`, `search_count` y lecturas por id, porque las reglas se aplican en todas esas rutas.
4. **Ventana interna.** Odoo necesita leer los pedidos cobrados mientras sincroniza una venta. En vez de `sudo()` (que anularía las validaciones de `pos_order_integrity`, que trata `env.su` como código de confianza) se usa una bandera local al hilo, activada solo por este módulo, que las reglas consultan mediante el campo técnico de búsqueda `pos.session.pos_window`. Una llamada RPC es una petición independiente: no puede activarla, y claves de contexto como `pos_window` no tienen efecto (hay prueba).
5. **Totales de sesión** (`cash_register_balance_end`, `cash_register_difference`, `cash_register_total_entry_encoding`, `total_payments_amount`, `order_count`, y variantes antiguas si existen): filtro en `read()`, rechazo de dominios, `order=`, `groupby`, agregados y rutas que los mencionen (escaneo de texto, falla cerrado, también con objetos `Domain`), y bloqueo de `export_data` y `onchange`. `groups=` sobre esos campos está **desactivado** (`USE_FIELD_GROUPS = False` en `blind_common.py`): asignar `Field.groups` después del setup puede no surtir efecto y puede romper la validación de vistas nativas al actualizar point_of_sale. Riesgo asumido: sin `groups=`, la lectura por atributo en código Python no está bloqueada (no es alcanzable desde RPC salvo por métodos públicos no revisados). Para evaluar activarlo: ponerlo en True en una base de prueba, ejecutar `-u point_of_sale` y abrir el POS como cajero; si aparece un error de vista o AccessError al abrir, dejarlo en False.
6. **Costos y márgenes** (`total_cost`, `margin`, `margin_percent`, `standard_price`, instantánea y costo manual del guard): filtrados en `read`, dominios, agrupaciones y exportación de pos.order, pos.order.line, product.product y product.template.
7. **Precarga del POS (loadData / `_load_pos_data_*`)**: se recortan los campos sensibles de la lista de campos y se limpia la respuesta de `load_data`. La respuesta de `sync_from_ui` al cajero **falla cerrado**: solo pedidos cuyo uuid envió el propio cliente, con sus líneas y pagos; modelos desconocidos y cualquier otro pedido se descartan (si las filas de 18 no traen `uuid`, la venta legítima volvería vacía: TODO-VERIFICAR).
8. **Informe "Detalles de ventas"** (`get_sale_details`, `_get_report_values`): bloqueado para no gerentes. Era una vía directa a totales y pagos por medio.
9. **Cierre y escritura directa (C2)**:
   - `pos.session.write` y `create` para el cajero: fuera de los métodos propios solo se permiten `login_number` y `sequence_number`; `state`, `cash_register_balance_start/end_real`, `stop_at` y `user_id` se rechazan. Las transiciones de estado legítimas son abrir, pasar a cierre y volver; **el paso a `closed` exige un registro de conteo previo** (incluso dentro de los métodos propios con usuario no sudo).
   - `set_opening_control`, `update_closing_control_state_session` y `action_pos_session_open` corren con ventana interna y validación; el efectivo inicial se valida y se registra.
   - `action_pos_session_close` y `try_cash_in_out` están bloqueados para el cajero (decisión provisional: las entradas/salidas de efectivo las registra el gerente; confirmar con Efraín).
   - `action_pos_session_closing_control` y `action_pos_session_validate` rechazan al cajero fuera del flujo propio.
   - El cierre exige conteo previo, comprueba que la sesión sea del cajero, **ignora los argumentos que envíe el cliente** (p. ej. `bank_payment_method_diff_pairs`) y reemplaza cualquier mensaje de error de Odoo por uno genérico. `close_session_from_ui` corre en `savepoint`.
   - **Apertura vs. cierre anterior (M9):** al abrir se registra el efectivo declarado y se compara con el efectivo contado al cerrar la sesión anterior de la misma caja (`opening_discrepancy`, filtro "Apertura distinta del cierre anterior"). Retiros autorizados entre turnos también generarán discrepancia: es una alerta para el gerente, no una prueba.
   - **Diferencia final (A1, N2):** al contar se guarda `difference_at_count` y no vuelve a cambiar. Al cerrar se recalculan solo las ventas en efectivo (pos.payment), para reflejar ventas hechas entre el conteo y el cierre (`cash_sales_after_count`), y con ellas `expected_cash` y `difference`; `counted_cash` y la apertura no cambian. Las entradas/salidas de efectivo NO se releen al cerrar: Odoo registra el ajuste nativo de diferencia en `statement_line_ids` y sumarlo igualaría esperado y contado; se conservan los movimientos del conteo (el cajero no puede registrar movimientos; si el gerente registra uno entre conteo y cierre, no se refleja). Un cierre sin conteo ciego previo (p. ej. del gerente) se marca `calc_after_close` y su diferencia no es fiable.
   - **Apertura una sola vez (N1):** `set_opening_control` para el cajero solo se acepta con la sesión en `opening_control` y si no hay ya un registro de apertura; re-declarar el efectivo inicial después de vender se rechaza.
10. **Historial de tickets**: `search_paid_order_ids` devuelve lista vacía al cajero.

## Qué NO cubre

Ver también el informe de TODO-VERIFICAR al final.

- **Interfaz del diálogo de cierre.** No hay parche JavaScript. El diálogo estándar recibirá ceros y calculará en pantalla "diferencia = contado - 0", una cifra sin sentido (no filtra nada, pero confunde). Falta un parche OWL del diálogo de cierre que oculte esos campos; no se escribió porque los nombres de componentes de Odoo 18 no se pudieron verificar.
- **Caché del navegador / IndexedDB del POS.** Odoo 18 guarda datos precargados en el dispositivo. Datos cargados con una sesión de gerente en la misma tableta quedan en el navegador. Usar un perfil de navegador exclusivo del cajero, nunca abrir el POS del cajero con la cuenta del gerente y limpiar datos del sitio al cambiar de persona.
- **Costos en `standard_price`.** No se protege con `groups=` porque Odoo calcula el costo de la línea con el usuario de la sesión. Mitigación operativa: no cargar costos en `standard_price`; usar solo el costo manual protegido de `pos_order_integrity`. Rutas indirectas (onchange, campos relacionados en otros modelos, nombre/búsqueda de producto) no están cubiertas.
- **Integridad de escritura en otros modelos.** El control de escritura cubre pos.session; no se revisó la escritura directa por el cajero en pos.config, pos.payment.method ni en pedidos (eso corresponde a pos_order_integrity). Los campos que el flujo nativo escribe como cajero sin sudo en la sesión (lista `SAFE_DIRECT_WRITE`) son una hipótesis: si el POS falla al abrir con AccessError, ampliar la lista con evidencia.
- **Cantidad de ventas.** `sequence_number`, el nombre de los pedidos y el consecutivo de pedidos permiten inferir cuántas ventas hubo (no importes).
- **Efectivo inicial por defecto.** Odoo puede prellenar el efectivo inicial con el cierre anterior (`last_session_closing_cash` en pos.config). Con las reglas, el cajero no ve sesiones cerradas, así que verá cero; el efectivo inicial se declara manualmente.
- **Chatter y asientos contables.** Mensajes en la sesión abierta, `account.move` y `account.move.line` del cierre: no se tocan. No dar al cajero ningún grupo de contabilidad.
- **Pagos que no son efectivo.** El cierre ciego cuenta solo efectivo; Nequi, llave y transferencias se contabilizan como los registró Odoo, sin conteo ni diferencia.
- **Tiempo.** Un cajero que cobra una venta puede deducir el total de esa venta (es la venta actual, permitido por el alcance); no hay protección contra sumar ventas propias de memoria.
- **Pedidos existentes en sincronización.** Si `sync_from_ui` devolviera datos de un pedido existente referenciado por id, el filtro por uuid de la respuesta es la única defensa (TODO-VERIFICAR).
- **Terminal de pago, bus (longpolling) y notificaciones**: no analizados.
- **Dos cajeros en la misma caja:** con las reglas, el segundo no ve la sesión abierta del primero; Odoo impedirá abrir otra (una caja, una sesión abierta).
- **Después de cambiar los grupos de un usuario** reiniciar el servidor o limpiar la caché de reglas (el comportamiento de la caché de `ir.rule` no está verificado).

## Configuración necesaria

- En el punto de venta: **activar el control avanzado de efectivo** (`cash_control`). El módulo se niega con un mensaje claro a abrir/cerrar en modo ciego si está desactivado (TODO-VERIFICAR nombre del campo; sin él Odoo no pide conteo de apertura y cierre).
- En el punto de venta: **desactivar** "límite máximo de diferencia" (`set_maximum_difference`). Si está activo, el cierre se bloquea cuando la diferencia lo supera y el cajero podría deducir el esperado por tanteo; el módulo se niega a cerrar en ese caso.
- En el diario de efectivo: definir cuentas de pérdida y ganancia. Si faltan, el cierre con diferencia fallaría y solo ese fallo delataría que hay diferencia (el módulo muestra siempre el mismo mensaje genérico, pero el fallo en sí es una señal).
- Cajero: cuenta de Odoo propia, solo con el grupo POS usuario / cajero restringido. Efraín con `group_pos_store_manager`; no compartir cuentas.

## Cómo probar manualmente (base aislada, datos ficticios)

1. No editar `installable` en este repositorio ni montar `./addons` del compose principal (se monta con escritura). Copiar `addons/` a un directorio aparte para el entorno aislado, poner allí `installable: True` en este manifiesto y en `pos_order_integrity`, y montar solo esa copia; instalar y anotar cualquier error (los TODO-VERIFICAR de nombres de modelo fallarán aquí de forma ruidosa).
2. Crear usuarios `cajero` (POS usuario + cajero restringido) y `efrain` (gerente). Configurar el punto de venta como arriba.
3. Como cajero: abrir caja con 20.000, hacer una venta en efectivo de 10.000 y otra con Nequi; cerrar contando 29.000. Verificar que el diálogo y las respuestas de red (pestaña Red del navegador: `get_closing_control_data`, `post_closing_cash_details`, `close_session_from_ui`) no contienen 30.000, 10.000 ni la diferencia de 1.000.
4. Desde el navegador del cajero, enviar llamadas directas (consola o `curl` con su sesión) a `/web/dataset/call_kw/<modelo>/<método>`: `pos.order` `search_read`/`read_group`, `pos.payment` `search_read`, `pos.session` `read` con `cash_register_difference`, `pos.blind.cash.closing` `search_read`, `report.point_of_sale.report_saledetails` `get_sale_details`, `pos.order` `search_paid_order_ids`, `product.product` `read` con `standard_price`. Esperado: error de acceso, lista vacía o ausencia del campo.
5. Inspeccionar la precarga del POS (respuesta de carga de datos al abrir la sesión y IndexedDB): sin `standard_price`, `total_cost`, `margin` ni totales de sesión.
6. Como Efraín: Cierres de caja > Diferencias de caja muestra esperado, contado y diferencia (-1.000 en el ejemplo, sin la venta en borrador pendiente); comparar con el campo `odoo_mismatch`.
7. Ejecutar `odoo-bin -d <base_de_prueba> -i pos_blind_cash_closing --test-tags /pos_blind_cash_closing --stop-after-init`. Los fallos de `setUp` (campos obligatorios de Odoo 18) no prueban nada del módulo: ajustar el montaje primero.
8. Repetir el paso 3 con la tableta real y con un segundo navegador como gerente para comprobar que no queda caché cruzada.

## Archivos

- `models/blind_common.py`: identidad, ventana interna, filtros y validación (sin modelos).
- `models/pos_session.py`, `pos_order.py`, `pos_payment.py`, `product.py`, `report_sale_details.py`: sobreescrituras.
- `models/cash_closing.py`: registro inmutable de diferencias.
- `security/`: ACL del registro y reglas globales; `hooks.py`: regla de `report.pos.order`.
- `views/cash_closing_views.xml`: lista, formulario, pivote y menú para gerente/admin.
- `tests/test_blind_close.py`: pruebas TransactionCase (no ejecutadas) del cajero intentando leer totales.

## TODO-VERIFICAR (nombres y comportamientos de Odoo 18 no comprobados)

Prioridad alta (pueden impedir instalar o romper el POS):

1. Modelo abstracto `report.point_of_sale.report_saledetails` y métodos `get_sale_details` / `_get_report_values` (si el nombre difiere, `_inherit` falla al instalar).
2. Ids XML de modelos en las reglas: `point_of_sale.model_pos_session`, `model_pos_order`, `model_pos_order_line`, `model_pos_payment`, `account.model_account_bank_statement_line`; campo `pos_session_id` de `account.bank.statement.line`.
3. Que `user.has_group(...)` funcione dentro de `domain_force` y que la caché de `ir.rule` se invalide al cambiar grupos.
4. Que asignar `Field.groups` en `_setup_complete` tenga efecto en el control de acceso a campos; y que ninguna operación nativa ejecutada por el cajero sin `sudo` (p. ej. el cálculo de `pos.config.last_session_closing_cash`) lea esos campos y falle al abrir el POS.
5. Existencia y firma de `pos.order.sync_from_ui` (Odoo 18; `create_from_ui` es de 17 y no se cubre), `pos.order.search_paid_order_ids`, `pos.session.load_data`, `_load_pos_data_fields` en cada modelo y qué modelo carga el producto (`product.product` vs `product.template`).
6. Firma de `_search` y `_read_group` en esta versión exacta (se sobreescriben con `*args/**kwargs`) y que `domain` llegue como lista y no como objeto `Domain` (si no, el escaneo de dominios se omite).
7. Que `search_read`, `web_read` y `web_search_read` pasen por `read()` (el filtro de campos sensibles se apoya en eso).

Prioridad media:

8. Nombres de campos de `pos.session`: `cash_register_balance_start`, `cash_register_balance_end`, `cash_register_balance_end_real`, `cash_register_difference`, `cash_register_total_entry_encoding`, `total_payments_amount`, `order_count`, `statement_line_ids`, `payment_method_ids`, `currency_id`, `user_id`; y variantes `cash_real_*` (se ignoran si no existen).
9. `pos.payment.method.is_cash_count` y `type`; `pos.payment.session_id` y `pos_order_id`.
10. Fórmula del esperado: ¿los pagos en efectivo registrados ya descuentan el cambio devuelto? ¿las entradas/salidas de efectivo viven en `statement_line_ids`? Comparar con `odoo_expected_cash` (el nativo usa el cierre anterior, no el efectivo inicial declarado).
11. Claves que espera el diálogo estándar de cierre en `get_closing_control_data` y firmas de `post_closing_cash_details`, `close_session_from_ui`, `update_closing_control_state_session`, `action_pos_session_closing_control`, `action_pos_session_validate`.
12. `pos.config.set_maximum_difference` (nombre del campo).
13. `report.pos.order` (regla creada en `post_init_hook` solo si el modelo existe; se omite con aviso en el log).
14. Vistas de Odoo 18: `<list>`, `column_invisible`, `view_mode` `list`.
15. Pruebas: campos obligatorios al crear diario, medios de pago, `pos.config`, `pos.session`, `pos.order`, líneas y pagos; escritura directa de `state`.

Interacción con `pos_order_integrity` a revisar: el guard no debe depender de `env.su` para permitir las escrituras internas de costo que Odoo hace tras el pago (este módulo no usa `sudo()` en `sync_from_ui` justamente para no saltarse sus validaciones); en el cierre sí se usa `sudo()` y por tanto el guard no valida esa operación.

## Precondiciones del flujo (también del fixture de pruebas)

Control avanzado de efectivo activo (`cash_control`), sin límite máximo de diferencia, diario de efectivo con cuentas de pérdida y ganancia, y un medio de pago de efectivo en la caja. `tests/test_blind_close.py` fija todo eso en `setUpClass` (con comprobaciones `if campo in _fields`; los nombres son TODO-VERIFICAR).

## Nuevos TODO-VERIFICAR (segunda revisión)

16. `pos.session.write` y `create` bloqueados: qué campos escribe el flujo nativo de apertura/cierre/login como cajero sin sudo (`login_number`, `sequence_number`, otros); si algún método nativo no envuelto escribe `state`, el POS fallará con AccessError al abrir o cerrar.
17. Nombres y firmas de `set_opening_control(cashbox_value, notes)`, `update_closing_control_state_session(notes)`, `action_pos_session_open`, `action_pos_session_close`, `try_cash_in_out`.
18. `pos.payment.method.type == 'cash'` (se usa si existe; si no, `is_cash_count`) y clave `opening_notes` y demás claves del diálogo de cierre.
19. `pos.config.cash_control`.
20. Que las filas de `sync_from_ui` incluyan `uuid` (pos.order), `order_id` (líneas) y `pos_order_id` (pagos).
21. Escaneo de texto de dominios y `order=`: posibles falsos positivos si un valor de dominio legítimo del POS contiene el nombre de un campo sensible.
22. Efectos de las reglas globales en contadores y tableros de pos.config y en pantallas del backend de usuarios POS no gerentes.

## Vectores aún abiertos tras la segunda revisión

- Lectura por atributo sin `groups=` (decisión M7) y rutas de métodos públicos de pos.session / pos.config no revisados que devuelvan totales.
- El cajero puede ver la venta en curso y sus pagos parciales; sumar ventas propias de memoria no se puede impedir.
- Cobertura incompleta de escritura en otros modelos (ver arriba).
- Cierre del gerente sin conteo previo: diferencia no fiable (marcada, no corregida).
- Todo lo listado en "Qué NO cubre".

## TODO-VERIFICAR (tercera revisión)

23. Que el ajuste nativo de diferencia al cerrar entre en `statement_line_ids` (motivo de no releer movimientos al cierre). Cómo detectarlo: cerrar con faltante en una base de prueba y comparar `statement_line_ids` antes y después. Si no entra ahí, el diseño sigue siendo válido, solo más conservador.
24. Fixture: `account.account` con `account_type` `expense` / `income_other` y sin `company_ids` explícito; `loss_account_id` / `profit_account_id` en `account.journal`.
25. Que `set_opening_control` sea la única vía por la que el POS declara el efectivo inicial y que no se invoque dos veces en un flujo legítimo (reintentos de red del cliente se rechazarían con mensaje de error).
