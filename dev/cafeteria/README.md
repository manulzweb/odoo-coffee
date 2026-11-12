# Entorno aislado para pruebas de cafetería

Este entorno es exclusivamente para desarrollo local con datos ficticios. Usa un proyecto Compose separado, PostgreSQL y almacenamiento propios, y publica Odoo solo en `127.0.0.1:18069`. Las credenciales del archivo son públicas y exclusivamente de prueba. No usar con información real ni exponerlo a Internet.

Antes de iniciarlo, recuperar el acceso autorizado al motor Docker. Comprobar `docker compose ps`, `docker ps -a`, `docker image ls` y `docker volume ls` sin eliminar ni modificar recursos. Comprobar que el nombre de proyecto `cafeteria-dev` y el puerto 18069 no están en uso; si el nombre ya existe, investigar su origen y usar otro nombre de proyecto nuevo de manera consistente. La configuración existente del proyecto principal no se ejecuta ni se comparte intencionalmente.

Desde la raíz del repositorio:

```powershell
docker compose -p cafeteria-dev -f dev/cafeteria/compose.yml config --quiet
docker compose -p cafeteria-dev -f dev/cafeteria/compose.yml up -d
docker compose -p cafeteria-dev -f dev/cafeteria/compose.yml ps
```

Abrir http://localhost:18069 y crear una base de pruebas con datos ficticios. El gestor de bases y sus credenciales no están endurecidos para producción. El directorio de módulos se monta en solo lectura: no instalar `pos_order_integrity`, que sigue siendo un prototipo incompleto. Identificar la edición y módulos instalados antes de probar las funciones nativas.

Para detener los servicios sin borrar datos:

```powershell
docker compose -p cafeteria-dev -f dev/cafeteria/compose.yml stop
```

No ejecutar `down -v`, `volume prune` ni borrar volúmenes sin identificar su contenido y confirmar que se pueden descartar. Este archivo no demuestra aislamiento efectivo ni funcionamiento hasta que se pruebe con Docker; tampoco constituye una configuración de producción o respaldo.
