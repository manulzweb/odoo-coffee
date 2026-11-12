{
    "name": "La Guapa Branding",
    "summary": "Marca La Guapa en login, POS y autopedido (QR); oculta la marca Odoo",
    "version": "18.0.1.2.0",
    "license": "LGPL-3",
    "category": "Tools",
    "depends": ["web", "point_of_sale", "pos_self_order"],
    "data": ["views/templates.xml"],
    "assets": {
        # Variables de marca antes que las de Odoo/Bootstrap
        "pos_self_order.assets": [
            ("prepend", "laguapa_branding/static/src/self_order/brand_variables.scss"),
            "laguapa_branding/static/src/self_order/theme.scss",
            "laguapa_branding/static/src/self_order/landing_page.xml",
            "laguapa_branding/static/src/self_order/product_card.js",
            "laguapa_branding/static/src/self_order/currency.js",
            "laguapa_branding/static/src/self_order/product_card.xml",
        ],
        "point_of_sale._assets_pos": [
            ("prepend", "laguapa_branding/static/src/pos/pos_variables.scss"),
            "laguapa_branding/static/src/pos/pos_theme.scss",
        ],
    },
    "installable": True,
}
