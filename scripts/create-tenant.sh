#!/usr/bin/env bash
# Uso: scripts/create-tenant.sh <nombre-tenant> ["Nombre del restaurante"]
# Crea la base de datos <nombre-tenant> (= subdominio) con POS de restaurante y
# localizacion colombiana. Imprime la clave generada del administrador.
set -euo pipefail
cd "$(dirname "$0")/.."

TENANT="${1:?Uso: $0 <tenant> [\"Nombre del restaurante\"]}"
NAME="${2:-$TENANT}"
[[ "$TENANT" =~ ^[a-z][a-z0-9_]{1,30}$ ]] || { echo "Tenant invalido: solo a-z, 0-9 y _ (empieza con letra)"; exit 1; }

ODOO="docker compose run --rm -T saas-odoo odoo --no-http --workers=0 --max-cron-threads=0 --stop-after-init -d $TENANT"

echo ">> [1/3] Creando base '$TENANT' (base + contabilidad)..."
$ODOO -i base --without-demo=all --load-language=es_CO

echo ">> [2/3] Configurando empresa (Colombia / COP) y clave de administrador..."
PASS="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-20)"
docker compose run --rm -T saas-odoo odoo shell --no-http --workers=0 -d "$TENANT" <<PY
company = env.company
company.write({
    'name': """$NAME""",
    'country_id': env.ref('base.co').id,
    'currency_id': env.ref('base.COP').id,
})
env.ref('base.COP').active = True
admin = env.ref('base.user_admin')
admin.write({'password': '$PASS', 'lang': 'es_CO', 'tz': 'America/Bogota'})
env.cr.commit()
PY

echo ">> [3/3] Instalando POS restaurante + localizacion Colombia..."
$ODOO -i point_of_sale,pos_restaurant,l10n_co

echo
echo "=============================================="
echo " Tenant listo: $TENANT"
echo " Usuario:      admin"
echo " Clave:        $PASS      (guardala ya, no se vuelve a mostrar)"
echo " Recuerda agregar el host a TENANT_HOSTS en .env y: docker compose up -d caddy"
echo "=============================================="
