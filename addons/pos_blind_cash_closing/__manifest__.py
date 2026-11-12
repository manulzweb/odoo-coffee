{
    "name": "Punto de venta: cierre de caja ciego",
    "version": "18.0.1.0.0",
    "category": "Sales/Point of Sale",
    "summary": "Cierre de caja ciego del lado servidor: el cajero cuenta, el servidor calcula la diferencia",
    "license": "LGPL-3",
    # DEPENDENCIA: los grupos (cajero restringido, gerente de la cafeteria) los
    # define el modulo pos_order_integrity (otro agente). Aqui solo se referencian
    # sus ids XML: pos_order_integrity.group_pos_store_manager y
    # pos_order_integrity.group_cashier_restricted. Este modulo NO los redefine.
    "depends": ["point_of_sale", "pos_order_integrity"],
    "data": [
        "security/ir.model.access.csv",
        "security/security_rules.xml",
        "views/cash_closing_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "application": False,
    # Honesto: analisis estatico solamente; nada se ha instalado ni ejecutado en
    # Odoo 18 y hay TODO-VERIFICAR abiertos (ver README). Ademas depende de
    # pos_order_integrity, que tambien es no instalable. Poner True solo en una
    # base aislada de pruebas, tras revisar el README y ejecutar tests/.
    "installable": False,
}
