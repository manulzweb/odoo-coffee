# Continuidad: POS para cafetería

Actualización: 11 de noviembre de 2026. Documento de traspaso; contrastar con el estado actual del código y los servicios antes de actuar.

## Objetivo

Manuel desarrolla e implementa para don Efraín un POS de cafetería con Odoo. Su prioridad es sustituir los vales de venta por registros consultables, fáciles de consolidar por día y mes. Se quiere desplegar pronto, pero solo después de probar seguridad, cierre de caja, recuperación y operación real.

## Alcance acordado

- Un local, una caja y atención en mostrador; existen mesas, pero no requieren gestión.
- Productos como café, bebidas, panes y productos por peso; catálogo y precios reales fueron solicitados y siguen pendientes de entrega.
- Venta por unidad, bolsa y peso. Una bolsa del pan de bolita trae 10 unidades; existen varios tipos de pan. La relación entre bolsa y unidades para inventario queda pendiente de confirmar.
- Peso medido en una balanza existente, cuya marca y modelo se desconocen; introducir manualmente el peso como primera opción. Ejemplo: 0,250 kg a COP 20.000/kg = COP 5.000.
- Efectivo, Nequi, llave y transferencias; pago mixto deseable si se valida. Identificación exacta de llave pendiente.
- Un cajero abre caja ingresando efectivo inicial, registra ventas y cierra ingresando efectivo contado. El cajero puede ver la venta actual y lo necesario para apertura y cierre, pero no totales históricos, ventas del turno, costos, márgenes ni reportes.
- Cajero no cambia precios ni aplica descuentos, ni accede a historial, correcciones o devoluciones. Las ventas confirmadas no se eliminan. Don Efraín puede corregir y devolver; motivo opcional, con registro de autor y fecha.
- Don Efraín consulta ventas diarias y mensuales, promedio diario, productos más vendidos y diferencias de caja. Definir el denominador del promedio diario.
- Registrar costo manual por producto y mostrar margen bruto estimado; sin receta ni costos detallados de ingredientes. Un costo desconocido no equivale a cero. Validar tratamiento histórico, impuestos, cambios de costo y devoluciones antes de afirmar exactitud.
- Acceso en portátil y tableta; don Efraín podría consultar desde celular, cuyo rendimiento debe probarse. No hay impresora, lector ni cajón confirmados; no se requiere impresión.
- Internet estable, pero se desea funcionamiento temporal sin conexión o, si no se demuestra seguro, continuidad mediante vales y registro posterior sin duplicados.
- Inventario, compras, proveedores, gastos, alertas y recetas son fase posterior. Este proyecto es para una sola cafetería.
- La información financiera debe ser privada y accesible solo a usuarios autorizados. No se solicita integración con DIAN; eso no determina las obligaciones fiscales de la cafetería, que deben revisarse con su contador.

## Roles

1. Manuel: administrador técnico de Odoo, infraestructura, módulos, usuarios y respaldo; desea su propio panel para agregar funcionalidades. Empezar evaluando menús y permisos nativos.
2. Efraín: gerente con acceso comercial y reportes; puede gestionar correcciones y devoluciones, sin administración técnica plena.
3. Cajero: venta y apertura/cierre de caja con las restricciones anteriores. Son necesarias identidades autenticadas separadas; un rol de empleado seleccionado por PIN no prueba por sí mismo autorización segura del servidor.

## Estado del proyecto

- Existe Docker Compose con Odoo 18, PostgreSQL 16 y Caddy; revisar configuración real sin imprimir secretos de `.env` o credenciales.
- El repositorio contiene cambios previos sin confirmar y módulos de otro negocio, incluido `pos_role_policy` y scripts de La Guapa. No revertir ni sobrescribir trabajo ajeno.
- **No ejecutar `scripts/configure_laguapa_pos.py` para la cafetería**: selecciona el primer POS y cambia configuraciones globales y de otro negocio; puede modificar sesiones, métodos de pago y menús.
- `addons/pos_order_integrity` (rediseñado, versión 18.0.2.0.0) y `addons/pos_blind_cash_closing` (cierre de caja ciego del lado servidor, depende del anterior) existen como código escrito por análisis estático, con pruebas en sus carpetas `tests/`. Ambos mantienen `installable: False` en el repositorio y nada de ellos se ha instalado ni ejecutado en Odoo 18; sus README declaran TODO-VERIFICAR abiertos. La validación de pagos (`pos.payment` fabricados) y el control de escritura directa sobre `pos.session` son brechas conocidas en corrección. No activarlos cambiando el manifest del repositorio, porque `addons/` lo monta en lectura y escritura el proyecto principal; probarlos en una copia fuera del repo (ver `docs/guion-pruebas-powershell.md`).
- El cierre estándar de Odoo puede mostrar totales y montos de medios de pago al cajero. Ocultar interfaz no garantiza confidencialidad. `pos_blind_cash_closing` intenta el cierre ciego en servidor (reglas de registro, filtrado de campos sensibles, registro inmutable `pos.blind.cash.closing`), pero no está probado y no incluye parche de interfaz del diálogo de cierre.
- No se han realizado pruebas funcionales de Odoo, instalación del módulo ni pruebas reales por perfiles. Las revisiones de cajero adversarial, Efraín y usuario curioso fueron estáticas.

