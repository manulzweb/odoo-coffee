from odoo import api, fields, models

POS_ROLES = [
    ("mesero", "Mesero"),
    ("cajero", "Cajero"),
    ("gerente", "Gerente"),
]


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    pos_role = fields.Selection(
        POS_ROLES,
        string="Rol en el POS",
        default="cajero",
        required=True,
        help="Mesero: toma pedidos, no cobra.\n"
        "Cajero: cobra y cierra caja.\n"
        "Gerente: descuentos, precios, reembolsos y anulaciones.",
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ["pos_role"]

    def _load_pos_data(self, data):
        res = super()._load_pos_data(data)
        for emp in res["data"]:
            # El rol del POS manda sobre las listas basico/avanzado de pos_hr.
            # Un usuario Odoo con permiso de Gerente de POS sigue siendo gerente.
            if emp.get("_user_role") == "admin" or emp.get("pos_role") == "gerente":
                emp["_role"] = "manager"
                emp["pos_role"] = "gerente"
            else:
                emp["_role"] = "cashier"
        return res
