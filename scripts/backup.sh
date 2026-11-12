#!/usr/bin/env bash
# Respaldo de todas las bases (dump) + filestore. Uso: scripts/backup.sh
# Programar en el host:  0 4 * * *  /ruta/al/proyecto/scripts/backup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="backups/$STAMP"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
mkdir -p "$DEST"

DBS=$(docker exec "$POSTGRES_CONTAINER_NAME" psql -U "$POSTGRES_USER" -d postgres -Atc \
  "SELECT datname FROM pg_database WHERE datistemplate = false AND datname <> 'postgres'")

for db in $DBS; do
  echo ">> dump $db"
  docker exec "$POSTGRES_CONTAINER_NAME" pg_dump -U "$POSTGRES_USER" -Fc "$db" > "$DEST/$db.dump"
done

echo ">> filestore"
docker run --rm -v "${COMPOSE_PROJECT_NAME}_saas-odoo-web-data:/data:ro" -v "$PWD/$DEST:/out" \
  alpine tar czf /out/filestore.tar.gz -C /data .

find backups -mindepth 1 -maxdepth 1 -type d -mtime +"$KEEP_DAYS" -exec rm -rf {} +
echo "Listo: $DEST  (copialo FUERA del servidor: rclone/rsync a S3, Backblaze, etc.)"
