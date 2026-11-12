# Revisión del POS desde el perfil de cajero adversarial

Estado: revisión estática, sin pruebas funcionales ni explotación ejecutadas. Docker rechazó el acceso al proceso de trabajo. Los riesgos se refieren al código disponible, no prueban que una instancia concreta esté comprometida.

## Hallazgos y prioridad

1. **Crítico — controles solo en navegador.** `addons/pos_role_policy/static/src/pos_roles.js` contiene lógica para bloquear acciones. Un usuario que controle su navegador puede intentar modificar ese JavaScript o enviar solicitudes directamente. La protección debe existir también en servidor para los permisos y datos sensibles, y validarse con credenciales de cajero.
2. **Crítico — identidad de empleado diferente de identidad autenticada.** `hr_employee.py` asigna `_role` al empleado para el frontend; esa representación no demuestra que el servidor autentique al gerente que aprueba una devolución. Evitar autorizaciones basadas en un rol o identificador de empleado enviado por el cliente. Verificar separación real de cuentas, accesos y aprobación.
3. **Alto — exposición de cierre.** La documentación de Odoo 18 indica que el diálogo estándar muestra total de la sesión y cantidades por medio de pago; incumple la confidencialidad solicitada. Ocultar campos no evita que las respuestas o RPC los revelen. Diseñar un cierre ciego y comprobar en tráfico y permisos que los datos no lleguen al cliente. Para gestionar diferencias, acordar cómo el servidor procesa las diferencias y qué ve el cajero.
4. **Alto — controles de integridad y precios.** El bloqueo visual de precio, descuento y devolución no demuestra que el servidor rechace pedidos manipulados, incluidos descuentos, líneas negativas o precios falsos. Tampoco deben bloquearse sin análisis las devoluciones legítimas del gerente o la sincronización offline; verificar el modelo exacto instalado.
5. **Alto — políticas aplicadas a todos los pedidos.** La regla actual bloquea `onDeleteOrder` al cajero sin distinguir venta confirmada de un borrador. Puede impedir corregir un carrito antes de cobrar. Comprobar en interfaz y definir qué operación se permite antes y después de confirmar.
6. **Medio — datos locales y sin conexión.** El POS puede mantener datos en el navegador. Las restricciones de interfaz no garantizan que totales, costos o ventas previas no se hayan sincronizado al dispositivo. Examinar respuestas, caché y almacenamiento local; evaluar uso compartido de tableta y cierre de sesión.

## Matriz de pruebas a ejecutar en una base aislada

| Prueba | Resultado requerido |
| --- | --- |
| Cajero modifica precio o descuento en interfaz y solicita guardar por RPC | Rechazo en servidor; sin venta alterada persistida. |
| Cajero envía devolución, cantidad negativa o modifica orden pagada | Rechazo; auditoría de la tentativa según diseño. |
| Cajero cambia su rol en datos del navegador o suplanta ID de gerente | La autorización no cambia; operación privilegiada rechazada. |
| Cajero intenta leer pedidos históricos, reportes, costos y totales usando interfaz o llamadas directas | Acceso denegado o respuesta sin campos protegidos; comprobar también datos precargados. |
| Cajero cierra caja con efectivo contado distinto del esperado | Puede completar el procedimiento autorizado sin recibir ventas totales ni montos por medio; diferencia visible al gerente. |
| Cajero elimina artículo o cancela carrito sin cobrar | Comportamiento acordado y utilizable; no afecta órdenes ya pagadas. |
| Gerente inicia sesión con su propia identidad y hace devolución | Se autoriza y registra quién, cuándo y motivo opcional. |
| Cajero manipula venta almacenada offline antes de sincronizar | El servidor aplica las mismas reglas o el flujo falla de forma segura, sin pérdida silenciosa. |
| Revisión de navegador después de cierre de sesión | No quedan disponibles datos no autorizados según la política y los límites técnicos documentados. |

El cierre ciego y el modo offline pueden entrar en conflicto con el diseño estándar de Odoo. Si no se consigue un mecanismo seguro y probado, no prometer privacidad ni funcionamiento sin conexión: operar con procedimiento alternativo acordado y mantener el despliegue bloqueado.

Referencia: https://www.odoo.com/documentation/18.0/es/applications/sales/point_of_sale.html
