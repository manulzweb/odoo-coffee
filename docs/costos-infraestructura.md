# Presupuesto preliminar: POS de cafetería

Fecha de consulta: 11 de noviembre de 2026. Valores de referencia, no una cotización definitiva. Sin despliegues ni compras realizadas.

## Supuestos

Un local, una caja, acceso ocasional del gerente, Odoo Community 18 y PostgreSQL en la misma VM, operación continua, una base de datos, dominio existente o pendiente de cotización, y respaldo externo. La carga, número de ventas y requisitos de disponibilidad aún no están medidos. No se ha verificado el consumo real ni la capacidad libre de la cuenta de Oracle. Para ilustrar en pesos se usa **COP 4.000/USD**, cifra supuesta, no TRM ni tasa real; revisar tasa y recargos del medio de pago antes de contratar. Las cifras excluyen impuestos, dominio, soporte comercial de proveedor y excedentes de datos. Community y componentes adicionales deben verificarse por licencia; no se asume que Enterprise sea gratuito.

## Comparación

| Opción | Servidor | Respaldo / costo conocido | Costo base calculado | Observaciones |
|---|---|---|---|---|
| Oracle OCI, capacidad Always Free disponible | $0 incremental **si** se cumplen los límites aplicables de cuenta, región, RAM, CPU y almacenamiento | Depende del mecanismo y espacio realmente disponible | Desde $0 de recursos elegibles, no costo total garantizado | Los recursos se comparten con las otras VMs de Manuel; un servicio pagado o exceso puede facturarse. |
| AWS Lightsail Linux IPv4, 2 GB | USD 12/mes; 2 vCPU, 60 GB SSD, transferencia incluida sujeta a región | Ejemplo: 20 GB-mes facturables de snapshots × USD 0,05 = USD 1/mes | USD 13/mes ≈ COP 52.000 con tasa supuesta | Candidato económico para pruebas, no garantía de que 2 GB basten para Odoo, PostgreSQL y proxy. |
| AWS Lightsail Linux IPv4, 4 GB | USD 24/mes; 2 vCPU, 80 GB SSD | Mismo ejemplo de 20 GB-mes: USD 1 | USD 25/mes ≈ COP 100.000 con tasa supuesta | Más margen de memoria; validar con mediciones. |

Los 20 GB-mes de snapshots son un supuesto para ilustrar cálculo, no el tamaño esperado: AWS factura el almacenamiento de instantáneas efectivamente retenido. Las copias automáticas conservan hasta siete instantáneas; medir el consumo real. Agregar una copia independiente y probar restauración de la base y filestore antes de operar. El precio aquí no incluye el almacenamiento fuera de Lightsail.

## Oracle: puntos de control

La documentación vigente consultada indica 1.500 horas de OCPU y 9.000 GB-hora al mes para A1, equivalentes a 2 OCPU y 12 GB continuos para cuentas Always Free, y 200 GB combinados de volúmenes de arranque y bloque elegibles. Son límites compartidos de la cuenta, no por proyecto. Se indica también hasta cinco respaldos de volumen elegibles; confirmar región, uso existente, estado de cuenta y facturación real. Hay discrepancias entre páginas comerciales de Oracle y la documentación operativa sobre el cupo A1: confirmar el límite efectivo de la tenencia en consola antes de proyectar costo cero. Oracle puede recuperar instancias Always Free consideradas inactivas, y puede no haber capacidad disponible. Un VPS compartido es un punto único de falla y no garantiza continuidad; respaldos externos y procedimiento de recuperación son indispensables.

Si se usa capacidad pagada, una tarifa publicada para A1 es USD 0,01/OCPU-hora y USD 0,0015/GB-hora. Una VM ilustrativa de 1 OCPU y 4 GB por 730 horas costaría **USD 11,68/mes** en cómputo y memoria antes de cualquier franquicia elegible: (1 × 0,01 + 4 × 0,0015) × 730. Almacenamiento, respaldo e impuestos son adicionales. Comprobar tarifa, región y franquicias en el estimador y consola.

## Propuesta de precio al cliente

Propuesta orientativa, no tarifa de mercado verificada ni acuerdo cerrado. Separar implementación inicial de servicio mensual; el primero cubre levantamiento, configuración, pruebas y capacitación, y se cotiza según horas reales. El mantenimiento no debería depender de un porcentaje de las ventas de la cafetería sin conocerlas ni negociar expresamente.

- **Si OCI está efectivamente cubierto por cuota existente:** COP 60.000/mes de ejemplo: reserva de infraestructura y respaldos 10.000 + soporte previsto 40.000 (1 hora a 40.000) + margen 10.000. Los 10.000 son una provisión interna, no factura demostrada. Margen antes de imprevistos y tributos.
- **Si se contrata Lightsail 2 GB:** COP 105.000/mes de ejemplo: base calculada 52.000 + soporte previsto 40.000 + margen 13.000. Falta sumar copia externa, dominio, impuestos y excedentes; por ello no debe presentarse como precio cerrado.
- **Si se necesita Lightsail 4 GB:** la base ilustrativa ya es COP 100.000; sumar soporte, margen y conceptos pendientes, por lo que COP 105.000 no sería sostenible.

Definir en la oferta qué incluye el soporte, horario, tiempo de atención, respaldo, restauración, actualizaciones, propiedad de datos y exportación; desarrollos, migraciones y atención extraordinaria se cotizan aparte. Solicitar aprobación del presupuesto al dueño antes de comprometer gasto. Establecer alertas y presupuesto en nube; las alertas no son un límite de gasto garantizado.

## Capacidad y un worker

Un worker de Odoo puede ser una hipótesis inicial, no una garantía: Odoo, PostgreSQL, proxy y procesos auxiliares comparten memoria y CPU. Verificar configuración de workers y procesos asociados en Odoo 18, carga simultánea, cron, sincronización y consumo de RAM. Medir latencia al cobrar y abrir POS, memoria máxima, intercambio a disco, CPU y tasa de errores bajo escenario de caja + gerente + respaldo. Elegir tamaño tras la prueba; 2 GB puede ser insuficiente.

## Fuentes oficiales consultadas

- [AWS: paquetes Lightsail](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html).
- [AWS: costos de snapshots](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-faq-snapshots.html).
- [Oracle: recursos Always Free y recuperación de instancias inactivas](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).
- [Oracle: precios A1](https://www.oracle.com/cloud/compute/arm/).
