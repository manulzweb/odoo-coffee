{
    "name": "POS Role Policy",
    "summary": "Roles de Mesero, Cajero y Gerente en el Punto de Venta (multi-tenant)",
    "description": """
Asigna a cada empleado un rol en el POS y aplica permisos en la interfaz:

* Mesero: toma pedidos, los envia a cocina, mueve y divide mesas. No cobra.
* Cajero: lo del mesero + cobrar, imprimir cuenta y cerrar caja.
* Gerente: todo (descuentos, cambio de precio, reembolsos, eliminar pedidos,
  entradas/salidas de efectivo).
""",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "category": "Sales/Point of Sale",
    "depends": ["pos_hr", "pos_restaurant"],
    "data": ["views/hr_employee_views.xml"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_role_policy/static/src/**/*",
        ],
    },
    "installable": True,
}
