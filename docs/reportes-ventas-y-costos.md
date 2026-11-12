# Reportes y costos: especificación de aceptación

Estado: pendiente de validación contra la edición y configuración instaladas de Odoo 18. No se ha verificado con datos reales ni se ha instalado un módulo de reportes.

## Datos de entrada

- Cada presentación vendible tiene nombre, unidad de venta, precio de venta y costo estimado manual. La bolsa de diez panes y el pan individual se registran por separado. Cada costo debe corresponder a la unidad del producto (bolsa, unidad o kilogramo).
- Registrar costo desconocido como pendiente, no confundirlo con costo cero. Antes de mostrar ganancias, validar que exista un modo fiable de distinguir ambos estados en la configuración elegida.
- Una venta contiene fecha/hora, productos, cantidades, importes y pagos. Una devolución conserva su vínculo con la venta original y se refleja con signo adecuado.
- No registrar compras, gastos, recetas ni existencias en la primera fase.

## Indicadores para Efraín

1. Ventas brutas, devoluciones y ventas netas, con el tratamiento de impuestos definido explícitamente. Agrupar por día, mes, producto y medio de pago.
2. Productos más vendidos por cantidad y por importe; estas clasificaciones son distintas. Para pesos mostrar unidad y precisión; no sumar unidades y kilogramos como si fueran equivalentes.
3. Promedio de ventas netas diario: ventas netas del periodo dividido entre días de apertura. El negocio debe confirmar cómo identificar los días de apertura y qué hacer si no hay ninguno. No asumir días calendario.
4. Costo estimado y margen bruto estimado por producto: ingreso neto de impuestos menos costo de unidades vendidas, con devoluciones y redondeo. No incluir ventas con costo pendiente en el margen calculado; mostrar cuántas y cuánto representan. Confirmar si los precios incluyen impuestos con el contador.
5. Diferencia de caja por sesión: efectivo contado menos efectivo esperado, considerando fondo inicial y movimientos autorizados. Separar Nequi, llave y transferencia del efectivo físico.
6. Filtros de fecha y zona horaria America/Bogota, con periodo de inicio inclusivo y fin inclusivo según día local. Mostrar estado de sincronización: ventas pendientes de subir pueden no estar reflejadas.

El costo aplicable debe quedar históricamente estable al cambiar el costo del catálogo, y una devolución debe usar el costo de la venta original cuando sea identificable. Los mecanismos nativos de Odoo deben verificarse antes de desarrollar uno adicional; especialmente ventas sin inventario, servicio, unidad por peso y sincronización diferida. No mostrar el margen como confiable hasta superar esas pruebas.

## Decisiones pendientes

Sin respuesta registrada a la fecha; no asumir ni inventar valores ni precios.

1. Denominador del promedio diario: confirmar con don Efraín cómo se identifica un día de apertura (por ejemplo, día con al menos una venta, o día con sesión de caja abierta) y qué mostrar cuando no hay días abiertos. La fila "Promedio" de las pruebas solo ilustra la aritmética con tres días ficticios.
2. Relación bolsa-unidades del pan: la bolsa del pan de bolita trae 10 unidades; falta confirmar la equivalencia para cada tipo de pan y si el inventario futuro descuenta unidades o bolsas. Hasta entonces, bolsa y unidad se registran como presentaciones separadas.
3. Identificación de "llave": definir qué medio de pago es, cómo se registra y cómo se concilia frente a Nequi y transferencias.
4. Balanza: marca y modelo desconocidos; usar ingreso manual del peso. Precisión y unidad de pesaje por producto sin definir.
5. Tratamiento de impuestos en precios y costos: confirmar con el contador si los precios incluyen impuestos.
6. Costos manuales por producto y catálogo con precios reales: pendientes de entrega.

## Acceso y privacidad

Solo gerente y administrador técnico pueden acceder a informes, costos, ganancias y detalles históricos. Comprobar permisos de servidor, exportación, reportes, accesos directos y RPC; ocultar botones no basta. El cajero necesita ver su venta actual y los datos necesarios para abrir/cerrar caja, sin panel de ventas acumuladas. Comprobar si el cierre estándar revela cifras que contradicen este requisito.

## Pruebas de aceptación con datos ficticios

| Prueba | Datos | Resultado esperado |
|---|---|---|
| Margen por unidad | 2 panes a $1.000, costo $600 cada uno, sin impuestos | Ventas $2.000, costo $1.200, margen $800. |
| Venta por peso | 0,250 kg a $20.000/kg, costo $12.000/kg, sin impuestos | Ventas $5.000, costo $3.000, margen $2.000. |
| Bolsa | Una bolsa de diez panes a $5.000, costo $3.000 | Ventas $5.000 y margen $2.000; no confundir costo por bolsa con costo por unidad. |
| Costo histórico | Vender con costo $600, luego cambiar el costo a $800 | La venta antigua conserva $600; la nueva usa $800. |
| Sin costo | Una venta de producto cuyo costo no se conoce | Ingreso incluido; margen identificado como incompleto, no calculado como si costo fuera cero. |
| Devolución | Devolver uno de los dos panes vendidos arriba | Neto: $1.000 de ventas, $600 de costo y $400 de margen, si la devolución pertenece al mismo periodo. |
| Promedio | Ventas netas $300.000 durante tres días abiertos | Promedio $100.000/día; período sin días abiertos no divide por cero. |
| Cierre | Fondo $100.000, efectivo recibido $250.000 y contado $340.000, sin otros movimientos | Esperado $350.000 y diferencia −$10.000; los pagos electrónicos no suman al efectivo. |
| Pago combinado | Venta $10.000: efectivo $4.000, Nequi $6.000 | La venta suma $10.000 una vez; cada medio refleja su parte sin duplicar ingresos. |
| Permisos | El cajero intenta abrir informes, exportar o consultar el endpoint directamente | El servidor deniega el acceso. El gerente sí accede. |
| Zona horaria | Ventas alrededor de medianoche en Bogotá | Cada venta aparece en su fecha local correcta. |

## Dependencias y decisión técnica

Usar primero los informes nativos de Punto de venta > Informes > Órdenes para gráficos y tablas dinámicas. Verificar contra Odoo 18 instalado las métricas de costo y las dimensiones de reporte, así como las diferencias entre montos con y sin impuestos. Si faltan los requisitos históricos o de protección, diseñar una extensión pequeña y probarla antes de instalarla en producción. No modificar tablas SQL directamente ni implementar reportes a partir del costo actual del producto como sustituto del costo histórico.
