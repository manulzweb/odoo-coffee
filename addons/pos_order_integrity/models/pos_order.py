from odoo import api, models, _
from odoo.exceptions import AccessError
from odoo.tools import float_compare

from .guard import cash_methods, check_numeric_vals, is_cash_method, is_restricted, read_before

# Campos de pos.order que el flujo normal de Odoo toca despues de confirmar.
# Hipotesis a verificar con una venta real completa (impresion, cierre, factura).
# TODO-VERIFICAR (Odoo 18): lista completa; si falta alguno, el cierre o el pago
# fallaran para el cajero con "Solo el gerente puede modificar ventas confirmadas".
ORDER_SYSTEM_FIELDS = frozenset({"nb_print", "account_move", "session_move_id"})
ORDER_AMOUNT_FIELDS = frozenset({"amount_total", "amount_tax", "amount_paid", "amount_return"})
# Transiciones de estado que el cajero puede provocar sin ser gerente.
ORDER_ALLOWED_TRANSITIONS = frozenset({
    ("paid", "done"), ("paid", "invoiced"), ("invoiced", "done"),
})
CONFIRMING_STATES = ("paid", "done", "invoiced")
# Estados con los que un cajero puede crear una venta.
# TODO-VERIFICAR (Odoo 18): si sync_from_ui/_process_order crea el pedido ya en
# 'paid', hay que anadir 'paid' aqui (los controles de linea y de totales siguen).
ORDER_CREATE_STATES = ("draft",)


