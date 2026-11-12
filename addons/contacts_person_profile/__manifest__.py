{
    "name": "Contacts Person Profile",
    "author": "David Martinez",
    "category": "CSPI",
    "version": "18.0.1.0.0",
    "summary": "Campos adicionales para contactos tipo persona",
    "depends": ["contacts"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_partner_views.xml",
        "views/contact_role_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
}
