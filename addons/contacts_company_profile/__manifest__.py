{
    "name": "Contacts Company Profile Extension",
    "summary": "Extensión de contactos para perfilamiento empresarial",
    "description": """
Extiende contactos para agregar información empresarial avanzada.
Solo aplica cuando el contacto es tipo compañía.
    """,
    "author": "David Martinez",
    "category": "CSPI",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "depends": [
        "contacts",
        "mail",
        "social_network_base",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/catalogs_views.xml",
        "views/res_partner_views.xml",
        "views/res_partner_social_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
}