from odoo import _, api, fields, models
from odoo.exceptions import AccessError

from .guard import dump_detail


class PosOrderAuditLog(models.Model):
    """Registro inmutable de devoluciones, correcciones y cancelaciones.

    Autor y fecha se guardan en campos propios (ademas de create_uid/create_date).
    Se crea solo desde codigo del servidor (sudo); nadie tiene permiso de
    escritura ni de borrado por ACL.
    """
    _name = "pos.order.audit.log"
    _description = "Auditoria de devoluciones y correcciones de ventas"
    _order = "date desc, id desc"

    order_id = fields.Many2one("pos.order", string="Venta", required=True,
                               index=True, ondelete="restrict", readonly=True)
    action = fields.Selection(
        [("refund", "Devolucion"), ("correction", "Correccion"), ("cancel", "Cancelacion")],
        required=True, readonly=True)
    user_id = fields.Many2one("res.users", string="Autor", required=True, readonly=True)
    date = fields.Datetime(string="Fecha", required=True, readonly=True)
    reason = fields.Text(string="Motivo (opcional)", readonly=True)
    detail = fields.Text(string="Detalle (JSON)", readonly=True)

    @api.model
    def _pos_log(self, action, order, payload):
        # El motivo es texto libre tomado del contexto; NO autoriza nada, por lo
        # que no importa que el cliente controle el contexto.
        reason = (self.env.context.get("pos_audit_reason") or "").strip() or False
        return self.sudo().create({
            "order_id": order.id,
            "action": action,
            "user_id": self.env.user.id,  # sudo() conserva el uid real
            "date": fields.Datetime.now(),
            "reason": reason,
            "detail": dump_detail(payload),
        })

    def write(self, vals):
        if not self.env.su:
            raise AccessError(_("El registro de auditoria no se puede modificar."))
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            raise AccessError(_("El registro de auditoria no se puede eliminar."))
        return super().unlink()
