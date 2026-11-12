# Consideraciones de uso, privacidad y servicio

Fecha de revisión: 11 de noviembre de 2026. Documento orientativo para el proyecto; no sustituye la revisión de un abogado. Las medidas propuestas no certifican que el sistema las cumpla: deben implementarse y probarse.

## Alcance

El POS registra ventas y sesiones de caja para una cafetería. No se solicita identificación de clientes para ventas corrientes como requisito funcional inicial. Sí habrá datos de usuarios, por ejemplo nombre, cuenta y acciones realizadas. No recolectar datos de clientes ni información adicional si no se necesitan para el servicio.

Los datos personales son información asociada a personas naturales identificadas o identificables; la información puramente corporativa de una persona jurídica no se clasifica automáticamente como dato personal. Sin embargo, nombres, credenciales o actividad identificable de cajeros y administradores pueden serlo. Véase [SIC: ámbito de la Ley 1581](https://sedeelectronica.sic.gov.co/boletin-juridico/conceptos/ambito-de-aplicacion-de-la-ley-1581-de-2012-en-datos-corporativos).

## Roles y deberes

De manera preliminar, si la cafetería determina las finalidades del tratamiento de datos personales y Manuel los administra por cuenta de ella, la cafetería podría ser responsable y Manuel encargado. La calificación depende de lo que efectivamente hagan y debe confirmarse. El responsable y el encargado tienen deberes propios de seguridad y confidencialidad; corresponde definir finalidades, procedimientos y medios. La autorización debe obtenerse cuando sea exigible, considerando las excepciones legales: no debe asumirse que toda operación requiere la misma base. Fuentes: [Ley 1581, artículos 3, 4, 9, 10, 17 y 18](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=49981); [SIC: deberes del encargado](https://sedeelectronica.sic.gov.co/index.php/publicaciones/boletin-juridico/concepto/deberes-del-encargado-del-tratamiento-de-datos-personales-en-los-contratos-de-prestacion-de-servicios).

La cafetería debe revisar su política de tratamiento y procedimientos para consultas y reclamos. No se puede concluir con los datos disponibles si debe inscribir alguna base en el RNBD: depende de su naturaleza y condiciones aplicables. La ausencia de obligación de inscripción no elimina las demás obligaciones de protección de datos. [SIC: obligados al RNBD](https://sedeelectronica.sic.gov.co/publicaciones/boletin-juridico/concepto/cuales-personas-estan-obligadas-realizar-el-registro-de-bases-de-datos-personales-en-el-rnbd).

## Medidas recomendadas antes de operar

1. Asignar cuentas individuales; limitar cajero a sus funciones y reservar reportes y administración para autorizados. Validar permisos en servidor, no solo ocultando botones. No registrar contraseñas ni datos personales innecesarios en logs.
2. Usar HTTPS, respaldos externos protegidos y prueba de restauración; fijar frecuencia, retención, acceso, cifrado y procedimiento ante pérdida de equipos.
3. Documentar cómo identificar, contener y comunicar incidentes a las partes y, cuando corresponda legalmente, a la autoridad; evitar prometer confidencialidad absoluta o ausencia de acceso legalmente exigible. [SIC: guía de incidentes](https://sedeelectronica.sic.gov.co/noticias/superindustria-expide-guia-para-la-gestion-de-incidentes-de-seguridad-en-el-tratamiento-de-datos-personales).
4. Definir expresamente si nube y respaldos quedan fuera de Colombia, qué proveedores intervienen y si accederán a datos personales. Revisar condiciones de transferencia o transmisión internacional y contratos aplicables antes de elegir la región; no asumir que usar nube extranjera sea automáticamente ilegal o suficiente por sí solo.
5. Establecer plazos de conservación, exportación y eliminación teniendo en cuenta obligaciones legales de conservación y solicitudes legítimas; no prometer borrado inmediato universal.
6. No usar datos del negocio para fines propios ni compartirlos con terceros sin la base e instrucciones correspondientes. [SIC: límites del encargado](https://sedeelectronica.sic.gov.co/publicaciones/boletin-juridico/concepto/el-encargado-no-puede-hacer-analisis-de-datos-sin-instruccion-del-responsable).

## Acuerdo de servicio sugerido

Preparar y revisar con don Efraín un acuerdo que identifique las partes y establezca: alcance y funciones excluidas; precio inicial y mensual y cambios de costo; quién es dueño y administrador de las cuentas de nube y dominio; responsables de acceso, contraseñas y respaldos; confidencialidad; proveedores y ubicación de datos; soporte, horario y tiempos objetivo realistas; ventanas de mantenimiento; continuidad y procedimiento con vales; tratamiento de incidentes; exportación y entrega de datos al finalizar; plazo y forma de terminación. No prometer disponibilidad del 100 % ni recuperación que no se haya probado.

Se puede acordar una licencia o permiso de uso y aclarar titularidad del código propio y de los datos, respetando las licencias de Odoo y de cada módulo de terceros. Verificar las licencias específicas y compatibilidad antes de distribuir o modificar componentes; no asumir que todos los módulos de Odoo son open source.

## Asuntos fiscales

El proyecto no contempla integración fiscal automática. La decisión de no integrar una entidad no elimina eventuales obligaciones de facturación, conservación o entrega de información. El contador de la cafetería debe confirmar qué comprobante se requiere y cómo operar antes de producción.