## Docker y bloqueo actual

Comprobación adicional del 12 de noviembre de 2026 (UTC): `docker compose ps` sigue fallando desde esta sesión con acceso denegado a `//./pipe/docker_engine` y a la configuración Docker del usuario. `docker compose -p cafeteria-dev -f dev/cafeteria/compose.yml config --quiet` valida la sintaxis sin conectarse al motor, aunque muestra la advertencia de configuración. No confirma que existan las imágenes, que el puerto esté libre ni que el aislamiento funcione. Las cuatro pruebas del validador de catálogo volvieron a pasar. No se iniciaron servicios ni se ejecutaron pruebas de Odoo.

La virtualización se activó en BIOS. El usuario ejecutó `docker info` en PowerShell: el motor funciona con WSL 2, Docker Desktop 29.9.2 y muestra cero contenedores e imágenes. `docker compose ps` en el proyecto mostró lista vacía. No interpretar esto como evidencia de que no existen volúmenes o datos anteriores; inspeccionar antes de cualquier acción destructiva.

La sesión de Codex de esta conversación seguía obteniendo `permission denied` al acceder a `//./pipe/docker_engine`, y advertencia de acceso denegado a la configuración Docker del usuario. El usuario sí tiene acceso desde su PowerShell; el problema observado es el permiso de la sesión aislada. Al iniciar una nueva sesión comprobar primero `docker compose ps`. No intentar eludir restricciones mediante otra interfaz; si persiste, explicar el bloqueo y opciones permitidas.

No se ha iniciado ni desplegado Odoo en esta sesión. No iniciar configuraciones de producción ni tocar datos existentes sin identificar servicios y destino; aislar desarrollo y verificar restauración de respaldos.

## Trabajo preparado y pruebas

- `docs/cafeteria-especificacion-inicial.md`: alcance, criterios y pruebas.
- `docs/guia-configuracion-pos-cafeteria.md`: guía de configuración pendiente de validación.
- `docs/reportes-ventas-y-costos.md`: especificación de reportes y casos.
- `docs/panel-tecnico-plan.md`: propuesta del panel de Manuel.
- `docs/revision-cajero-adversarial.md` y `docs/revision-usuario-curioso.md`: revisiones estáticas, no pruebas ejecutadas.
- `docs/consideraciones-uso.md`: notas de privacidad y uso; no sustituye asesoría legal.
- `docs/costos-infraestructura.md`: estimación preliminar OCI/AWS, supuestos y precios ilustrativos, no presupuesto aprobado. Volver a verificar precios y capacidad real.
- `docs/catalogo-cafeteria-plantilla.csv` y `docs/catalogo-cafeteria-instrucciones.md`: recopilación del catálogo, no importación directa a Odoo.
- `scripts/validar-catalogo-cafeteria.cjs` y su archivo `.test.cjs`: validador de catálogo. Cuatro pruebas pasaron con `node --test scripts/validar-catalogo-cafeteria.test.cjs` en la sesión anterior.
- El prototipo incluye pruebas para Odoo que **no se han ejecutado**.

## Solicitud de trabajo y delegación

Manuel autorizó delegar agentes por módulo y pidió terminar implementación, probar y revisar, con perspectivas de cajero que intenta vulnerar controles, Efraín con poca experiencia y celular lento, y usuario curioso que explora rutas y variantes. También pidió apoyo sobre panel técnico, consideraciones de uso y costos con beneficio moderado. Distinguir análisis estático de pruebas reales y corregir hallazgos; no prometer cobertura total.

## Próximos pasos

