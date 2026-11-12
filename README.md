# SaaS Odoo 18 — Entorno local con Docker Compose

Este repositorio contiene la configuración para ejecutar **Odoo 18** y **PostgreSQL 16** en un entorno local mediante Docker Compose.

El objetivo es contar con un entorno reproducible, con persistencia de datos, comunicación interna entre servicios, límites de recursos, verificación de salud de PostgreSQL y una configuración de logs con rotación.

> **Importante:** esta configuración está orientada principalmente a desarrollo y pruebas locales. Antes de utilizarla en producción, se deben revisar las credenciales, la exposición de puertos, las políticas de respaldo, la estrategia de actualización y la configuración de recursos.

## Tabla de contenido

- [Arquitectura](#arquitectura)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Requisitos](#requisitos)
- [Servicios](#servicios)
- [Recursos y límites](#recursos-y-límites)
- [Healthcheck y orden de inicio](#healthcheck-y-orden-de-inicio)
- [Persistencia de datos](#persistencia-de-datos)
- [Red y puertos](#red-y-puertos)
- [Configuración de Odoo](#configuración-de-odoo)
- [Inicio del entorno](#inicio-del-entorno)
- [Comandos de administración](#comandos-de-administración)
- [Verificación y diagnóstico](#verificación-y-diagnóstico)
- [Reconstrucción y actualización](#reconstrucción-y-actualización)
- [Respaldo y recuperación](#respaldo-y-recuperación)
- [Seguridad y recomendaciones](#seguridad-y-recomendaciones)
- [Solución de problemas](#solución-de-problemas)

## Arquitectura

El entorno está compuesto por dos servicios:

- **`sass-data-base`**: motor PostgreSQL 16, responsable de almacenar la información de Odoo.
- **`saas-odoo`**: aplicación Odoo 18, que se conecta a PostgreSQL mediante la red privada de Docker Compose.

```text
Equipo local
│
├── Navegador ───────────────> http://localhost:8069
│                                  │
│                             saas-odoo
│                             Odoo 18
│                                  │
│                         Red Docker privada
│                                  │
│                             sass-data-base
│                             PostgreSQL 16
│                                  │
│                         Volumen persistente
│                         odoo-db-data
│
└── Cliente PostgreSQL ──────> localhost:5432
```

La aplicación Odoo se conecta a PostgreSQL usando el nombre DNS del servicio `sass-data-base` y el puerto interno `5432`. No debe utilizar `localhost` como host de PostgreSQL desde el contenedor de Odoo, porque `localhost` apuntaría al propio contenedor de Odoo.

## Estructura del proyecto

Una estructura esperada es:

```text
proyecto-odoo/
├── compose.yaml
├── README.md
├── addons/
│   └── ...
└── config/
    └── odoo.conf
```

Descripción:

| Ruta | Descripción |
|---|---|
| `compose.yaml` | Define los servicios, redes, volúmenes, healthcheck y recursos. |
| `README.md` | Documentación del entorno. |
| `addons/` | Módulos personalizados de Odoo. Se monta dentro del contenedor en `/mnt/extra-addons`. |
| `config/odoo.conf` | Archivo de configuración de Odoo montado como solo lectura. |

Los directorios `addons/` y `config/` deben existir antes de iniciar los contenedores. El archivo `config/odoo.conf` debe ser un archivo válido de configuración de Odoo.

## Requisitos

- Docker Desktop o Docker Engine instalado.
- Docker Compose v2 disponible mediante el comando `docker compose`.
- Recursos suficientes asignados a Docker, especialmente memoria.
- Puertos locales `8069` y `5432` disponibles, si se desea acceder a ambos servicios desde el equipo.
- Archivos `config/odoo.conf` y directorio `addons/` creados.

Verificar las versiones:

```bash
docker --version
docker compose version
```

En Docker Desktop para macOS, los límites de los contenedores también están condicionados por los recursos asignados globalmente a Docker Desktop.

## Servicios

### PostgreSQL — `sass-data-base`

| Propiedad | Valor |
|---|---|
| Imagen | `postgres:16` |
| Nombre del contenedor | `sass-data-base` |
| Base inicial | `postgres` |
| Usuario inicial | `odoo` |
| Puerto interno | `5432` |
| Volumen de datos | `odoo-db-data` |
| Política de reinicio | `unless-stopped` |

Variables de entorno configuradas:

```yaml
POSTGRES_DB: postgres
POSTGRES_USER: odoo
POSTGRES_PASSWORD: odoo
```

Estas variables se utilizan para la inicialización de PostgreSQL cuando el directorio de datos está vacío. **Cambiar estas variables posteriormente no modifica automáticamente las credenciales ni las bases de datos que ya existen en un volumen inicializado.**

La contraseña `odoo` es apropiada únicamente para un entorno local de prueba. Debe cambiarse y gestionarse de forma segura antes de cualquier uso compartido o productivo.

### Odoo — `saas-odoo`

| Propiedad | Valor |
|---|---|
| Imagen | `odoo:18.0` |
| Nombre del contenedor | `saas-odoo` |
| Puerto interno | `8069` |
| Host de PostgreSQL | `sass-data-base` |
| Puerto de PostgreSQL | `5432` |
| Volumen de datos | `odoo-web-data` |
| Addons personalizados | `./addons:/mnt/extra-addons` |
| Configuración | `./config/odoo.conf:/etc/odoo/odoo.conf:ro` |
| Política de reinicio | `unless-stopped` |

Variables de conexión:

```yaml
HOST: sass-data-base
PORT: 5432
USER: odoo
PASSWORD: odoo
```

Odoo utiliza el nombre del servicio de PostgreSQL como host. Ambos servicios se encuentran conectados a la red `saas-network`.

## Recursos y límites

Cada servicio tiene límites definidos mediante `deploy.resources.limits`.

```yaml
deploy:
  resources:
    limits:
      cpus: "2.0"
      memory: 4G
```

Los límites son **individuales por contenedor**:

| Servicio | Máximo de CPU | Máximo de memoria |
|---|---:|---:|
| `sass-data-base` | 2 CPU | 4 GB |
| `saas-odoo` | 2 CPU | 4 GB |
| **Máximo combinado configurado** | **4 CPU** | **8 GB** |

Los límites no reservan esos recursos de forma permanente; establecen el máximo que cada contenedor puede consumir.

En Docker Desktop, la máquina virtual de Docker debe tener recursos globales suficientes para ambos contenedores y para otros procesos que se ejecuten dentro de ella. Si Docker Desktop tiene asignados menos recursos, los límites individuales no podrán aprovecharse plenamente.

## Healthcheck y orden de inicio

PostgreSQL incluye un healthcheck basado en `pg_isready`:

```yaml
healthcheck:
  test:
    - CMD-SHELL
    - pg_isready -U "$${POSTGRES_USER}" -d "$${POSTGRES_DB}"
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 30s
```

Parámetros:

| Parámetro | Significado |
|---|---|
| `test` | Ejecuta `pg_isready` para comprobar que PostgreSQL acepta conexiones. |
| `interval: 10s` | Ejecuta la comprobación cada 10 segundos. |
| `timeout: 5s` | Da hasta 5 segundos para completar cada comprobación. |
| `retries: 5` | Marca el servicio como no saludable tras 5 fallos consecutivos. |
| `start_period: 30s` | Permite un periodo inicial de arranque de 30 segundos. |

El uso de `$$` evita que Docker Compose expanda las variables antes de que el comando se ejecute dentro del contenedor.

Odoo declara:

```yaml
depends_on:
  sass-data-base:
    condition: service_healthy
    restart: true
```

Esto establece que:

1. Compose inicia PostgreSQL.
2. PostgreSQL ejecuta sus comprobaciones de salud.
3. Cuando PostgreSQL se encuentra `healthy`, Compose puede iniciar Odoo.
4. `restart: true` permite que Odoo se reinicie cuando PostgreSQL se reinicia mediante una operación explícita de Compose que activa esta dependencia.

El healthcheck comprueba que PostgreSQL esté aceptando conexiones; no verifica que todas las bases de datos de Odoo, módulos o procesos de negocio estén funcionando correctamente.

## Persistencia de datos

Se utilizan dos volúmenes nombrados:

```yaml
volumes:
  odoo-web-data:
  odoo-db-data:
```

| Volumen | Ruta dentro del contenedor | Uso |
|---|---|---|
| `odoo-db-data` | `/var/lib/postgresql/data` | Archivos de datos de PostgreSQL. |
| `odoo-web-data` | `/var/lib/odoo` | Datos persistentes de Odoo, incluyendo archivos de sesión y otros datos gestionados por la aplicación. |

Los volúmenes sobreviven a la eliminación y recreación de los contenedores.

> No utilizar `docker compose down -v` si se desea conservar la información. La opción `-v` elimina los volúmenes declarados por Compose y puede ocasionar pérdida de datos.

Los módulos personalizados se montan desde el directorio local `addons/`. Los cambios en esos archivos se reflejan en el contenedor, pero puede ser necesario actualizar el módulo o reiniciar Odoo para que los cambios surtan efecto.

## Red y puertos

La red definida es:

```yaml
networks:
  saas-network:
    driver: bridge
```

Los servicios conectados a esta red pueden comunicarse entre sí usando sus nombres DNS de servicio.

### Puertos publicados

| Servicio | Publicación | Acceso |
|---|---|---|
| Odoo | `8069:8069` | `http://localhost:8069` |
| PostgreSQL | `127.0.0.1:5432:5432` | Solo desde el equipo local mediante `localhost:5432` |

PostgreSQL está publicado explícitamente sobre `127.0.0.1`, evitando exponer el puerto en todas las interfaces de red del equipo.

Odoo no necesita el puerto de PostgreSQL publicado para conectarse internamente. La publicación de `5432` se conserva para permitir el uso de herramientas locales de administración de bases de datos.

## Configuración de Odoo

El archivo local:

```text
./config/odoo.conf
```

se monta en:

```text
/etc/odoo/odoo.conf
```

con la opción `:ro`, que significa solo lectura desde el contenedor.

Ejemplo básico de configuración:

```ini
[options]
; La conexión a PostgreSQL se proporciona mediante variables de entorno.
; Mantener aquí las opciones adicionales que requiera el proyecto.

addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
```

Este ejemplo es una base mínima. Si el archivo actual contiene parámetros adicionales —por ejemplo, `dbfilter`, `proxy_mode`, `workers`, `admin_passwd` o rutas de logs—, deben conservarse según las necesidades del entorno.

Los parámetros de conexión de PostgreSQL deben ser coherentes con las variables `HOST`, `PORT`, `USER` y `PASSWORD` definidas en el servicio Odoo.

## Inicio del entorno

Desde la raíz del proyecto:

### 1. Validar el archivo Compose

```bash
docker compose config
```

Este comando interpreta y valida la configuración de Compose. Si hay errores de sintaxis o referencias incorrectas, se deben corregir antes de iniciar los servicios.

### 2. Iniciar los servicios

```bash
docker compose up -d
```

La opción `-d` inicia los contenedores en segundo plano.

### 3. Revisar el estado

```bash
docker compose ps
```

PostgreSQL debe mostrar el estado `healthy` una vez que su healthcheck haya pasado. Odoo debe aparecer como `Up`.

### 4. Abrir Odoo

En el navegador:

```text
http://localhost:8069
```

En el primer inicio, Odoo puede mostrar la pantalla de creación o selección de una base de datos, según el contenido del volumen y la configuración de Odoo.

## Comandos de administración

Los comandos se ejecutan desde el directorio donde se encuentra `compose.yaml`.

### Iniciar

```bash
docker compose up -d
```

### Detener sin eliminar contenedores

```bash
docker compose stop
```

### Iniciar servicios detenidos

```bash
docker compose start
```

### Reiniciar Odoo

```bash
docker compose restart saas-odoo
```

### Reiniciar PostgreSQL

```bash
docker compose restart sass-data-base
```

### Detener y eliminar contenedores y red

```bash
docker compose down
```

Este comando no elimina los volúmenes nombrados, por lo que conserva los datos.

### Ver logs de ambos servicios

```bash
docker compose logs -f
```

### Ver logs de un servicio específico

```bash
docker compose logs -f sass-data-base
```

```bash
docker compose logs -f saas-odoo
```

### Ejecutar un comando dentro de PostgreSQL

```bash
docker compose exec sass-data-base psql -U odoo -d postgres
```

### Ejecutar una consola dentro de Odoo

```bash
docker compose exec saas-odoo bash
```

## Verificación y diagnóstico

### Revisar estado de salud de PostgreSQL

```bash
docker inspect sass-data-base \
  --format '{{json .State.Health}}'
```

Para una salida más legible, se puede utilizar:

```bash
docker inspect sass-data-base \
  --format '{{.State.Health.Status}}'
```

Estados posibles:

- `starting`: el healthcheck aún está en periodo de inicio o no ha pasado.
- `healthy`: la comprobación está pasando.
- `unhealthy`: se han acumulado fallos de comprobación.

### Verificar límites de recursos configurados

Para PostgreSQL:

```bash
docker inspect sass-data-base \
  --format 'RAM={{.HostConfig.Memory}} CPU={{.HostConfig.NanoCpus}}'
```

Para Odoo:

```bash
docker inspect saas-odoo \
  --format 'RAM={{.HostConfig.Memory}} CPU={{.HostConfig.NanoCpus}}'
```

Con los límites de este Compose, los valores esperados son:

```text
RAM=4294967296 CPU=2000000000
```

La memoria se expresa en bytes y `NanoCpus` representa CPU en unidades de mil millones.

### Revisar consumo actual

```bash
docker stats sass-data-base saas-odoo
```

Este comando muestra consumo de CPU, memoria, red y otros datos en tiempo real.

### Revisar los puertos publicados

```bash
docker compose port saas-odoo 8069
```

```bash
docker compose port sass-data-base 5432
```

### Listar volúmenes

```bash
docker volume ls
```

### Inspeccionar un volumen

```bash
docker volume inspect odoo-db-data
```

Compose puede agregar un prefijo basado en el nombre del proyecto a los volúmenes. Si el nombre real difiere, se debe utilizar el nombre mostrado por `docker volume ls`.

## Reconstrucción y actualización

En esta configuración se utilizan imágenes oficiales, no se construye una imagen personalizada mediante un `Dockerfile`.

### Actualizar imágenes

```bash
docker compose pull
```

Luego recrear los contenedores:

```bash
docker compose up -d
```

Este procedimiento puede descargar una versión más reciente de la etiqueta `postgres:16` u `odoo:18.0`.

Antes de actualizar en un entorno importante, se recomienda realizar un respaldo y revisar las notas de la versión.

### Aplicar cambios en addons personalizados

Los addons están montados desde el equipo local. Para aplicar cambios de código:

1. Guardar los archivos modificados en `addons/`.
2. Reiniciar Odoo si los cambios requieren recargar el proceso:

   ```bash
   docker compose restart saas-odoo
   ```

3. Actualizar el módulo desde la interfaz de Odoo o mediante el procedimiento de actualización correspondiente.

Reiniciar el contenedor no actualiza automáticamente la estructura de una base de datos ni ejecuta una actualización de módulos.

### Recrear contenedores

```bash
docker compose up -d --force-recreate
```

Este comando recrea los contenedores, conservando los volúmenes nombrados.

> La recreación de contenedores no equivale a borrar la base de datos. Sin embargo, siempre es recomendable contar con respaldos recientes antes de realizar cambios importantes.

## Respaldo y recuperación

### Crear un respaldo lógico de PostgreSQL

El siguiente comando crea un archivo SQL en el directorio actual del equipo:

```bash
docker compose exec -T sass-data-base \
  pg_dump -U odoo -d postgres \
  > respaldo-postgres.sql
```

Este ejemplo respalda la base `postgres`. En Odoo, cada base de datos de negocio debe respaldarse por separado, y también se deben conservar los archivos asociados de Odoo cuando sean necesarios.

Para listar las bases existentes:

```bash
docker compose exec sass-data-base \
  psql -U odoo -d postgres -c '\l'
```

### Restaurar un respaldo SQL

La restauración debe realizarse sobre la base de datos correcta y, de preferencia, en un entorno detenido o aislado para evitar modificaciones concurrentes.

Ejemplo de restauración en una base existente:

```bash
cat respaldo-postgres.sql | \
  docker compose exec -T sass-data-base \
  psql -U odoo -d postgres
```

Este comando no debe ejecutarse indiscriminadamente sobre una base que contenga información vigente. La restauración puede sobrescribir o duplicar objetos y datos dependiendo del contenido del archivo.

Para un procedimiento de respaldo y recuperación de Odoo completo, se deben contemplar:

- Base de datos PostgreSQL.
- Filestore de Odoo correspondiente a cada base de datos.
- Configuración y addons personalizados.
- Prueba periódica de restauración.

## Seguridad y recomendaciones

1. **Cambiar las credenciales de ejemplo.** `POSTGRES_PASSWORD: odoo` no debe utilizarse en producción.
2. **No publicar PostgreSQL en todas las interfaces.** La publicación actual está restringida a `127.0.0.1`.
3. **Proteger el archivo de configuración.** Revisar permisos y evitar subir secretos al repositorio.
4. **No versionar respaldos ni datos de clientes.** Utilizar reglas apropiadas en `.gitignore`.
5. **Fijar versiones para entornos estables.** Las etiquetas `postgres:16` y `odoo:18.0` pueden recibir actualizaciones.
6. **Respaldar antes de actualizar.** Una actualización de imagen no sustituye un respaldo.
7. **Supervisar el consumo.** Los límites de Docker no reemplazan la configuración de workers, memoria y procesos de Odoo.
8. **No eliminar volúmenes por accidente.** Evitar `docker compose down -v` cuando se necesite conservar los datos.
9. **Evaluar el acceso a Odoo.** Para exposición externa se requiere revisar HTTPS, proxy inverso, `proxy_mode`, políticas de acceso y configuración de seguridad.
10. **Validar los respaldos.** Un archivo generado no garantiza por sí solo que la recuperación sea correcta; realizar pruebas de restauración.

## Solución de problemas

### Odoo no inicia porque PostgreSQL no está saludable

Revisar:

```bash
docker compose ps
docker compose logs sass-data-base
```

Comprobar manualmente:

```bash
docker compose exec sass-data-base \
  pg_isready -U odoo -d postgres
```

Verificar que Docker tenga recursos suficientes y que el volumen de PostgreSQL no esté dañado.

### Odoo no puede conectarse a PostgreSQL

Confirmar que las variables de entorno de Odoo apunten al servicio correcto:

```yaml
HOST: sass-data-base
PORT: 5432
USER: odoo
PASSWORD: odoo
```

No usar `localhost` como host de PostgreSQL dentro del contenedor Odoo.

Revisar también los logs:

```bash
docker compose logs --tail=100 saas-odoo
docker compose logs --tail=100 sass-data-base
```

### El puerto 5432 ya está ocupado

Si otro PostgreSQL se encuentra ejecutándose localmente, puede impedir la publicación del puerto.

Consultar procesos o contenedores que lo utilizan. Si no se necesita conexión directa desde el equipo, se puede eliminar la sección `ports` de PostgreSQL: Odoo seguirá conectándose por la red privada de Compose.

### Los cambios de un addon no aparecen

Verificar el montaje:

```bash
docker compose exec saas-odoo \
  ls -la /mnt/extra-addons
```

Después, reiniciar Odoo si es necesario y actualizar el módulo desde la interfaz o mediante el procedimiento correspondiente.

### Se perdió la base de datos al recrear el entorno

Revisar si se eliminó el volumen o si se cambió el nombre del proyecto Compose, lo cual puede generar volúmenes con prefijos diferentes.

Listar volúmenes:

```bash
docker volume ls
```

No crear una base nueva ni eliminar volúmenes adicionales hasta identificar dónde se encuentran los datos originales.

---

## Referencias oficiales

- [Docker Compose — documentación](https://docs.docker.com/compose/)
- [Docker Compose — orden de inicio y dependencias](https://docs.docker.com/compose/how-tos/startup-order/)
- [Docker Compose — especificación de despliegue y recursos](https://docs.docker.com/reference/compose-file/deploy/)
- [Docker — volúmenes](https://docs.docker.com/engine/storage/volumes/)
- [Imagen oficial de PostgreSQL](https://hub.docker.com/_/postgres)
- [Imagen oficial de Odoo](https://hub.docker.com/_/odoo)

## Para casos especiales
### Para eliminar los assets despues de cargar una copia de la bd y obligar a odoo a generarlos nuevamente
DELETE FROM ir_attachment
WHERE url LIKE '/web/assets/%';

DELETE FROM ir_attachment
WHERE name LIKE 'assets_%';
## Seguir trabajando en otra máquina

El proyecto se mueve en un zip que incluye el código, el historial de git, `.env`, `CREDENCIALES.md`
y un respaldo de los datos en `backups/<fecha>/` (una base `.dump` por restaurante y `filestore.tar.gz`).

```bash
unzip saas-odoo-<fecha>.zip && cd saas-odoo
scripts/restore.sh backups/<fecha>      # crea los volumenes, restaura las bases y los archivos, y levanta todo
docker compose ps
```

Luego abre `http://laguapa.localhost` (y los demás tenants de `TENANT_HOSTS`). El backend del
administrador está en `http://<tenant>.localhost/admin-<ADMIN_KEY>` (ver `.env`).

Para llevar los datos actualizados de vuelta: `scripts/backup.sh` y copia la carpeta nueva de `backups/`.

### Módulos y scripts propios

| Ruta | Para qué |
|---|---|
| `addons/pos_role_policy` | Roles Mesero / Cajero / Gerente en el POS (genérico, sirve para cualquier tenant) |
| `addons/laguapa_branding` | Marca La Guapa: login, POS y autopedido QR; oculta la marca Odoo |
| `scripts/create-tenant.sh` | Crea un restaurante nuevo (base de datos = subdominio) |
| `scripts/load_laguapa.py` | Carga logo y carta de La Guapa |
| `scripts/configure_laguapa_pos.py` | Pagos, propina, mesas, empleados/PIN, autopedido (re-ejecutable) |
| `scripts/backup.sh` / `scripts/restore.sh` | Respaldo y restauración de todas las bases + archivos |

Al editar `config/Caddyfile` usa `docker compose up -d --force-recreate caddy` (el `reload` no ve el archivo nuevo).
