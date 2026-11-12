# Guion de pruebas en PowerShell: entorno aislado cafeteria-dev

Estado: guion preparado de forma estática el 12 de noviembre de 2026. Ninguno de los comandos de este documento fue ejecutado al escribirlo; las salidas esperadas son lo que debería ocurrir según `dev/cafeteria/compose.yml` y el comportamiento documentado de Odoo 18, no resultados observados. Si una salida difiere, no continuar: pegar la salida real y detenerse.

## Alcance y reglas de seguridad

- Solo se toca el proyecto Compose `cafeteria-dev`, definido en `dev/cafeteria/compose.yml`. Servicios reales del archivo: `db` (postgres:16, usuario `odoo_dev`, base de mantenimiento `postgres`) y `odoo` (odoo:18.0, publicado solo en `127.0.0.1:18069`). Volúmenes del archivo: `db_data` y `odoo_data`, que Compose nombra `cafeteria-dev_db_data` y `cafeteria-dev_odoo_data`.
- Prohibido en este guion y en cualquier variante: `down -v`, `volume prune`, `system prune`, `docker rm` o `docker volume rm` sobre algo que no sea explícitamente de este guion, y cualquier comando con el proyecto principal `saas-odoo` o sus volúmenes. Tampoco ejecutar `scripts/configure_laguapa_pos.py`, `scripts/backup.sh` ni `scripts/restore.sh` (apuntan al proyecto principal y leen `.env`).
- Todos los comandos usan `-p cafeteria-dev` y `-f dev/cafeteria/compose.yml`; a partir de la parte 3 se añade además `-f` con el override fuera del repositorio. No omitir `-p`.
- No editar el repositorio: no cambiar `installable` en `addons/`, ni `dev/cafeteria/compose.yml`, ni el proyecto principal. Los módulos se prueban en una copia fuera del repo (parte 3).
- Datos: solo ficticios. Las credenciales del compose son públicas y de prueba; no usar datos reales de la cafetería ni de don Efraín.
- No pegar de vuelta contenidos de `.env` ni `CREDENCIALES.md`.

## Preparación de la sesión

Abrir PowerShell, ir a la raíz del repositorio y definir un atajo para no equivocarse de proyecto:

```powershell
cd <ruta-al-repositorio-odoo-cafeteria>
function dc { docker compose -p cafeteria-dev -f dev/cafeteria/compose.yml @args }
function dodoo { dc exec -T odoo sh -c 'PGHOST=$HOST PGPORT=$PORT PGUSER=$USER PGPASSWORD=$PASSWORD exec odoo $@' sh @args }
```

`dodoo` ejecuta el comando `odoo` dentro del contenedor `odoo` usando las variables `HOST`, `PORT`, `USER` y `PASSWORD` que el compose ya define en ese contenedor, pasadas como variables `PG*` de PostgreSQL. Así la contraseña no se escribe en la línea de comandos de PowerShell ni como argumento `--db_password`. Esto no está verificado: se asume que Odoo 18 toma `PGHOST`, `PGUSER` y `PGPASSWORD` de libpq cuando no recibe `--db_host`, `--db_user` ni `--db_password`. Si el comando falla con error de conexión o autenticación a PostgreSQL, usar como alternativa los argumentos explícitos `--db_host=db --db_user=odoo_dev --db_password=<contraseña de dev/cafeteria/compose.yml>`; la contraseña del compose es pública y exclusiva de pruebas, por lo que ese riesgo es bajo. Con la alternativa, la contraseña queda visible en la lista de procesos del contenedor mientras corre el comando.

Desde la parte 3 se usa además la función `dct` (con el override fuera del repo); si se cierra la ventana hay que redefinir `$copia` y `dct` (paso 3.3). Reemplazar `<ruta-al-repositorio-odoo-cafeteria>` por la ruta real en Windows. La función `dc` solo vive en esa ventana. En el resto del guion `dc` equivale al comando completo. Si se prefiere no usar la función, escribir el comando completo.

---

## Parte 1. Estado del entorno

### Paso 1.1 Motor Docker

```powershell
docker info --format "{{.ServerVersion}} {{.OperatingSystem}}"
```

Esperado: una línea con la versión del servidor y el nombre del sistema (Docker Desktop con WSL 2). Si aparece error de conexión al motor, abrir Docker Desktop y repetir.

Pegar de vuelta: la línea o el error completo.

### Paso 1.2 Validar el compose

```powershell
dc config --quiet
```

Esperado: sin salida de error (puede mostrar una advertencia de configuración de Docker del usuario, ya vista antes). Código de salida 0.

```powershell
$LASTEXITCODE
```

Esperado: `0`.

Pegar de vuelta: cualquier texto que aparezca en `config --quiet` y el valor de `$LASTEXITCODE`.

### Paso 1.3 Estado de los contenedores del proyecto

```powershell
dc ps
```

Esperado: dos filas, `db` con estado `running (healthy)` y `odoo` con estado `running` y puerto `127.0.0.1:18069->8069/tcp`. Si la lista está vacía, iniciar con el paso 1.4.

Pegar de vuelta: la tabla completa.

### Paso 1.4 Iniciar si hace falta (no destructivo)

```powershell
dc up -d
dc ps
```

Esperado: `db` pasa a healthy y luego `odoo` inicia. Puede tardar un minuto.

Pegar de vuelta: la salida de `dc ps`.

### Paso 1.5 Odoo responde y no hay conflicto con otros servicios

```powershell
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:18069/web/database/selector).StatusCode
```

