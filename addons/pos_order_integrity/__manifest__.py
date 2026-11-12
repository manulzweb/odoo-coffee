{
    "name": "Punto de venta: integridad de pedidos",
    "version": "18.0.2.1.0",
    "category": "Sales/Point of Sale",
    "summary": "Controles de servidor para el cajero, modos de venta, costo manual y auditoria",
    "license": "LGPL-3",
    # Dependencias reales de Odoo 18: point_of_sale (modelos pos.*), product
    # (product.template, precision decimal) y uom (categorias kg/unidad).
    "depends": ["point_of_sale", "product", "uom"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "data/decimal_precision.xml",
        "data/uom_rounding.xml",
        "views/product_template_views.xml",
        "views/pos_audit_views.xml",
    ],
    "application": False,
    # Honesto: se mantiene NO instalable. Nada de este modulo se ha instalado ni
    # ejecutado en Odoo 18 (analisis estatico solamente) y hay TODO-VERIFICAR
    # abiertos en codigo y vistas. Este manifest es un archivo compartido y el
    # compose principal monta ./addons en lectura/escritura: NO cambiar este valor
    # aqui. Para probar, trabajar con una COPIA de addons/ en el entorno aislado
    # (ver README) y alli poner True.
    "installable": False,
}