class PosOrder(models.Model):
    _inherit = "pos.order"

    # ------------------------------------------------------------------
    def _pos_currency(self):
        self.ensure_one()
        return self.currency_id or self.company_id.currency_id

    def _pos_rounding_tolerance(self):
        """Tolerancia por redondeo de efectivo de la caja (0 si no se usa)."""
        self.ensure_one()
        config = self.config_id
        # TODO-VERIFICAR nombres cash_rounding / rounding_method en 18.
        if "cash_rounding" in config._fields and config.cash_rounding and config.rounding_method:
            return config.rounding_method.rounding
        return 0.0

    def _pos_check_totals(self):
        """El total no puede venir distinto de la suma de las lineas (amount_*
        pueden ser datos del cliente; TODO-VERIFICAR si en 18 se calculan).
        Se evalua TAMBIEN para pedidos sin lineas (esperado 0), y el total
        nunca puede ser negativo."""
        for order in self:
            currency = order._pos_currency()
            if float_compare(order.amount_total, 0.0, precision_rounding=currency.rounding) < 0:
                raise AccessError(_("El total de la venta no puede ser negativo."))
            expected = sum(order.lines.mapped("price_subtotal_incl"))
            diff = abs(order.amount_total - expected)
            if float_compare(diff, order._pos_rounding_tolerance(),
                             precision_rounding=currency.rounding) > 0:
                raise AccessError(_("El total de la venta no coincide con la suma de sus lineas."))

    def _pos_check_pricing_context(self):
        """Tarifa e impuestos no pueden ser elegidos por el cliente: la tarifa
        debe ser la permitida por la caja y la posicion fiscal la de la caja.
        TODO-VERIFICAR nombres en pos.config de Odoo 18: use_pricelist,
        pricelist_id, available_pricelist_ids, default_fiscal_position_id."""
        for order in self:
            config = order.config_id
            if order.pricelist_id:
                if "use_pricelist" in config._fields and not config.use_pricelist:
                    allowed = config.pricelist_id
                else:
                    allowed = config.pricelist_id | (
                        config.available_pricelist_ids
                        if "available_pricelist_ids" in config._fields
                        else config.env["product.pricelist"])
                if order.pricelist_id not in allowed:
                    raise AccessError(_("La tarifa del pedido no esta permitida en esta caja."))
            expected_fpos = (config.default_fiscal_position_id
                             if "default_fiscal_position_id" in config._fields
                             else config.env["account.fiscal.position"])
            if order.fiscal_position_id != expected_fpos:
                raise AccessError(_("La posicion fiscal del pedido no esta permitida en esta caja."))

    def _pos_check_payable(self):
        """Condiciones para pasar de borrador a pagado (usuarios restringidos).
        Odoo compara amount_total con amount_paid, pero ambos pueden ser datos
        del cliente: aqui se exige coherencia con las lineas y con los pagos
        reales (pos.payment)."""
        for order in self:
            currency = order._pos_currency()
            rounding = currency.rounding
            if not order.lines:
                raise AccessError(_("No se puede confirmar una venta sin lineas."))
            if float_compare(order.amount_total, 0.0, precision_rounding=rounding) <= 0:
                raise AccessError(_("No se puede confirmar una venta con total cero o negativo."))
            payments = order.payment_ids
            if not payments:
                raise AccessError(_("No se puede confirmar una venta sin pagos."))
            change = payments.filtered(lambda p: "is_change" in p._fields and p.is_change)
            normal = payments - change
            if any(float_compare(p.amount, 0.0, precision_rounding=rounding) <= 0 for p in normal):
                raise AccessError(_("Los pagos deben ser positivos."))
            net = sum(payments.mapped("amount"))
            if float_compare(abs(net - order.amount_total), order._pos_rounding_tolerance(),
                             precision_rounding=rounding) > 0:
                raise AccessError(
                    _("La suma de pagos (%(net)s) no coincide con el total (%(total)s).",
                      net=net, total=order.amount_total))
            # El cambio devuelto solo puede salir de pagos en efectivo.
            if change:
                cash_in = sum(cash_methods(normal).mapped("amount"))
                change_out = -sum(change.mapped("amount"))
                if (any(float_compare(p.amount, 0.0, precision_rounding=rounding) >= 0 for p in change)
                        or not all(is_cash_method(p.payment_method_id) for p in change)
                        or float_compare(change_out, cash_in, precision_rounding=rounding) > 0):
                    raise AccessError(_("El cambio devuelto no es coherente con los pagos en efectivo."))

    def _pos_check_restricted_write(self, vals):
        check_numeric_vals(vals, ORDER_AMOUNT_FIELDS)
        new_state = vals.get("state")
        for order in self:
            if "fiscal_position_id" in vals and (vals["fiscal_position_id"] or False) != (
                    order.fiscal_position_id.id or False):
                raise AccessError(_("Solo el gerente puede cambiar la posicion fiscal."))
            if order.state == "draft":
                if new_state == "cancel":
                    # remove_from_ui puede escribir 'cancel' antes de eliminar un
                    # carrito. Solo se admite si no hay pagos registrados.
                    # TODO-VERIFICAR (Odoo 18): secuencia real de remove_from_ui.
                    if order.payment_ids:
                        raise AccessError(_("No se puede cancelar una venta con pagos registrados."))
                elif new_state not in (None, "draft", "paid"):
                    raise AccessError(_("Solo el gerente puede cambiar el estado de ventas."))
            else:
                if set(vals) - ORDER_SYSTEM_FIELDS - {"state"}:
                    raise AccessError(_("Solo el gerente puede modificar ventas confirmadas."))
                if new_state and new_state != order.state and (
                        order.state, new_state) not in ORDER_ALLOWED_TRANSITIONS:
                    raise AccessError(_("Solo el gerente puede cambiar el estado de ventas confirmadas."))

    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        restricted = is_restricted(self.env)
        if restricted:
            for vals in vals_list:
                check_numeric_vals(vals, ORDER_AMOUNT_FIELDS)
                if vals.get("state", "draft") not in ORDER_CREATE_STATES:
                    raise AccessError(_("El cajero solo puede crear ventas en borrador."))
        orders = super().create(vals_list)
        if restricted:
            orders._pos_check_totals()
            orders._pos_check_pricing_context()
        elif not self.env.su:
            for order in orders:
                refund_lines = order.lines.filtered("refunded_orderline_id")
                if refund_lines:
                    self.env["pos.order.audit.log"]._pos_log(
                        "refund", order, {"lineas": refund_lines.ids})
        # La instantanea es idempotente; cubre pedidos creados ya confirmados.
        orders.filtered(lambda o: o.state in CONFIRMING_STATES).lines._pos_snapshot_costs()
        return orders

    def write(self, vals):
        restricted = is_restricted(self.env)
        if restricted:
            self._pos_check_restricted_write(vals)
        audit = None
        if not restricted and not self.env.su:
            confirmed = self.filtered(lambda o: o.state != "draft")
            ignore = set(ORDER_SYSTEM_FIELDS)
            if vals.get("state") in CONFIRMING_STATES:
                ignore.add("state")
            changed = [n for n in vals if n not in ignore]
            if confirmed and changed:
                before = read_before(confirmed, changed)
                audit = (confirmed, changed, before)
        to_pay = (self.filtered(lambda o: o.state == "draft")
                  if restricted and vals.get("state") == "paid" else self.browse())
        res = super().write(vals)
        if restricted:
            if to_pay or ORDER_AMOUNT_FIELDS & set(vals):
                self._pos_check_totals()
            if {"pricelist_id", "fiscal_position_id"} & set(vals):
                self._pos_check_pricing_context()
            # Se evalua siempre al confirmar; nunca se omite por falta de lineas.
            to_pay._pos_check_payable()
        if vals.get("state") in CONFIRMING_STATES:
            self.lines._pos_snapshot_costs()
        if audit:
            orders, changed, before = audit
            for order in orders:
                action = "cancel" if vals.get("state") == "cancel" else "correction"
                self.env["pos.order.audit.log"]._pos_log(action, order, {
                    "campos": changed,
                    "antes": before.get(str(order.id)),
                    "despues": {k: v for k, v in vals.items() if k in changed},
                })
        return res

    def unlink(self):
        if is_restricted(self.env) and any(order.state != "draft" for order in self):
            raise AccessError(_("Solo el gerente puede eliminar ventas confirmadas."))
        return super().unlink()
