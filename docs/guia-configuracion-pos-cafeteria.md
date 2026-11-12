# Guía de configuración y pruebas del POS

Estado: guía preparada para Odoo 18; **no ejecutada ni validada en esta instalación**. No usar datos reales hasta completar las pruebas de seguridad y restauración.

## Preparación

1. Trabajar en una base de pruebas separada. Confirmar versión exacta y edición de Odoo, compañía y módulos instalados. Registrar respaldo y comprobar restauración antes de modificar datos existentes.
2. Instalar o comprobar Punto de venta. No activar funciones de mesas, impresión automática, terminal bancaria ni integración electrónica de báscula si no están requeridas.
3. Usar una sola configuración de punto de venta, en pesos colombianos y con zona horaria America/Bogota. Revisar impuestos y precios con el contador y don Efraín; no inferirlos ni fijarlos sin confirmación.
4. Crear accesos individuales para operador y gerente, siguiendo la política de permisos verificada en servidor. El rol técnico es de Manuel. No usar identidades genéricas compartidas para aprobar devoluciones.

## Catálogo

Crear productos disponibles en POS cuando llegue el catálogo, registrando nombre, categoría, precio de venta y costo manual. Mantener separados el pan individual y la bolsa como presentaciones. La bolsa de pan de bolita contiene 10 panes; quedan pendientes otras variedades y la relación de existencias. Inventario no se gestiona en esta fase.

Para venta por peso, habilitar unidades de medida y configurar el producto en kg, con precio y costo por kg. Sin balanza conectada, probar en una sesión si puede introducirse la cantidad decimal manualmente desde el teclado del POS; no marcar como pesaje con báscula integrada hasta comprobar esa integración. Ejemplo: 0,250 kg × $20.000/kg = $5.000. La precisión y redondeo deben acordarse y probarse. La opción oficial «Pesar con báscula» corresponde al uso de una báscula conectada, no confirma por sí sola la entrada manual.

## Medios de pago

En Punto de venta → Configuración → Métodos de pago, configurar efectivo, Nequi, llave y transferencia con diarios apropiados para la contabilidad existente. Asociarlos al punto de venta y validar con el responsable contable; no duplicar ingresos al representar movimientos entre cuentas. El registro de una transferencia o Nequi en POS no comprueba que el dinero haya llegado: el operador debe verificarlo por el procedimiento acordado. Verificar pagos combinados y cambio en efectivo mediante ventas de prueba.

## Caja y privacidad

Abrir una sesión con el efectivo inicial, registrar ventas y cerrar contando el efectivo físico. El cierre estándar de Odoo 18 muestra número de pedidos, total vendido e importes esperados por medio de pago. **Esto contradice la petición de ocultar totales al cajero**: no desplegar hasta implementar y verificar un cierre ciego y la protección de esos datos también en servidor. No confundir ocultar una columna con impedir acceso mediante red o llamadas directas.

## Casos de prueba con datos ficticios

| Caso | Pasos | Resultado esperado |
| --- | --- | --- |
| Por unidad | Café $3.000 × 2 | Total $6.000. |
| Bolsa | Bolsa $5.000 × 1 | Total $5.000, presentación identificada. |
| Peso | Queso $20.000/kg × 0,250 kg | Total $5.000; peso almacenado como 0,250 kg. |
| Cantidad inválida | Introducir 0 y cantidad negativa en venta normal | No se confirma venta indebida; devolución solo mediante flujo autorizado. |
| Pagos | Registrar una venta por medio y una combinada | Suma correcta; cada medio queda identificado; pago digital se verifica fuera de Odoo. |
| Cierre | Fondo $100.000, ventas en efectivo $50.000, contado $145.000 | El gerente ve diferencia de −$5.000; cajero solo ve datos autorizados. |
| Privacidad | Cajero abre cierre y trata de consultar historial/reportes y datos por RPC | No obtiene totales globales, costos ni reportes; resultado medido tras personalización. |
| Sin internet | Sesión abierta, cortar red, vender, reconectar | Una sola venta sincronizada; repetir tras recarga y revisar duplicados. Si falla, usar vales y conciliación. |
| Dispositivos | Repetir flujo en portátil y tableta real | Botones legibles, cantidades y cierre utilizables; anotar navegador y tamaño. |

Los resultados anteriores son criterios, no evidencias de prueba. Documentar fecha, versión, dispositivo, usuario, resultado y correcciones antes de producción.

## Referencias oficiales

- [Punto de venta Odoo 18](https://www.odoo.com/documentation/18.0/es/applications/sales/point_of_sale.html): ventas, apertura y cierre.
- [Métodos de pago Odoo 18](https://www.odoo.com/documentation/18.0/applications/sales/point_of_sale/payment_methods.html).
- [Hardware y básculas Odoo 18](https://www.odoo.com/documentation/18.0/es/applications/sales/point_of_sale/pos_hardware.html).
