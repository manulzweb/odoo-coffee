from odoo import _, api, models
from odoo.exceptions import AccessError

from . import blind_common as bc


class ReportSaleDetails(models.AbstractModel):
    """Informe nativo 'Detalles de ventas': devuelve totales, pagos por medio y
    productos de cualquier sesion; es un metodo RPC publico y el POS lo ofrece
    en su interfaz. Se bloquea para todo usuario no gerente.

    TODO-VERIFICAR (Odoo 18): el modelo abstracto
    'report.point_of_sale.report_saledetails' y el metodo get_sale_details; si
    el nombre es otro, _inherit falla al instalar (error ruidoso, no silencioso).
    """
    _inherit = "report.point_of_sale.report_saledetails"

    @api.model
    def get_sale_details(self, *args, **kwargs):
        if bc.is_blind(self.env):
            raise AccessError(_("Operacion no permitida."))
        return super().get_sale_details(*args, **kwargs)

    @api.model
    def _get_report_values(self, docids, data=None):
        if bc.is_blind(self.env):
            raise AccessError(_("Operacion no permitida."))
        return super()._get_report_values(docids, data=data)
