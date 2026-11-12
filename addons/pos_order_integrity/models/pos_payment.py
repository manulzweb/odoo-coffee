from odoo import api, models, _
from odoo.exceptions import AccessError
from odoo.tools import float_compare

from .guard import check_numeric_vals, is_cash_method, is_restricted, read_before

# TODO-VERIFICAR (Odoo 18): nombres pos.payment: pos_order_id, amount,
# payment_method_id, is_change (linea de cambio que _process_payment_lines
# agrega con monto negativo y el metodo de efectivo de la caja), session_id.
PAYMENT_VALIDATED_FIELDS = frozenset({"pos_order_id", "amount", "payment_method_id", "is_change"})
PAYMENT_AUDIT_FIELDS = ("pos_order_id", "amount", "payment_method_id")


class PosPayment(models.Model):
    _inherit = "pos.payment"

    def _pos_is_change(self):
        self.ensure_one()
        return "is_change" in self._fields and bool(self.is_change)

    def _pos_validate_restricted(self):
        """Un pago fabricado (monto negativo, metodo ajeno a la caja, orden ya
        confirmada) es la via para marcar como pagada una venta que no se cobro."""
        for pay in self:
            order = pay.pos_order_id
            if not order or order.state != "draft":
                raise AccessError(_("Solo se registran pagos en ventas en borrador."))
            if pay.payment_method_id not in order.config_id.payment_method_ids:
                raise AccessError(_("El metodo de pago no pertenece a la caja de la venta."))
            rounding = (order.currency_id or order.company_id.currency_id).rounding
            negative = float_compare(pay.amount, 0.0, precision_rounding=rounding) <= 0
            if pay._pos_is_change():
                # Unica excepcion: la linea nativa de cambio (negativa, en efectivo).
                if not negative or not is_cash_method(pay.payment_method_id):
                    raise AccessError(_("Linea de cambio no valida."))
            elif negative:
                raise AccessError(_("El monto de un pago debe ser positivo."))

    @api.model_create_multi
    def create(self, vals_list):
        restricted = is_restricted(self.env)
        for vals in vals_list:
            check_numeric_vals(vals, ("amount",))
            if restricted:
                order = self.env["pos.order"].browse(vals.get("pos_order_id")).exists()
                if not order or order.state != "draft":
                    raise AccessError(_("Solo se registran pagos en ventas en borrador."))
        payments = super().create(vals_list)
        if restricted:
            payments._pos_validate_restricted()
        elif not self.env.su:
            for order in payments.pos_order_id.filtered(lambda o: o.state != "draft"):
                self.env["pos.order.audit.log"]._pos_log(
                    "correction", order,
                    {"pagos_creados": payments.filtered(lambda p: p.pos_order_id == order).ids})
        return payments

    def write(self, vals):
        restricted = is_restricted(self.env)
        check_numeric_vals(vals, ("amount",))
        audit = None
        if restricted:
            if any(p.pos_order_id.state != "draft" for p in self):
                raise AccessError(_("Solo el gerente puede modificar pagos de ventas confirmadas."))
            if vals.get("pos_order_id"):
                order = self.env["pos.order"].browse(vals["pos_order_id"]).exists()
                if not order or order.state != "draft":
                    raise AccessError(_("Solo se registran pagos en ventas en borrador."))
        elif not self.env.su:
            confirmed = self.filtered(lambda p: p.pos_order_id.state != "draft")
            if confirmed:
                audit = (confirmed, read_before(confirmed, list(PAYMENT_AUDIT_FIELDS)))
        res = super().write(vals)
        if restricted and (PAYMENT_VALIDATED_FIELDS & set(vals)):
            self._pos_validate_restricted()
        if audit:
            confirmed, before = audit
            for order in confirmed.pos_order_id:
                ids = confirmed.filtered(lambda p: p.pos_order_id == order).ids
                self.env["pos.order.audit.log"]._pos_log("correction", order, {
                    "pagos": ids, "antes": {str(i): before.get(str(i)) for i in ids},
                    "despues": vals})
        return res

    def unlink(self):
        restricted = is_restricted(self.env)
        if restricted and any(p.pos_order_id.state != "draft" for p in self):
            raise AccessError(_("Solo el gerente puede eliminar pagos de ventas confirmadas."))
        confirmed = self.filtered(lambda p: p.pos_order_id.state != "draft")
        if confirmed and not restricted and not self.env.su:
            before = read_before(confirmed, list(PAYMENT_AUDIT_FIELDS))
            for order in confirmed.pos_order_id:
                ids = confirmed.filtered(lambda p: p.pos_order_id == order).ids
                self.env["pos.order.audit.log"]._pos_log("correction", order, {
                    "pagos_eliminados": {str(i): before.get(str(i)) for i in ids}})
        return super().unlink()
