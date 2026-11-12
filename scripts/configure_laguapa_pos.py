# Configura el POS de La Guapa: roles, pagos, propina, mesas, recibo y autopedido.
# Se ejecuta DENTRO del contenedor (requiere los modulos pos_hr, pos_role_policy y laguapa_branding):
#   docker compose run --rm -T saas-odoo odoo shell --no-http --workers=0 -d laguapa < scripts/configure_laguapa_pos.py
# Re-ejecutable: no duplica registros. Imprime los PIN solo cuando los crea.
import secrets

cfg = env["pos.config"].search([], limit=1)
company = env.company

# --- 0. La configuracion del POS no se puede editar con una caja abierta
open_sessions = env["pos.session"].search([("config_id", "=", cfg.id), ("state", "!=", "closed")])
busy = open_sessions.filtered(lambda s: s.state != "opening_control" or s.order_ids)
if busy:
    raise SystemExit("Hay una caja abierta con pedidos (%s). Cierrala y vuelve a ejecutar." % ", ".join(busy.mapped("name")))
open_sessions.unlink()  # solo sesiones vacias en 'control de apertura'

# --- 1. Metodos de pago locales
card = env["pos.payment.method"].search([("name", "=", "Tarjeta")], limit=1)
methods = env["pos.payment.method"]
for name in ["Efectivo", "Tarjeta", "Nequi", "Daviplata", "Transferencia Bancolombia"]:
    pm = env["pos.payment.method"].search([("name", "=", name)], limit=1)
    if not pm:
        pm = env["pos.payment.method"].create({"name": name, "journal_id": card.journal_id.id, "company_id": company.id})
    methods |= pm

# --- 2. Configuracion general del POS
cfg.write({
    "name": "La Guapa",
    "payment_method_ids": [(6, 0, methods.ids)],
    # Propina voluntaria (se agrega en la pantalla de pago)
    "iface_tipproduct": True,
    # Permisos: el rol de cada empleado (pos_role_policy) decide quien hace que
    "module_pos_hr": True,
    "manual_discount": True,
    "restrict_price_control": True,
    # Restaurante
    "iface_printbill": True,
    "iface_splitbill": True,
    # Recibo
    "is_header_or_footer": True,
    "receipt_header": "LA GUAPA\nArt based bar & restaurant\nBarranquilla, Atlántico",
    "receipt_footer": "¡Gracias por visitarnos!\nLa propina es voluntaria.\nIG: @laguapabaq",
})
tip = cfg.tip_product_id or env.ref("point_of_sale.product_product_tip", raise_if_not_found=False)
if not tip:
    tip = env["product.product"].search([("name", "=", "Propina voluntaria")], limit=1) or env["product.product"].create(
        {"name": "Propina voluntaria", "type": "service", "list_price": 0}
    )
tip.write({"name": "Propina voluntaria", "taxes_id": [(5, 0, 0)]})
cfg.tip_product_id = tip

# --- 3. Pisos y mesas
for old, new in [("Main Floor", "Salón"), ("Patio", "Terraza")]:
    floor = env["restaurant.floor"].search([("name", "=", old)])
    if floor:
        floor.name = new
# Sin el plano de demostracion de Odoo: fondo crema y mesas color menta
floors = env["restaurant.floor"].search([("pos_config_ids", "in", cfg.ids)])
floors.write({"floor_background_image": False, "background_color": "rgb(246,242,233)"})
floors.table_ids.write({"color": "#bbfee8"})

# --- 4. Empleados y roles (PIN de 4 digitos para entrar al POS)
users = {u.login: u for u in env["res.users"].search([("login", "in", ["gerente", "cajero", "mesero"])])}
# Abrir/cerrar caja publica un mensaje a nombre del usuario: necesita un correo de remitente
for login, user in users.items():
    if not user.email:
        user.email = "%s@laguapa.local" % login
STAFF = [
    # nombre,        rol,       usuario Odoo vinculado
    ("Gerente",      "gerente", "gerente"),
    ("Cajero",       "cajero",  "cajero"),
    ("Mesero 1",     "mesero",  "mesero"),
    ("Mesero 2",     "mesero",  None),
]
Emp = env["hr.employee"]
staff = Emp
for name, role, login in STAFF:
    emp = Emp.search([("name", "=", name)], limit=1)
    vals = {"pos_role": role, "company_id": company.id}
    if login and login in users:
        vals["user_id"] = users[login].id
    if not emp:
        vals.update({"name": name, "pin": "".join(secrets.choice("0123456789") for _ in range(4))})
        emp = Emp.create(vals)
        print("PIN  %-10s (%s): %s" % (name, role, emp.pin))
    else:
        emp.write(vals)
    staff |= emp

cfg.write({
    "basic_employee_ids": [(6, 0, staff.filtered(lambda e: e.pos_role != "gerente").ids)],
    "advanced_employee_ids": [(6, 0, staff.filtered(lambda e: e.pos_role == "gerente").ids)],
})

# --- 5. Autopedido por QR en la mesa
es = env["res.lang"].search([("code", "=", "es_CO")], limit=1)
cfg.write({
    "self_ordering_mode": "mobile",
    "self_ordering_service_mode": "table",
    "self_ordering_pay_after": "meal",  # se paga al final con el mesero
    "self_ordering_takeaway": False,
    "self_ordering_default_language_id": es.id,
    "self_ordering_available_language_ids": [(6, 0, es.ids)],
    "self_ordering_image_brand": company.logo,
    "self_ordering_image_brand_name": "La Guapa",
    "self_ordering_image_home_ids": [(5, 0, 0)],  # usamos la portada de marca
})
for link in env["pos_self_order.custom_link"].search([("pos_config_ids", "in", cfg.ids)]):
    if link.url.endswith("/products"):
        link.write({"name": "Ver la carta y pedir", "style": "primary"})

# --- 6. Carta: descripcion publica e imagen de cada categoria
products = env["product.template"].search([("available_in_pos", "=", True)])
products.write({"color": 0})  # tarjetas sin foto en blanco, no en pastel aleatorio
for p in products:
    if p.description_sale and not p.public_description:
        p.public_description = "<p>%s</p>" % p.description_sale
# Categorias de demostracion de Odoo ("Food", "Drinks") que ya no usa ningun producto de la carta
for categ in env["pos.category"].search([("name", "in", ["Food", "Drinks"])]):
    if not products.filtered(lambda p: categ in p.pos_categ_ids):
        categ.unlink()
for categ in env["pos.category"].search([]):
    categ.color = 0  # sin los colores pastel aleatorios
    if not categ.image_128:
        with_img = products.filtered(lambda p: categ in p.pos_categ_ids and p.image_256)[:1]
        if with_img:
            categ.image_128 = with_img.image_256  # el campo redimensiona a 128px

# --- 7. Solo el administrador de la plataforma ve las demas aplicaciones
admin_group = env.ref("base.group_system")
pos_menu = env.ref("point_of_sale.menu_point_root")
roots = env["ir.ui.menu"].sudo().search([("parent_id", "=", False), ("id", "!=", pos_menu.id)])
roots.write({"groups_id": [(6, 0, admin_group.ids)]})

env.cr.commit()
print("OK  POS: %s | pagos: %s | propina: %s" % (cfg.name, ", ".join(cfg.payment_method_ids.mapped("name")), cfg.tip_product_id.name))
print("OK  roles:", [(e.name, e.pos_role) for e in staff])
print("OK  pisos:", [(f.name, len(f.table_ids)) for f in env["restaurant.floor"].search([])])
print("OK  autopedido:", cfg.self_ordering_url)