Esperado: `200`.

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker volume ls --format "{{.Name}}"
```

Esperado: se ven los contenedores de `cafeteria-dev`. Si el proyecto principal `saas-odoo` está detenido, no debe aparecer en `docker ps`. En volúmenes deben figurar `cafeteria-dev_db_data` y `cafeteria-dev_odoo_data`; otros volúmenes pertenecen a otros proyectos y no se tocan.

Pegar de vuelta: el código `200` y ambas listas (nombres de volúmenes, nada más).

### Paso 1.6 Versión y bases existentes

```powershell
dc exec -T odoo odoo --version
dc exec -T db psql -U odoo_dev -d postgres -Atc "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY 1"
```

Esperado: una versión de Odoo 18.0 y la lista de bases (al menos `postgres`; ninguna base de cafetería si nunca se creó).

Pegar de vuelta: ambas salidas.

---

## Parte 2. Base aislada con datos ficticios

La base de pruebas manuales se llama `cafeteria_prueba`. Los datos de demostración de Odoo son ficticios y genéricos, no el catálogo real; el catálogo real sigue pendiente.

### Paso 2.1 Crear la base e instalar Punto de venta

El comando crea la base si no existe, instala `point_of_sale` y termina. Se usa `--no-http` para no competir por el puerto con el Odoo en ejecución.

```powershell
dodoo -d cafeteria_prueba -i point_of_sale --stop-after-init --no-http 2>&1 | Tee-Object -FilePath salida-paso-2-1.log | Select-Object -Last 30
Select-String -Path salida-paso-2-1.log -Pattern "ERROR|CRITICAL" | Select-Object -First 20
```

Esperado: muchas líneas de registro y, al final, sin `ERROR` ni `CRITICAL`; el proceso termina. Puede tardar varios minutos. Es normal ver `WARNING` de módulos. El segundo comando no debe mostrar coincidencias.

Pegar de vuelta: las últimas 30 líneas y la salida del `Select-String`.

### Paso 2.2 Confirmar módulos instalados

```powershell
dc exec -T db psql -U odoo_dev -d cafeteria_prueba -Atc "SELECT name, state, latest_version FROM ir_module_module WHERE state='installed' AND name IN ('base','point_of_sale','account','stock','hr') ORDER BY name"
```

Esperado: `base` y `point_of_sale` en `installed` con versión 18.0.x. La edición (Community o Enterprise) no se deduce de esta consulta; la imagen `odoo:18.0` es Community, a confirmar al abrir Odoo.

Pegar de vuelta: las filas.

---

## Parte 3. Copia aislada de los módulos e instalación

### Por qué una copia

Los manifests de `pos_order_integrity` y `pos_blind_cash_closing` tienen `installable: False`, a propósito, porque el código no está verificado. El directorio `addons/` es compartido: el `docker-compose.yml` del proyecto principal monta `./addons` en lectura y escritura, y `dev/cafeteria/compose.yml` monta `../../addons` en solo lectura. Poner `installable: True` en el repositorio expondría los módulos al proyecto principal. Por eso este guion nunca edita el repositorio: trabaja con una copia fuera de él, con `installable: True` solo en la copia, y la monta en el contenedor `odoo` de `cafeteria-dev` mediante un archivo override nuevo que también vive fuera del repositorio. No se edita `dev/cafeteria/compose.yml` ni nada del proyecto principal.

### Paso 3.1 Crear la copia fuera del repo

Desde la raíz del repositorio:

```powershell
$copia = Join-Path $env:USERPROFILE "cafeteria-pruebas"
New-Item -ItemType Directory -Force -Path "$copia\addons" | Out-Null
robocopy addons\pos_order_integrity "$copia\addons\pos_order_integrity" /E /XD __pycache__ | Out-Null
robocopy addons\pos_blind_cash_closing "$copia\addons\pos_blind_cash_closing" /E /XD __pycache__ | Out-Null
Get-ChildItem "$copia\addons" | Select-Object Name
```

Nota: robocopy devuelve códigos de salida menores que 8 en éxito; no usar `$LASTEXITCODE` aquí como criterio de error si vale 1 a 7.

Esperado: la lista muestra exactamente dos carpetas, `pos_order_integrity` y `pos_blind_cash_closing`. No se copian los otros módulos (`pos_role_policy`, módulos de La Guapa, etc.).

Pegar de vuelta: la lista de carpetas.

### Paso 3.2 Poner installable True solo en la copia

```powershell
foreach ($m in "pos_order_integrity","pos_blind_cash_closing") {
  $f = "$copia\addons\$m\__manifest__.py"
  (Get-Content -Raw -Encoding UTF8 $f) -replace '"installable":\s*False', '"installable": True' | Set-Content -Encoding UTF8 -NoNewline $f
}
Select-String -Path "$copia\addons\*\__manifest__.py" -Pattern '"installable"'
Select-String -Path addons\pos_order_integrity\__manifest__.py, addons\pos_blind_cash_closing\__manifest__.py -Pattern '"installable"'
```

Esperado: en la copia ambas líneas muestran `"installable": True`; en el repositorio, ambas siguen mostrando `"installable": False`. Si el repositorio muestra `True`, detenerse y avisar.

Pegar de vuelta: las cuatro líneas resultantes.

### Paso 3.3 Crear el archivo override fuera del repo

El compose base monta el directorio de addons con `../../addons:/mnt/extra-addons:ro`. En Docker Compose, al combinar archivos, la lista `volumes` se une por ruta de destino: una entrada del override con el mismo destino `/mnt/extra-addons` reemplaza a la del base. Así el override cambia solo el origen del montaje, sin tocar el compose principal.

```powershell
@"
services:
  odoo:
    volumes:
      - ${env:USERPROFILE}\cafeteria-pruebas\addons:/mnt/extra-addons:ro
