# Panel técnico: propuesta y validación

## Objetivo

Manuel necesita administrar módulos y usuarios de la cafetería. Odoo ya dispone de los menús nativos Aplicaciones y Ajustes para estas tareas. Usarlos primero en lugar de construir un panel que duplique permisos o exponga operaciones sensibles.

## Diseño propuesto

- Cuenta técnica individual de Manuel con permisos de administración apropiados; definir y validar sus grupos en el entorno real.
- Cuenta individual de don Efraín con acceso de negocio restringido, sin permisos para instalar módulos ni gestionar la infraestructura.
- Cuenta individual para cada operador, sin acceso a Aplicaciones, Ajustes, usuarios o costos y reportes.
- Altas de módulos de forma manual y controlada: revisar compatibilidad, probar en una base aislada, verificar copia recuperable y luego efectuar la instalación autorizada.
- Documentar módulos instalados, versión, dependencia, responsable y fecha del cambio. Mantener actualizaciones y restauración como procedimientos separados.

## Pruebas requeridas

1. Con la cuenta técnica, verificar acceso a Aplicaciones y capacidad de consultar módulos instalados sin instalar nada.
2. Con las cuentas del gerente y cajero, comprobar que Aplicaciones y Ajustes no son accesibles, incluso por enlace directo o solicitudes RPC.
3. Confirmar que el gerente conserva únicamente sus operaciones comerciales aprobadas y no puede concederse permisos técnicos.
4. Probar instalación y reversión de un módulo de prueba en una base aislada y restaurar un respaldo antes de repetirlo en producción.
5. Revisar que los usuarios no compartan credenciales y no asignar privilegios técnicos por defecto.

## Decisiones pendientes

Ninguna de estas decisiones tiene respuesta registrada; no asumir valores hasta que Manuel o don Efraín las confirmen.

- Denominador del promedio diario de ventas (días de apertura frente a otro criterio): decide el negocio; afecta el informe que verá don Efraín.
- Relación entre bolsa y unidades del pan (una bolsa de pan de bolita trae 10 unidades según el alcance; falta confirmar la equivalencia para inventario y para los demás tipos de pan).
- Identificación exacta del medio de pago "llave": qué es, cómo se concilia y si requiere método de pago propio.
- Balanza: marca y modelo desconocidos; primera opción acordada, ingreso manual del peso. Integración con la balanza no decidida.
- Catálogo y precios reales: pendientes de entrega; no se inventan.
- Qué permisos exactos deben tener las cuentas de Manuel, Efraín y cajero: se definen tras revisar los grupos reales de Odoo en el entorno aislado (ver `docs/guion-pruebas-powershell.md`).

## Estado

Propuesta sin implementar ni validar: durante la revisión el proceso recibió permiso denegado al acceder al motor Docker. No se han modificado cuentas, grupos ni aplicaciones de Odoo. Si los menús nativos no satisfacen la operación después de probarlos, especificar la brecha antes de crear un módulo propio.
