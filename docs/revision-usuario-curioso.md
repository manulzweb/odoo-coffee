# Revisión exploratoria: usuario curioso

Revisión estática de los archivos existentes; no se ejecutó la aplicación ni se realizaron pruebas de usuario, navegador, accesibilidad o seguridad en tiempo real. Hallazgos sujetos a validación en Odoo.

## Hallazgos que bloquean producción

1. El módulo previo `pos_role_policy` restringe acciones principalmente mediante JavaScript. Un usuario puede intentar solicitudes directas y rutas alternativas; ocultar controles no demuestra autorización en servidor. Sus roles de empleado tampoco deben confundirse con usuarios Odoo independientes.
2. El prototipo `pos_order_integrity` declara en su README que no valida precios, impuestos, pagos ni reportes y que no ha sido probado. Es posible que no cubra todas las rutas RPC y su intervención en órdenes confirmadas puede afectar sincronización y cierre. No considerarlo seguridad completa ni instalarlo en producción sin pruebas.
3. El script `scripts/configure_laguapa_pos.py` corresponde a otro restaurante: selecciona el primer POS encontrado, modifica configuraciones generales, reemplaza métodos de pago, cambia menús raíz, activa mesas y QR e imprime PIN. No ejecutarlo para la cafetería ni sobre bases compartidas.
4. La visibilidad de totales y datos al abrir y cerrar caja, buscar pedidos, acceder mediante URL directa o RPC y cambiar de empleado no ha sido verificada. El cajero debe ver solo la venta actual y el efectivo necesario para abrir y cerrar.
5. El respaldo `scripts/backup.sh` guarda archivos localmente y su propio comentario exige copiarlos fuera; el script de restauración reemplaza bases y filestore, por lo que debe probarse solo en entorno aislado. No se ha comprobado copia externa ni restauración.

## Casos de prueba pendientes

- Navegar todas las pestañas y menús como cajero, volver atrás, abrir URL directas, inspeccionar respuestas RPC e intentar consultas al historial, productos con costos y reportes.
- Intentar descuentos, precios alterados, cantidades negativas, devoluciones, cancelaciones, cambios tras confirmar y pagos alterados mediante interfaz y solicitudes directas. Verificar rechazo del servidor y no solo ocultación visual.
- Cambiar de empleado o usuario, probar sesión expirada, enlaces y permisos con cuentas independientes y comprobar que ninguna sesión compartida eleve privilegios.
- Venta por peso cero, negativo, decimales largos, precio y cantidad grandes, venta repetida al pulsar dos veces; corroborar redondeo y no duplicación.
- Interrumpir conexión antes y después de confirmar, recargar o cerrar dispositivo y reconectar; validar integridad, conciliación y vales de contingencia.
- Probar pago combinado y cambio, medios equivocados, cierre con diferencias y visualización de totales, en portátil y tableta real.
- Probar reportes vacíos, producto sin costo y cambio de costo posterior a la venta; validar margen histórico sin confundirlo con utilidad neta.

## Conclusión

Estos casos son un plan de pruebas, no resultados. No hay evidencia de que el sistema pueda vender de forma segura ni ser usado por el cliente hasta ejecutar y superar las pruebas de extremo a extremo en un entorno aislado y después verificar la preparación de producción.
