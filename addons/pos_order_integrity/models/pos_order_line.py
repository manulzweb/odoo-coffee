from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import float_compare, float_is_zero

from .guard import (
    WEIGHT_DECIMALS, check_numeric_vals, exceeds_decimals, is_restricted,
    read_before,
)

# Campos que Odoo escribe por su cuenta, con el usuario de la sesion y SIN sudo,
# despues de confirmar el pago (calculo de costo). Ver README: por que se
# permiten por nombre de campo y no con una bandera de contexto.
# TODO-VERIFICAR (Odoo 18): nombres exactos y quien los escribe.
LINE_SYSTEM_FIELDS = frozenset({"total_cost", "is_total_cost_computed"})
# Instantanea de costo propia: solo escribible desde codigo con sudo (env.su).
LINE_SNAPSHOT_FIELDS = frozenset(
    {"pos_cost_known", "pos_unit_cost", "pos_cost_date"})
LINE_NUMERIC_FIELDS = ("qty", "price_unit", "discount", "price_subtotal", "price_subtotal_incl")
LINE_VALIDATED_FIELDS = frozenset(
    {"product_id", "qty", "price_unit", "discount", "price_subtotal",
     "price_subtotal_incl", "tax_ids", "order_id", "refunded_orderline_id"})
LINE_AUDIT_VALUE_FIELDS = ("product_id", "qty", "price_unit", "discount")


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    # Costo historico conservado en la linea al confirmar la venta.
    pos_cost_known = fields.Boolean(
        string="Costo conocido al vender", readonly=True, copy=False)
    pos_unit_cost = fields.Float(
        string="Costo unitario al vender", digits="Product Price", readonly=True, copy=False)
    pos_cost_date = fields.Datetime(
        string="Fecha de la instantanea de costo", readonly=True, copy=False)

    # ------------------------------------------------------------------
    # Reglas de datos validas para TODOS los usuarios
    # ------------------------------------------------------------------
    @api.model
    def _pos_check_qty_value(self, qty, mode, is_refund):
        """Reglas de cantidad por modo de venta. Se usa con el valor ALMACENADO
        (constraint) y con el valor CRUDO de vals antes de escribir: el campo
        qty tiene 2 decimales por defecto y redondea, lo que ocultaria 0,1255."""
        qty = abs(qty) if is_refund else qty
        if float_compare(qty, 0.0, precision_digits=6) <= 0:
            raise ValidationError(_("La cantidad debe ser positiva."))
        if mode == "weight":
            if exceeds_decimals(qty, WEIGHT_DECIMALS):
                raise ValidationError(
                    _("El peso admite como maximo %s decimales.", WEIGHT_DECIMALS))
        elif float_compare(qty, round(qty), precision_digits=6) != 0:
            raise ValidationError(_("Unidades y bolsas se venden en cantidades enteras."))

    @api.constrains("qty", "product_id")
    def _check_pos_quantity(self):
        for line in self:
            if line.product_id:
                mode = line.product_id.sudo().product_tmpl_id.pos_sale_mode
                self._pos_check_qty_value(line.qty, mode, bool(line.refunded_orderline_id))

    @api.model
    def _pos_check_raw_vals_create(self, vals):
        """Cantidad cruda de vals (antes de super) para un create."""
        if "qty" in vals and vals.get("product_id"):
            product = self.env["product.product"].sudo().browse(vals["product_id"]).exists()
            if product:
                self._pos_check_qty_value(
                    vals["qty"], product.product_tmpl_id.pos_sale_mode,
                    bool(vals.get("refunded_orderline_id")))

    def _pos_check_raw_vals_write(self, vals):
        """Cantidad cruda de vals (antes de super) para un write."""
        if "qty" not in vals:
            return
        for line in self:
            product = (self.env["product.product"].sudo().browse(vals["product_id"])
                       if vals.get("product_id") else line.product_id.sudo())
            if product:
                refund = vals.get("refunded_orderline_id", line.refunded_orderline_id.id)
                self._pos_check_qty_value(
                    vals["qty"], product.product_tmpl_id.pos_sale_mode, bool(refund))

    # ------------------------------------------------------------------
    # Validaciones solo para usuarios restringidos
    # ------------------------------------------------------------------
    def _pos_expected_unit_price(self):
        self.ensure_one()
        product = self.product_id.sudo()
        order = self.order_id
        pricelist = order.pricelist_id
        if pricelist:
            # TODO-VERIFICAR: firma de product.pricelist._get_product_price en
            # Odoo 18 (product, quantity, uom, date) y su coherencia con
            # impuestos incluidos y posiciones fiscales.
            return pricelist.sudo()._get_product_price(
                product, abs(self.qty) or 1.0, uom=product.uom_id, date=order.date_order)
        return product.lst_price

    def _pos_validate_restricted(self):
        for line in self:
            order = line.order_id
            if "combo_parent_id" in line._fields and line.combo_parent_id:
                raise AccessError(_("Los combos no estan soportados en esta cafeteria."))
            if not line.product_id:
                raise AccessError(_("Toda linea debe tener un producto del catalogo."))
            if line.refunded_orderline_id:
                raise AccessError(_("Solo el gerente puede registrar devoluciones."))
            if not float_is_zero(line.discount, precision_digits=4):
                raise AccessError(_("Solo el gerente puede aplicar descuentos."))
            currency = order.currency_id or order.company_id.currency_id
            expected = line._pos_expected_unit_price()
            if float_compare(line.price_unit, expected, precision_rounding=currency.rounding) != 0:
                raise AccessError(
                    _("El precio %(got)s no coincide con el de lista %(exp)s.",
                      got=line.price_unit, exp=expected))
            # Los impuestos de la linea deben ser los del producto (la posicion
            # fiscal se valida a nivel de pedido y se aplica via
            # tax_ids_after_fiscal_position). TODO-VERIFICAR: en Odoo 18 tax_ids
            # guarda los impuestos del producto ANTES de la posicion fiscal.
            product_taxes = line.product_id.sudo().taxes_id.filtered(
                lambda t: t.company_id == order.company_id)
            if set(line.tax_ids.ids) != set(product_taxes.ids):
                raise AccessError(_("Los impuestos de la linea no coinciden con los del producto."))
            # Recalculo independiente: price_subtotal* podrian venir del cliente.
            taxes = (line.tax_ids_after_fiscal_position
                     if "tax_ids_after_fiscal_position" in line._fields else line.tax_ids)
            res = taxes.compute_all(  # TODO-VERIFICAR firma compute_all en 18
                line.price_unit, currency=currency, quantity=line.qty,
                product=line.product_id, partner=order.partner_id)
            if (float_compare(res["total_excluded"], line.price_subtotal,
                              precision_rounding=currency.rounding) != 0
                    or float_compare(res["total_included"], line.price_subtotal_incl,
                                     precision_rounding=currency.rounding) != 0):
                raise AccessError(_("Los subtotales de la linea no coinciden con el calculo del servidor."))

    # ------------------------------------------------------------------
    # Instantanea de costo historico
    # ------------------------------------------------------------------
    def _pos_snapshot_costs(self):
        """Copia a la linea el costo vigente (o el de la linea original en una
        devolucion). Idempotente: una linea ya fotografiada no se vuelve a tocar.
        Escribe con sudo para no depender de permisos del usuario de la sesion."""
        now = fields.Datetime.now()
        for line in self.filtered(lambda l: l.product_id and not l.pos_cost_date):
            origin = line.refunded_orderline_id
            if origin and origin.pos_cost_date:
                known, unit = origin.pos_cost_known, origin.pos_unit_cost
            else:
                tmpl = line.product_id.sudo().product_tmpl_id
                known = tmpl.pos_cost_known
                unit = tmpl.pos_manual_cost if known else 0.0
            line.sudo().write({
                "pos_cost_known": known,
                "pos_unit_cost": unit,
                "pos_cost_date": now,
            })

    def _pos_line_margin(self):
        """Margen bruto estimado sin impuestos, o None si el costo era desconocido."""
        self.ensure_one()
        if not self.pos_cost_known:
            return None
        return self.price_subtotal - self.pos_unit_cost * self.qty

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        restricted = is_restricted(self.env)
        for vals in vals_list:
            check_numeric_vals(vals, LINE_NUMERIC_FIELDS)
            self._pos_check_raw_vals_create(vals)
            if not self.env.su and (LINE_SNAPSHOT_FIELDS & set(vals)):
                raise AccessError(_("La instantanea de costo no se puede escribir manualmente."))
            if restricted and (LINE_SYSTEM_FIELDS & set(vals)):
                raise AccessError(_("Campo reservado al sistema."))
            if restricted:
                order = self.env["pos.order"].browse(vals.get("order_id")).exists()
                if not order or order.state != "draft":
                    raise AccessError(_("No se pueden agregar lineas a ventas confirmadas."))
        lines = super().create(vals_list)
        if restricted:
            lines._pos_validate_restricted()
        elif not self.env.su:
            for order in lines.order_id.filtered(lambda o: o.state != "draft"):
                self.env["pos.order.audit.log"]._pos_log(
                    "correction", order,
                    {"lineas_creadas": lines.filtered(lambda l: l.order_id == order).ids})
        return lines

    def write(self, vals):
        restricted = is_restricted(self.env)
        check_numeric_vals(vals, LINE_NUMERIC_FIELDS)
        self._pos_check_raw_vals_write(vals)
        if not self.env.su and (LINE_SNAPSHOT_FIELDS & set(vals)):
            raise AccessError(_("La instantanea de costo no se puede modificar."))
        audit_before = None
        confirmed = self.filtered(lambda l: l.order_id.state != "draft")
        if restricted:
            if confirmed:
                extra = set(vals) - LINE_SYSTEM_FIELDS
                if extra:
                    raise AccessError(_("Solo el gerente puede modificar ventas confirmadas."))
                # Escritura interna legitima de costo: se admite una sola vez por
                # linea (mientras el costo nativo aun no este calculado).
                if any(line.is_total_cost_computed for line in confirmed):
                    raise AccessError(_("El costo de una venta confirmada ya no se puede cambiar."))
            if vals.get("order_id"):
                order = self.env["pos.order"].browse(vals["order_id"]).exists()
                if not order or order.state != "draft":
                    raise AccessError(_("No se pueden mover lineas a ventas confirmadas."))
        elif not self.env.su:
            changed = [n for n in vals if n not in LINE_SYSTEM_FIELDS]
            if confirmed and changed:
                names = list({*changed, *LINE_AUDIT_VALUE_FIELDS})
                audit_before = (confirmed, changed, read_before(confirmed, names))
        res = super().write(vals)
        if restricted and (LINE_VALIDATED_FIELDS & set(vals)):
            self._pos_validate_restricted()
        if audit_before:
            lines, changed, before = audit_before
            for order in lines.order_id:
                ids = lines.filtered(lambda l: l.order_id == order).ids
                self.env["pos.order.audit.log"]._pos_log("correction", order, {
                    "lineas": ids, "campos": changed,
                    "antes": {str(i): before.get(str(i)) for i in ids},
                    "despues": {k: v for k, v in vals.items() if k in changed},
                })
        return res

    def unlink(self):
        restricted = is_restricted(self.env)
        confirmed = self.filtered(lambda l: l.order_id.state != "draft")
        if restricted and confirmed:
            raise AccessError(_("Solo el gerente puede modificar ventas confirmadas."))
        if confirmed and not self.env.su:
            before = read_before(confirmed, list(LINE_AUDIT_VALUE_FIELDS))
            for order in confirmed.order_id:
                ids = confirmed.filtered(lambda l: l.order_id == order).ids
                self.env["pos.order.audit.log"]._pos_log("correction", order, {
                    "lineas_eliminadas": {str(i): before.get(str(i)) for i in ids}})
        return super().unlink()
