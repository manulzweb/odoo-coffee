# Cafetería: especificación inicial del punto de venta

Estado: borrador para implementación y validación. Fecha: 2026-11-11.

## Objetivo y alcance

Sustituir los vales por ventas registradas en Odoo 18 para un local y una caja. Venta en mostrador desde portátil o tableta. Sin mesas, impresora, inventario, compras, gastos ni recetas en la primera versión. El catálogo y precios están pendientes de entrega.

## Funciones y criterios de aceptación

- POS-01: abrir sesión registrando el efectivo inicial; registrar y cerrar la sesión con el efectivo contado. Mostrar y conservar las diferencias para el gerente. Acordar y probar qué datos de cierre puede visualizar el cajero.
- POS-02: seleccionar productos y cantidades, mostrar total de la venta y registrar pago en efectivo, Nequi, llave o transferencia. Considerar pagos combinados; verificar su comportamiento en Odoo.
- POS-03: venta por peso con cantidad positiva y precio por kilogramo. Ejemplo: 0,250 kg a $20.000/kg equivalen a $5.000. Definir precisión y redondeo.
- POS-04: pan individual y bolsa como presentaciones de venta; bolsa de pan de bolita contiene 10 unidades. Relación de existencias por confirmar; inventario fuera del alcance inicial.
- POS-05: registrar costo manual y mostrar margen bruto estimado para el gerente. Verificar la conservación del costo histórico y definir manejo de productos sin costo. No presentar el resultado como utilidad neta.
- POS-06: reportes para gerente de ventas por día y mes, ventas por producto y medio de pago, promedio diario y diferencias de caja. Definir denominador del promedio diario. Validar disponibilidad según edición y configuración.
- POS-07: gerente puede corregir o devolver ventas; motivo opcional, conservar autor, fecha y trazabilidad. Operador no puede ejecutar estas acciones ni borrar ventas confirmadas.
- POS-08: operador ve la venta actual y los datos necesarios para apertura y cierre; no debe acceder a historial, reportes, costos, ganancia ni totales de ventas del período. Comprobar también datos mostrados durante el cierre.
- POS-09: operador no cambia precios ni aplica descuentos. Una cuenta técnica gestiona plataforma y módulos; el gerente tiene permisos de negocio limitados.
- POS-10: probar funcionamiento temporal sin conexión y sincronización sin duplicados en el dispositivo real. Si no supera las pruebas, usar vales de contingencia y registrar cada venta una sola vez al recuperar el servicio.

## Seguridad y preparación

La interfaz no constituye una barrera de autorización suficiente. Validar permisos y operaciones en servidor, incluidos RPC y acceso a datos, para la versión y configuración reales. No suponer que los roles de empleado del POS equivalen por sí solos a identidades autenticadas en el servidor. Determinar una estrategia que preserve la operación sin conexión y no permita eludir restricciones.

Usar credenciales individuales, HTTPS, acceso limitado, respaldos de base de datos y filestore fuera del servidor, y prueba de restauración. Mantener la información financiera disponible solo para personal autorizado. Cualquier obligación fiscal debe verificarse con el contador.

## Pruebas mínimas antes de operar

1. Venta por unidad, bolsa, peso y por cada medio de pago; comprobar cálculo y registro.
2. Apertura y cierre con efectivo inicial, entradas autorizadas y diferencia positiva y negativa.
3. Cajero: intentar descuento, cambio de precio, devolución, eliminación, historial y reportes, tanto en interfaz como mediante solicitudes directas; verificar que se rechacen.
4. Gerente: consultar reportes y devolver una venta con y sin motivo; comprobar trazabilidad y cálculo de reportes.
5. Costos: cambiar costo después de una venta y comprobar el resultado histórico; probar producto sin costo.
6. Abrir sesión, perder conexión, registrar una venta, reconectar y comprobar sincronización única; probar contingencia en papel.
7. Ensayar en portátil y tableta y restaurar respaldo en un entorno aislado.

## Decisiones pendientes

Catálogo y costos; identidad de las personas; modelo de balanza; precisión y redondeo; tratamiento de pagos por llave; regla del promedio diario; comportamiento de inventario para bolsas; definición y conservación del costo histórico; alcance exacto de datos visibles al cierre; infraestructura y costos. Validar obligaciones de comprobantes y tributación con contador.
