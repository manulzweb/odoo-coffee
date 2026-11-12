#!/usr/bin/env bash
# Restaura un respaldo hecho con scripts/backup.sh (todas las bases + filestore).
# Uso: scripts/restore.sh backups/<fecha>
# OJO: reemplaza las bases de datos y los archivos actuales por los del respaldo.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

SRC="${1:?Uso: $0 backups/<fecha>}"
[ -d "$SRC" ] || { echo "No existe: $SRC"; exit 1; }
ls "$SRC"/*.dump >/dev/null 2>&1 || { echo "No hay archivos .dump en $SRC"; exit 1; }

read -r -p "Esto REEMPLAZA las bases y archivos actuales por los de $SRC. ¿Continuar? [s/N] " ok
[[ "$ok" =~ ^[sS]$ ]] || { echo "Cancelado."; exit 1; }

echo ">> Creando contenedores y volumenes (sin arrancar Odoo)"
docker compose create
docker compose stop saas-odoo caddy >/dev/null 2>&1 || true

echo ">> Arrancando PostgreSQL"
docker compose up -d sass-data-base
until docker exec "$POSTGRES_CONTAINER_NAME" pg_isready -U "$POSTGRES_USER" -d postgres >/dev/null 2>&1; do sleep 2; done

for dump in "$SRC"/*.dump; do
  db="$(basename "$dump" .dump)"
  echo ">> Restaurando base '$db'"
  docker exec "$POSTGRES_CONTAINER_NAME" psql -U "$POSTGRES_USER" -d postgres -qc \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$db' AND pid <> pg_backend_pid();" >/dev/null
  docker exec "$POSTGRES_CONTAINER_NAME" dropdb -U "$POSTGRES_USER" --if-exists "$db"
  docker exec "$POSTGRES_CONTAINER_NAME" createdb -U "$POSTGRES_USER" "$db"
  docker exec -i "$POSTGRES_CONTAINER_NAME" pg_restore -U "$POSTGRES_USER" -d "$db" --no-owner --role="$POSTGRES_USER" < "$dump"
done

if [ -f "$SRC/filestore.tar.gz" ]; then
  echo ">> Restaurando archivos de Odoo (filestore)"
  docker run --rm -v "${COMPOSE_PROJECT_NAME}_saas-odoo-web-data:/data" -v "$PWD/$SRC:/in:ro" \
    alpine sh -c "rm -rf /data/* && tar xzpf /in/filestore.tar.gz -C /data && chown -R 100:101 /data"
fi

echo ">> Levantando todo"
docker compose up -d
echo "Listo. Revisa: docker compose ps"