1. Verificar acceso real a Docker y revisar estado del repositorio, imágenes, contenedores y volúmenes sin exponer secretos ni afectar datos existentes.
2. Preparar una base y entorno aislados; identificar edición y módulos exactos instalados. Obtener catálogo y decisiones pendientes sin inventar precios.
3. Probar funciones nativas antes de crear módulos. Corregir y probar seguridad de servidor, roles, cierre ciego y conservación del costo histórico. Mantener prototipos incompletos desactivados.
4. Verificar ventas, pesos, bolsa, pagos, apertura/cierre, devoluciones, reportes, RPC, límites por rol, desconexión y reconexión. Probar los tres perfiles solicitados con datos ficticios y dispositivos disponibles.
5. Estimar y medir recursos; comparar infraestructura, respaldos y cuota de soporte con las fuentes actuales y el uso real de OCI. No contratar recursos ni prometer costo cero sin comprobar.
6. Ensayar respaldo y restauración aislada, seguridad y capacitación. Informar resultados, riesgos y bloqueos reales antes de recomendar producción.

## Docker: acceso y arranque verificados (2026-11-12 UTC)

El acceso denegado a `docker_engine` y a `.docker/config.json` correspondía al sandbox de la sesión. Los comandos ejecutados con autorización fuera del sandbox acceden correctamente al motor; no se modificaron permisos de Windows ni la configuración de Docker.

Se descargaron las imágenes y se inició `cafeteria-dev` con `dev/cafeteria/compose.yml`. PostgreSQL está healthy y Odoo responde HTTP 200 en `http://127.0.0.1:18069/web/database/selector`. Esto verifica el arranque, no las funciones del POS ni los módulos personalizados. No se creó una base funcional de cafetería.

Durante el diagnóstico también se inició el proyecto principal, inicialmente sin contenedores ni volúmenes. Se dejó detenido con `docker compose stop`; sus recursos creados se conservaron. El único entorno dejado en ejecución es `cafeteria-dev`. Para futuros comandos desde esta sesión, solicitar ejecución autorizada fuera del sandbox si reaparece acceso denegado; cambiar Compose no corrige esa restricción.

## Trabajo en la nube (12 nov 2026)

En esta sesión en la nube se avanzó solo de forma estática: se leyeron y redactaron documentos y se revisaron archivos del repositorio. No se ejecutó Odoo, ni Docker, ni ninguna prueba, y no se modificó código ni configuración de servicios. Nada de lo escrito aquí está verificado en ejecución.

- Hubo además revisión estática de los módulos, con hallazgos críticos: pagos fabricados (pedido pagado sin pagos o pago negativo) y escritura directa en la sesión del POS (saldo inicial, estado). Están en corrección. Nada se ejecutó: ni instalación, ni pruebas, ni Odoo; no hay evidencia de que las correcciones funcionen.
- Se creó y actualizó `docs/guion-pruebas-powershell.md`: guion para que Manuel lo ejecute en PowerShell sobre `cafeteria-dev`, que prueba los módulos en una copia fuera del repo con un override de Compose, incluye configuración de caja (control de efectivo, cuentas de pérdida y ganancia), pruebas automáticas y casos de los tres perfiles, con salida esperada y qué pegar de vuelta. Las salidas esperadas son suposiciones por lectura de `dev/cafeteria/compose.yml`, no resultados observados.
- Se añadió la sección de decisiones pendientes a `docs/panel-tecnico-plan.md` y `docs/reportes-ventas-y-costos.md`: denominador del promedio diario, relación bolsa-unidades del pan, identificación de "llave", balanza, catálogo y precios reales. Siguen sin respuesta.
- Hechos comprobados por lectura: ambos módulos tienen `installable: False`; `pos_blind_cash_closing` existe en `addons/`, con `tests/test_blind_close.py`.

## Renombrado de modulos y catalogo (12 nov 2026, tarde)

- `cafeteria_pos_guard` pasa a `pos_order_integrity`; `cafeteria_cierre_ciego` pasa a `pos_blind_cash_closing`. Modelos: `pos.order.audit.log` y `pos.blind.cash.closing`. Grupo de gerente: `pos_order_integrity.group_pos_store_manager` ("Punto de venta: gerente de tienda"). Campos y metodos con prefijo `cafeteria_` pasan a `pos_` (por ejemplo `pos_manual_cost`, `pos_sale_mode`). Bases de prueba del guion: `pos_test_integrity` y `pos_test_blind_closing`.
- El renombrado fue mecanico y solo se comprobo sintaxis (Python y XML) y existencia de los archivos de los manifests. Nada se ha ejecutado en Odoo.
- Catalogo real recibido (planilla manuscrita): 15 productos en `docs/catalogo-cafeteria.csv` y `docs/import/product.template.csv`; pendientes en `docs/import/README.md`.