"@ | Set-Content -Encoding UTF8 "$copia\compose.test.yml"
Get-Content "$copia\compose.test.yml"
```

Esperado: el contenido muestra la ruta absoluta de la copia con tu usuario de Windows. Si el nombre de usuario contiene espacios, escribir la ruta entre comillas dobles en el archivo.

Definir un segundo atajo que usa ambos archivos y el mismo proyecto, y redefinir `dodoo` para que use ese atajo (con el montaje de la copia):

```powershell
function dct { docker compose -p cafeteria-dev -f dev/cafeteria/compose.yml -f "$copia\compose.test.yml" @args }
function dodoo { dct exec -T odoo sh -c 'PGHOST=$HOST PGPORT=$PORT PGUSER=$USER PGPASSWORD=$PASSWORD exec odoo $@' sh @args }
dct config | Select-String -Pattern "extra-addons" -Context 0,0
```

Esperado: una sola entrada de montaje a `/mnt/extra-addons` apuntando a la copia y en modo de solo lectura, sin la ruta del repositorio. Si aparecen dos montajes al mismo destino o aún aparece `addons` del repositorio, detenerse y pegar la salida de `dct config`.

Pegar de vuelta: la salida del `Select-String`.

### Paso 3.4 Aplicar el montaje y comprobar

```powershell
dct up -d
dct ps
dct exec -T odoo ls /mnt/extra-addons
```

Esperado: `up -d` recrea solo el contenedor `odoo` con el montaje nuevo; los volúmenes `cafeteria-dev_db_data` y `cafeteria-dev_odoo_data` se conservan (no se usa `-v`). `ls` muestra únicamente `pos_blind_cash_closing` y `pos_order_integrity`. Desde ahora usar `dct` en lugar de `dc` para todo el resto del guion.

Pegar de vuelta: `dct ps` y el `ls`.

### Paso 3.5 Instalar los módulos en cafeteria_prueba

El orden importa: `pos_blind_cash_closing` depende de `pos_order_integrity`.

```powershell
dodoo -d cafeteria_prueba -i pos_order_integrity,pos_blind_cash_closing --stop-after-init --no-http 2>&1 | Tee-Object -FilePath salida-paso-3-5.log | Select-Object -Last 40
Select-String -Path salida-paso-3-5.log -Pattern "ERROR|CRITICAL|Traceback|ParseError|ValidationError" | Select-Object -First 30
```

Esperado: instalación sin errores. Los README de ambos módulos declaran TODO-VERIFICAR abiertos (nombres de modelos, xmlids y vistas de Odoo 18 sin comprobar), y dicen que algunos fallan de forma ruidosa al instalar. Un error aquí es un hallazgo esperable, no un fallo del guion: pegar el traceback completo y detenerse.

Pegar de vuelta: las últimas 40 líneas y la salida del `Select-String`.

### Paso 3.6 Detectar errores de validación de vistas

Tras instalar, actualizar `point_of_sale` fuerza la revalidación de vistas heredadas por los módulos propios:

```powershell
dodoo -d cafeteria_prueba -u point_of_sale --stop-after-init --no-http 2>&1 | Tee-Object -FilePath salida-paso-3-6.log | Select-Object -Last 30
Select-String -Path salida-paso-3-6.log -Pattern "ERROR|CRITICAL|Traceback|ParseError|Invalid view|View error" | Select-Object -First 30
```

Esperado: sin coincidencias. Cualquier error de vista (xpath que no coincide, campo inexistente, etiqueta `<list>` inválida) es un hallazgo.

Pegar de vuelta: las últimas 30 líneas y la salida del `Select-String`.

### Paso 3.7 Confirmar el estado instalado

```powershell
dct exec -T db psql -U odoo_dev -d cafeteria_prueba -Atc "SELECT name, state FROM ir_module_module WHERE name IN ('pos_order_integrity','pos_blind_cash_closing') ORDER BY name"
dct exec -T db psql -U odoo_dev -d cafeteria_prueba -Atc "SELECT module, name FROM ir_model_data WHERE module='pos_order_integrity' AND model='res.groups' ORDER BY name"
```

Esperado: ambos módulos en `installed`; los grupos `group_pos_store_manager` y `group_cashier_restricted` existen (confirmado leyendo `security/groups.xml`: nombres visibles "Punto de venta: gerente de tienda" y "Punto de venta: cajero restringido").

Pegar de vuelta: ambas salidas.

---

## Parte 4. Configuración del punto de venta y usuarios

### Paso 4.1 Comprobar la UdM kg

```powershell
dct exec -T db psql -U odoo_dev -d cafeteria_prueba -Atc "SELECT id, name::text, rounding FROM uom_uom WHERE name::text ILIKE '%kg%' OR name::text ILIKE '%kilo%'"
```

Esperado: una fila para kg con `rounding` igual a `0.001`. Si muestra otro valor (por ejemplo 0.01), anotarlo como hallazgo: afectaría el pesaje de 0,250 kg. No corregir con SQL; si hay que ajustarlo, hacerlo desde la interfaz de Odoo (Inventario o Ventas > Configuración > Unidades de medida) y registrar el cambio. El módulo `pos_order_integrity` sube la precisión decimal `product.decimal_product_uom` a 3, pero el README declara pendiente verificar el redondeo de la UdM en la interfaz del POS.

Pegar de vuelta: las filas.

### Paso 4.2 Configurar el punto de venta de prueba

En http://127.0.0.1:18069, base `cafeteria_prueba`, como `admin` (cambiar su contraseña inicial de inmediato por una de prueba que no se reutilice). Ir a Punto de venta > Configuración > Ajustes, elegir el punto de venta de prueba y:

1. Activar el control avanzado de efectivo (campo `cash_control`). Es necesario para que el cierre pida efectivo contado y exista diferencia de caja.
2. Desactivar el límite máximo de diferencia (campo `set_maximum_difference`). Si está activo, el cierre se bloquea según la diferencia y el cajero podría deducir el efectivo esperado por tanteo; el módulo de cierre ciego se niega a cerrar en ese caso.
3. Revisar que existan los métodos de pago de efectivo y uno electrónico de prueba (por ejemplo "Nequi prueba").

Los nombres de menú pueden variar entre versiones; anotar los que aparezcan.

### Paso 4.3 Cuentas de pérdida y ganancia del diario de efectivo

Sin ellas, un cierre con diferencia puede fallar, y ese fallo delataría al cajero que hay diferencia. Ir a Contabilidad > Configuración > Diarios, abrir el diario de efectivo usado por el método de pago en efectivo y definir las cuentas de pérdida y de ganancia por diferencia de caja. Si no hay plan de cuentas instalado y no hay cuentas disponibles, no inventarlas: anotarlo y consultar a Manuel, porque se requiere decidir el paquete contable (el contador debe revisarlo para producción).

Verificar por SQL que quedaron definidas (los nombres de columna pueden variar; si falla la consulta, pegar el error):

```powershell
dct exec -T db psql -U odoo_dev -d cafeteria_prueba -Atc "SELECT j.id, j.name::text, j.loss_account_id, j.profit_account_id FROM account_journal j WHERE j.type='cash'"
dct exec -T db psql -U odoo_dev -d cafeteria_prueba -Atc "SELECT id, name::text, cash_control, set_maximum_difference FROM pos_config"
```

Esperado: el diario de efectivo con `loss_account_id` y `profit_account_id` no vacíos; el punto de venta con `cash_control` en `t` y `set_maximum_difference` en `f`.

Pegar de vuelta: ambas salidas, o la descripción de lo que impide completarlas.

### Paso 4.4 Crear los usuarios de prueba

En Ajustes > Usuarios, con correos ficticios (por ejemplo `cajero@prueba.local`, `efrain@prueba.local`), contraseñas de prueba no reutilizadas:

1. Cajero: cuenta propia, solo con el grupo de usuario de Punto de venta (y opcionalmente "Punto de venta: cajero restringido"). Sin grupos de Contabilidad ni de administrador.
2. Efraín: cuenta propia con el grupo "Punto de venta: gerente de tienda" (id `pos_order_integrity.group_pos_store_manager`). No asignarle Administrador de Punto de venta como sustituto: según los README, el grupo gerente es el que levanta las restricciones, y todo usuario que no esté en ese grupo ni sea administrador técnico se trata como restringido y ciego, tenga o no el grupo de cajero. Según el comentario de `groups.xml`, ese grupo no concede por sí mismo los menús nativos de informes; si Efraín no ve el menú Informes, registrarlo como hallazgo y decidir aparte qué grupo nativo adicional hace falta, probando ese cambio como caso separado.
3. `admin` hace de Manuel.

Después de cambiar los grupos de un usuario, reiniciar el servidor (`dct restart odoo`) antes de probar: el README de cierre ciego dice que no está verificado el comportamiento de la caché de reglas.

Confirmar por SQL (sin contraseñas):

```powershell
dct exec -T db psql -U odoo_dev -d cafeteria_prueba -Atc "SELECT u.login, string_agg(g.name::text, ' | ' ORDER BY g.name::text) FROM res_users u JOIN res_groups_users_rel r ON r.uid=u.id JOIN res_groups g ON g.id=r.gid WHERE u.login IN ('cajero@prueba.local','efrain@prueba.local') AND (g.name::text ILIKE '%Cafeter%' OR g.name::text ILIKE '%Point of Sale%' OR g.name::text ILIKE '%Punto de venta%') GROUP BY u.login"
```

Esperado: el cajero sin "Punto de venta: gerente de tienda"; Efraín con "Punto de venta: gerente de tienda". Si los logins difieren, ajustar los literales.

Pegar de vuelta: las filas. No pegar contraseñas.

---

## Parte 5. Pruebas automáticas de Odoo

### Por qué dos bases separadas

Los tests de `pos_order_integrity` crean pedidos y pagos con un usuario que no pertenece a "Punto de venta: gerente de tienda". Bajo las reglas de `pos_blind_cash_closing`, todo usuario sin ese grupo es ciego y no ve pedidos cobrados ni pagos. Si ambos módulos están instalados en la misma base, esos tests pueden fallar por la interacción entre módulos y no por un defecto del guard. Por eso se prueba en dos bases con nombres exactos:

- Base A, `pos_test_integrity`: solo `point_of_sale` y `pos_order_integrity`. Corre las etiquetas del guard.
- Base B, `pos_test_blind_closing`: `point_of_sale`, `pos_order_integrity` y `pos_blind_cash_closing`. Corre solo las etiquetas del cierre ciego.

Aviso: los resultados de la base A no cubren la interacción entre ambos módulos (por ejemplo, si el flujo de venta del cajero sigue funcionando con las reglas del cierre ciego activas). Esa interacción se prueba a mano en la parte 6 sobre `cafeteria_prueba`, donde están ambos instalados.

### Archivos de pruebas reales (leídos del directorio al escribir este guion)

`addons/pos_order_integrity/tests/`: `common.py` (clase base `PosIntegrityCommon`), `test_confirmed_orders.py`, `test_cost_snapshot.py`, `test_internal_writes.py`, `test_payments.py`, `test_price_validation.py`, `test_quantities_and_modes.py`, `test_refunds_corrections.py`.

`addons/pos_blind_cash_closing/tests/`: `test_blind_close.py` (clase `TestBlindClose`).

Antes de ejecutar, volver a listar los directorios por si el desarrollador agregó archivos nuevos:

```powershell
Get-ChildItem addons\pos_order_integrity\tests, addons\pos_blind_cash_closing\tests -Filter "test_*.py" | Select-Object Directory, Name
```

Si aparece un archivo que no está en esta lista, la copia de la parte 3 puede estar desactualizada: repetir los pasos 3.1 y 3.2 y reiniciar `odoo` (`dct restart odoo`) antes de seguir.

Etiquetas: cada clase de prueba lleva `@tagged("post_install", "-at_install", "<modulo>")`, con `<modulo>` igual a `pos_order_integrity` o `pos_blind_cash_closing` (comprobado en `common.py`, que las otras clases heredan o repiten). Las pruebas corren después de instalar y se seleccionan con `--test-tags /<modulo>`. Un test omitido (`skip`) no cuenta como aprobado.

### Paso 5.1 Base A: instalar el guard y ejecutar sus pruebas

La base se crea con el propio comando (`-d` con una base inexistente la crea). Antes de empezar, confirmar que el nombre no existe:

```powershell
dct exec -T db psql -U odoo_dev -d postgres -Atc "SELECT datname FROM pg_database WHERE datname IN ('pos_test_integrity','pos_test_blind_closing')"
```

Esperado: sin filas. Si aparece alguna, no borrarla: pegar la salida y detenerse.

```powershell
dodoo -d pos_test_integrity -i point_of_sale,pos_order_integrity --test-enable --test-tags /pos_order_integrity --stop-after-init --no-http 2>&1 | Tee-Object -FilePath salida-paso-5-1.log | Select-Object -Last 40
Select-String -Path salida-paso-5-1.log -Pattern "FAIL:|ERROR:|Traceback|skipped|failed|Ran " | Select-Object -First 80
```

Esperado: líneas `Starting Test...` para las clases de los siete archivos del guard (`TestConfirmedOrders`, `TestCostSnapshot`, `TestInternalWrites`, `TestPaymentsAndConfirmation`, `TestPriceValidation`, `TestQuantitiesAndModes`, `TestRefundsAndCorrections`) y un resumen sin fallos ni errores. Los README advierten que los fixtures de sesión, configuración y pedidos POS son conjeturas hechas por análisis estático: un error en `setUp` no demuestra nada sobre el módulo, hay que ajustar primero el montaje de la prueba. Pegar el traceback tal cual.

Pegar de vuelta: las 40 líneas y la salida del `Select-String`.

### Paso 5.2 Base B: instalar ambos módulos y ejecutar las pruebas del cierre ciego

```powershell
dodoo -d pos_test_blind_closing -i point_of_sale,pos_order_integrity,pos_blind_cash_closing --test-enable --test-tags /pos_blind_cash_closing --stop-after-init --no-http 2>&1 | Tee-Object -FilePath salida-paso-5-2.log | Select-Object -Last 40
Select-String -Path salida-paso-5-2.log -Pattern "FAIL:|ERROR:|Traceback|skipped|failed|Ran " | Select-Object -First 80
```

Esperado: líneas `Starting TestBlindClose...` y un resumen sin fallos ni errores. Aquí no se ejecutan los tests del guard (la etiqueta del guard no está en `--test-tags`), a propósito.

Pegar de vuelta: las 40 líneas y la salida del `Select-String`.

### Paso 5.3 Una clase o un test en concreto (si hay fallos)

Para repetir solo una clase, sobre la base ya creada, con `-u` en lugar de `-i`:

```powershell
dodoo -d pos_test_integrity -u pos_order_integrity --test-enable --test-tags /pos_order_integrity:TestPaymentsAndConfirmation --stop-after-init --no-http 2>&1 | Select-Object -Last 40
```

Esperado: mismo resultado para esa clase. Para el cierre ciego, usar `-d pos_test_blind_closing -u pos_blind_cash_closing` con `/pos_blind_cash_closing:TestBlindClose`.

Pegar de vuelta: las líneas de la ejecución.

### Paso 5.4 Limpieza de las dos bases de prueba

Solo estas dos bases, con nombre exacto, sin comodines. Conservar las bases hasta pegar los resultados si hubo fallos; si pasaron o ya se pegaron los resultados:

```powershell
dct exec -T db dropdb -U odoo_dev pos_test_integrity
dct exec -T db dropdb -U odoo_dev pos_test_blind_closing
dct exec -T db psql -U odoo_dev -d postgres -Atc "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY 1"
```

Esperado: sin error; la lista final ya no contiene esas dos bases y sigue conteniendo `cafeteria_prueba`. No ejecutar `dropdb` con ningún otro nombre. Si se borra una base por error, no hay copia: las bases de prueba automática no se respaldan.

Pegar de vuelta: la lista de bases.

### Paso 5.5 Lo que estas pruebas no cubren

Las pruebas automáticas usan `TransactionCase` y llamadas de modelo, no la interfaz del POS ni peticiones HTTP reales. No cubren la interacción entre ambos módulos (base A), el diálogo de cierre (sin parche OWL, según el README), la caché del navegador, la operación sin conexión ni el rendimiento en celular. Esos puntos se prueban en la parte 6. Un resultado verde aquí no autoriza a pasar a producción.

---

## Parte 6. Casos manuales por perfil

Preparar en `cafeteria_prueba` (como Manuel o Efraín): dos o tres productos ficticios con modo de venta del módulo (por ejemplo "Café prueba" a 3.000 en modo unidad, "Pan prueba" a 1.000 en modo unidad, "Queso por peso" a 20.000/kg en modo peso con UdM kg), con costo manual conocido en uno y sin costo en otro. Los precios son ficticios y no sirven como catálogo. Anotar los nombres reales de menús y campos que aparezcan. Para cada caso registrar: acción, resultado visto y si coincide con lo esperado.

### Ayudantes de PowerShell para llamadas directas (RPC)

Se usan solo contra la base de pruebas y con la cuenta del cajero de prueba. La contraseña se pide por teclado, no se escribe en el archivo.

```powershell
$base = "http://127.0.0.1:18069"
function Odoo-Login($login) {
  $p = Read-Host "Contraseña de $login (prueba)" -AsSecureString
  $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($p))
  $s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
  $b = @{jsonrpc="2.0"; method="call"; params=@{db="cafeteria_prueba"; login=$login; password=$plain}} | ConvertTo-Json -Depth 5
  Invoke-RestMethod -Uri "$base/web/session/authenticate" -Method Post -ContentType "application/json" -Body $b -WebSession $s | Out-Null
  return $s
}
function Odoo-Call($s, $model, $method, $argsJson, $kwJson = "{}") {
  $b = "{`"jsonrpc`":`"2.0`",`"method`":`"call`",`"params`":{`"model`":`"$model`",`"method`":`"$method`",`"args`":$argsJson,`"kwargs`":$kwJson}}"
  try { (Invoke-RestMethod -Uri "$base/web/dataset/call_kw/$model/$method" -Method Post -ContentType "application/json" -Body $b -WebSession $s) | ConvertTo-Json -Depth 8 }
  catch { "HTTP: " + $_.Exception.Message }
}
$cajero = Odoo-Login "cajero@prueba.local"
```

Esperado: sin salida de error. Odoo suele responder HTTP 200 con un campo `error` en el JSON cuando rechaza una llamada; ese JSON es lo que hay que pegar. Una respuesta con `result` y datos donde se esperaba rechazo es un hallazgo. Si el inicio de sesión falla, no insistir: pegar el mensaje.

### 6.A Cajero que intenta vulnerar controles

Referencia: `docs/revision-cajero-adversarial.md` (revisión estática; esto son las pruebas reales que faltan). Sesión: usuario cajero.

| N.º | Acción | Esperado | Pegar de vuelta |
|---|---|---|---|
| A1 | Cobro en efectivo con cambio, como cajero real en el POS: abrir sesión con efectivo inicial 20.000, vender Café prueba (3.000) y cobrar entregando 5.000 en efectivo | Se cobra normal: el POS calcula cambio de 2.000, el pedido queda pagado, sin error de acceso | Mensajes de error si los hay y número de pedido |
| A1b | Pago mixto efectivo más Nequi, como cajero en el POS: venta de 10.000, 4.000 en efectivo y 6.000 con el método electrónico | Se cobra normal; el pedido queda pagado con dos pagos | Mensajes de error si los hay y número de pedido |
| A1c | Pago solo Nequi, como cajero en el POS: venta de Pan prueba (1.000) pagada completa con el método electrónico | Se cobra normal | Mensajes de error si los hay y número de pedido |
| A2 | Intentar cambiar precio o aplicar descuento en la interfaz | Bloqueado en la interfaz | Lo que muestra la pantalla |
| A3 | Por RPC, crear una línea con precio distinto del de lista o con descuento. Ejemplo: `Odoo-Call $cajero "pos.order.line" "create" '[[{"order_id":ID_BORRADOR,"product_id":ID_PROD,"qty":1,"price_unit":1,"discount":50}]]'` con ids reales | Rechazo del servidor; ninguna línea alterada guardada | Respuesta completa y, después, si existe la línea |
| A4 | Intentar devolución (línea con cantidad negativa o enlace a la línea original), o modificar un pedido ya pagado por RPC (`write` sobre `pos.order.line` de un pedido pagado) | Rechazo | Respuesta |
| A5 | Pago fabricado, caso 1: crear por RPC un `pos.order` con `state` en `paid` y sin pagos. Ejemplo mínimo: `Odoo-Call $cajero "pos.order" "create" '[[{"session_id":ID_SESION,"config_id":ID_CONFIG,"state":"paid","amount_total":5000,"amount_paid":5000,"amount_tax":0,"amount_return":0}]]'`. Puede faltar algún campo obligatorio de Odoo; un rechazo por campo faltante no cuenta: ajustar hasta que el servidor evalúe el estado | Rechazo; ningún pedido en `paid` sin pagos queda guardado. Si queda guardado es un hallazgo crítico (el README del guard declara la validación de pagos fuera de su alcance y el hallazgo está en corrección) | Respuesta, y verificar como Efraín si existe un pedido pagado sin pagos |
| A6 | Pago fabricado, caso 2: crear un `pos.payment` con importe negativo sobre un pedido propio. Ejemplo: `Odoo-Call $cajero "pos.payment" "create" '[[{"pos_order_id":ID_PEDIDO,"payment_method_id":ID_METODO,"amount":-1000}]]'` | Rechazo | Respuesta, y si existe el pago |
| A7 | Escritura directa en `pos.session`: `Odoo-Call $cajero "pos.session" "write" '[[ID_SESION],{"cash_register_balance_start":999999}]'` y luego `'[[ID_SESION],{"state":"closed"}]'` | Rechazo de ambas (el README de cierre ciego reconoce que el cajero conserva escritura nativa sobre su sesión y que falta un control; el hallazgo está en corrección) | Respuesta de cada una y el estado resultante de la sesión |
| A8 | `remove_from_ui` de un borrador: sincronizar un carrito sin cobrar y llamar `Odoo-Call $cajero "pos.order" "remove_from_ui" '[[ID_BORRADOR]]'`; repetir sobre un pedido ya pagado | Permitido para el borrador propio; rechazado para el pedido pagado | Respuesta de cada llamada |
| A9 | Intentar leer pedidos históricos, informes y costos desde menús, URL directa y RPC. Ejemplos: `search_read` de `pos.order`, `pos.payment`, `pos.session` con `cash_register_difference`, `pos.blind.cash.closing`, `product.product` con `standard_price`, y `report.point_of_sale.report_saledetails` método `get_sale_details` | Acceso denegado, lista vacía o ausencia del campo | Respuesta de cada llamada |
| A10 | En las herramientas de red del navegador (F12 > Red), revisar la precarga del POS y las respuestas de `get_closing_control_data`, `post_closing_cash_details` y `close_session_from_ui` | Sin totales históricos, costos, márgenes ni cifras de diferencia | Lista de campos sensibles vistos, si los hay |
| A11 | Cierre con faltante: con las ventas en efectivo de A1 y A1b (efectivo esperado por el servidor: inicial más lo cobrado en efectivo, descontando el cambio), contar 1.000 menos que lo esperado y cerrar | El cajero completa el cierre sin ver total de ventas, importes por medio ni la diferencia; el mensaje es genérico. Anotar el efectivo contado exacto para compararlo en D1 | Lo que muestra el diálogo de cierre y el valor contado |
| A11b | Faltante y venta en efectivo entre el conteo y el cierre: en una sesión nueva, vender en efectivo (anotar el monto), contar con 1.000 de faltante (paso de conteo del diálogo de cierre), abrir el POS en otra pestaña con el mismo usuario, hacer una venta en efectivo adicional (anotar el monto) y completar el cierre en la primera pestaña. Si Odoo no permite vender tras el conteo, anotar el mensaje exacto y continuar | A verificar en D1b: según el código de `_register` (`cash_closing.py`), al cerrar se recalculan las ventas en efectivo, `expected_cash` y `difference`, mientras `difference_at_count`, `counted_cash` y `opening_cash` se conservan; la venta posterior queda en `cash_sales_after_count`. El comportamiento real es lo que hay que anotar | Mensajes mostrados, montos de ambas ventas y valor contado |
| A14 | N1, reapertura de control: tras vender en la sesión abierta, llamar de nuevo `Odoo-Call $cajero "pos.session" "set_opening_control" '[[ID_SESION],100000,"reapertura"]'` (la firma leída en el código es `set_opening_control(cashbox_value, notes)`; si el número de argumentos no coincide, ajustar sin cambiar el sentido: nuevo monto de efectivo inicial) | Rechazo del servidor; el efectivo inicial de la sesión no cambia | Respuesta completa y el valor de `cash_register_balance_start` antes y después (como Efraín o por SQL de solo lectura) |
| A12 | Eliminar un artículo o cancelar un carrito sin cobrar en la interfaz | Comportamiento acordado, sin afectar pedidos pagados | Resultado |
| A13 | Cerrar sesión y revisar si el navegador conserva datos no autorizados | Sin datos no autorizados | Observación |

El diálogo estándar de cierre puede mostrar cifras sin sentido (diferencia calculada contra cero), porque no hay parche de interfaz; es una limitación documentada, anotar lo que se vea.

### 6.B Efraín con poca experiencia en celular lento

Referencia: `docs/revision-usuario-curioso.md` y `docs/reportes-ventas-y-costos.md`. Sesión: usuario Efraín (grupo "Punto de venta: gerente de tienda"), en un celular real si se puede. Si solo hay navegador de escritorio con rendimiento reducido, anotar que no equivale a un celular real.

| N.º | Acción | Esperado | Pegar de vuelta |
|---|---|---|---|
| B1 | Abrir Odoo desde el celular | El compose publica solo en `127.0.0.1`, así que no se verá desde el celular. Usar la pantalla del portátil o decidir aparte una exposición controlada; no abrir puertos a Internet | Resultado |
| B2 | Medir con cronómetro desde abrir la página hasta ver el informe de ventas | Anotar el tiempo; no hay umbral acordado | Segundos y dispositivo |
| B3 | Entrar con la cuenta de Efraín y consultar ventas del día y del mes (informes de pedidos y menú Cierres de caja) | Si Efraín tiene el grupo gerente ve ventas, importes y diferencias, a diferencia del cajero; anotar si el menú de informes nativo aparece o no (el grupo no lo concede por sí mismo) | Cifras vistas frente a cifras de las ventas hechas, y qué menús aparecen |
| B4 | Hacer una devolución con su propia identidad, con y sin motivo | Se autoriza para el gerente; queda registro de autor y fecha en `pos.order.audit.log`, el motivo es opcional | Cómo se registró y dónde se ve |
| B5 | Buscar promedio diario, productos más vendidos y diferencia de caja | Anotar qué existe en pantalla y qué falta. La diferencia de caja de la sesión de A11 debe estar disponible para el gerente | Lo encontrado y lo ausente |
| B6 | Tocar botones equivocados a propósito (borrar, cerrar, volver atrás) en medio de una operación | Sin pérdida silenciosa de datos | Qué pasó |
| B7 | Venta por peso de 0,250 kg a 20.000/kg (como cajero o Efraín) | Total de 5.000 | Total mostrado |
| B8 | Con la cuenta de Efraín, comprobar que no puede abrir Aplicaciones ni Ajustes técnicos | Denegado | Respuesta |

El cálculo del promedio diario depende de una decisión pendiente (ver `docs/reportes-ventas-y-costos.md`); en B5 anotar solo qué muestra Odoo.

### 6.C Usuario curioso

Sesión alternando cajero, Efraín y administrador, probando rutas y variantes no previstas.

| N.º | Acción | Esperado | Pegar de vuelta |
|---|---|---|---|
| C1 | Con el cajero, escribir en la barra del navegador rutas de Ajustes, Aplicaciones, Usuarios y reportes de punto de venta | Acceso denegado | Rutas y respuesta |
| C2 | Con Efraín, intentar abrir Aplicaciones y Ajustes técnicos y concederse permisos | Denegado | Respuesta |
| C3 | Abrir dos pestañas con la misma sesión de caja y vender en ambas | Sin duplicados ni pérdida; anotar el comportamiento | Resultado |
| C4 | Cortar la red del navegador a mitad de una venta y reconectar | Sin pérdida silenciosa ni duplicado; si no está garantizado, anotarlo | Lo ocurrido |
| C5 | Pago mixto: venta de 10.000, 4.000 en efectivo y 6.000 con el método electrónico (ya hecho en A1b; comparar totales por medio desde la cuenta de Efraín) | La venta suma 10.000 una vez | Totales por medio y total |
| C6 | Cambiar el costo manual de un producto después de vender y mirar el costo de la venta antigua | La venta antigua conserva su costo | Valores antes y después |
| C7 | Producto sin costo definido | El margen se muestra incompleto, no como costo cero | Lo que muestra Odoo |
| C8 | Ventas cerca de medianoche, solo si Odoo lo permite sin tocar SQL | Fecha local de Bogotá correcta | Fechas vistas |
| C9 | Probar productos con modo bolsa sin unidades por bolsa, modo peso con UdM distinta de kg, y peso con cuatro decimales (0,2505) | Rechazo (peso con más de tres decimales se rechaza, no se redondea) | Mensajes |

No modificar tablas SQL para forzar estos casos.

### 6.D Verificación por Efraín o Manuel tras los casos del cajero

Como Efraín o `admin`, y también por SQL de solo lectura:

| N.º | Acción | Esperado | Pegar de vuelta |
|---|---|---|---|
| D1 | Ver Cierres de caja (modelo `pos.blind.cash.closing`) tras el cierre con faltante de A11 | Registro con `state` cerrada, `opening_cash` 20.000, `cash_sales`, `cash_moves`, `expected_cash`, `counted_cash` igual al valor contado, `difference` igual a contado menos esperado (negativa de 1.000) y `difference_at_count` igual a `difference` (sin ventas posteriores; `cash_sales_after_count` en 0); `odoo_expected_cash` para el control cruzado y `odoo_mismatch` (campo calculado, solo visible en la vista) consistentes | Todos esos valores del registro |
| D1b | Registro de la sesión de A11b | `difference_at_count` con el faltante original de 1.000 negativo; `cash_sales_after_count` igual a la venta en efectivo hecha tras el conteo; `expected_cash` que incluye esa venta; `difference` igual a `counted_cash` menos `expected_cash` (distinta de `difference_at_count` por esa venta, lo que muestra que el cierre no oculta el faltante medido al contar); `calc_after_close` en falso. Anotar también `odoo_expected_cash` y `odoo_mismatch` | Todos esos valores y si coinciden con lo esperado |
| D2 | Revisar las líneas de las ventas de A1, A1b y A1c | Cada línea (ventas de A1, A1b y A1c) con costo histórico propio (`pos_unit_cost`, `pos_cost_known`, `pos_cost_date`) | Valores de una línea con costo y otra sin costo |
| D3 | Comprobar que no hay pedidos pagados sin pagos ni pagos negativos tras A5 y A6 | Ninguno | Resultado de las consultas siguientes |

```powershell
dct exec -T db psql -U odoo_dev -d cafeteria_prueba -Atc "SELECT o.id, o.name, o.state, o.amount_total FROM pos_order o WHERE o.state IN ('paid','done','invoiced') AND NOT EXISTS (SELECT 1 FROM pos_payment p WHERE p.pos_order_id=o.id)"
dct exec -T db psql -U odoo_dev -d cafeteria_prueba -Atc "SELECT id, pos_order_id, amount FROM pos_payment WHERE amount < 0"
dct exec -T db psql -U odoo_dev -d cafeteria_prueba -Atc "SELECT id, session_id, state, opening_cash, cash_sales, cash_moves, expected_cash, counted_cash, difference, difference_at_count, cash_sales_after_count, odoo_expected_cash, has_previous, opening_discrepancy, calc_after_close FROM pos_blind_cash_closing ORDER BY id"
```

Esperado: las dos primeras sin filas (si aparecen filas es un hallazgo; una devolución legítima del gerente puede generar un pago negativo y debe explicarse); la tercera con la fila del faltante. Los nombres de columna de la tercera consulta son los campos que declara `models/cash_closing.py` al escribir este guion (`odoo_mismatch` no tiene columna porque es calculado). Si el desarrollador agregó o renombró campos, la consulta puede fallar: pegar el error y ver las columnas con `\d pos_blind_cash_closing` dentro de `psql`.

---

## Parte 7. Respaldo y restauración aislada

Se respalda la base `cafeteria_prueba` del proyecto `cafeteria-dev` y se restaura en una base nueva `cafeteria_restaurada`, sin sobrescribir nada. No usar `scripts/backup.sh` ni `scripts/restore.sh`: están escritos para el proyecto principal y leen `.env`.

Detalle técnico: se evita redirigir binarios con `>` en PowerShell porque puede corromper el archivo; se genera el archivo dentro del contenedor y se copia con `docker compose cp`.

### Paso 7.1 Dump de la base

```powershell
dct exec -T db pg_dump -U odoo_dev -Fc -f /tmp/cafeteria_prueba.dump cafeteria_prueba
dct exec -T db ls -l /tmp/cafeteria_prueba.dump
```

Esperado: sin error; `ls` muestra el archivo con tamaño mayor que cero.

Pegar de vuelta: la línea de `ls`.

### Paso 7.2 Copiar el dump y el filestore al host

```powershell
New-Item -ItemType Directory -Force -Path respaldos-prueba | Out-Null
dct cp db:/tmp/cafeteria_prueba.dump respaldos-prueba/cafeteria_prueba.dump
dct cp odoo:/var/lib/odoo/filestore/cafeteria_prueba respaldos-prueba/filestore_cafeteria_prueba
Get-ChildItem respaldos-prueba | Select-Object Name, Length
```

Esperado: el dump aparece con tamaño mayor que cero y existe la carpeta del filestore. Si el último `cp` falla porque la carpeta no existe, es posible que la base aún no haya generado archivos adjuntos; anotarlo y pegar el error.

Pegar de vuelta: la tabla de `Get-ChildItem`.

### Paso 7.3 Restaurar en una base nueva

```powershell
dct exec -T db createdb -U odoo_dev cafeteria_restaurada
dct exec -T db pg_restore -U odoo_dev -d cafeteria_restaurada --no-owner /tmp/cafeteria_prueba.dump
dct exec -T db psql -U odoo_dev -d postgres -Atc "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY 1"
```

Esperado: `createdb` y `pg_restore` sin error (pueden aparecer avisos menores; pegarlos); la lista de bases incluye `cafeteria_prueba` y `cafeteria_restaurada`. Si `createdb` indica que la base ya existe, no borrarla: elegir otro nombre, por ejemplo `cafeteria_restaurada2`, y usarlo en lo que sigue.

Pegar de vuelta: toda la salida.

### Paso 7.4 Restaurar el filestore de la base nueva

```powershell
dct cp respaldos-prueba/filestore_cafeteria_prueba odoo:/var/lib/odoo/filestore/cafeteria_restaurada
dct exec -T -u root odoo chown -R odoo:odoo /var/lib/odoo/filestore/cafeteria_restaurada
```

Esperado: sin error. Omitir si en el paso 6.2 no hubo filestore.

Pegar de vuelta: cualquier error.

### Paso 7.5 Verificar la restauración

```powershell
dct exec -T db psql -U odoo_dev -d cafeteria_restaurada -Atc "SELECT count(*) FROM pos_order"
dct exec -T db psql -U odoo_dev -d cafeteria_prueba -Atc "SELECT count(*) FROM pos_order"
```

Esperado: ambos números iguales. Luego abrir http://127.0.0.1:18069, elegir la base `cafeteria_restaurada`, entrar con el usuario de pruebas y revisar que las ventas ficticias se vean.

Pegar de vuelta: ambos números y lo observado al abrir la base restaurada.

### Paso 7.6 Limpieza

Las bases de pruebas automáticas ya se limpian en el paso 5.4. `cafeteria_prueba` y `cafeteria_restaurada` no se borran hasta que Manuel lo confirme y se haya cerrado el informe. No se incluye ningún comando de borrado de volúmenes.

### Paso 7.7 Detener sin borrar datos

```powershell
dct stop
dct ps
```

Esperado: ambos servicios detenidos; los volúmenes se conservan.

---

## Qué pegar de vuelta al final

Un resumen con: salida de los pasos 1.3, 1.5 y 1.6; resultados de 2.1 y 2.2; de 3.1 a 3.7 (incluido el `-u point_of_sale`); de 4.1 a 4.4; de 5.1 y 5.2; las tablas 6.A, 6.B, 6.C y 6.D con resultado observado por fila; y salidas de 7.1 a 7.5. Los resultados que no coincidan con lo esperado son hallazgos y deben registrarse tal cual, sin corregirlos a mano.

## Decisiones pendientes que afectan las pruebas

Estas decisiones no se resuelven aquí; ver `docs/reportes-ventas-y-costos.md` y `docs/panel-tecnico-plan.md`: denominador del promedio diario, relación bolsa-unidades del pan, identificación de "llave", marca y modelo de la balanza, y catálogo y precios reales.
