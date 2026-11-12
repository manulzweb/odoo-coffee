from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosBlindCashClosing(models.Model):
    """Registro inmutable del cierre ciego de cada sesion.

    Lo crea y actualiza solo codigo del servidor (sudo). Ni el cajero ni nadie
    tiene ACL de escritura; el cajero ni siquiera tiene ACL de lectura, de modo
    que la diferencia nunca viaja a su navegador.
    """
    _name = "pos.blind.cash.closing"
    _description = "Cierre de caja ciego"
    _order = "counted_at desc, id desc"
    _rec_name = "session_name"

    session_id = fields.Many2one(
        "pos.session", string="Sesion", required=True, index=True,
        ondelete="restrict", readonly=True)
    session_name = fields.Char(string="Nombre de sesion", readonly=True)
    config_id = fields.Many2one("pos.config", string="Punto de venta", readonly=True)
    cashier_id = fields.Many2one("res.users", string="Cajero", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    state = fields.Selection(
        [("open", "Abierta, sin conteo"), ("counted", "Contado, sesion abierta"),
         ("closed", "Sesion cerrada")],
        default="open", required=True, readonly=True)
    counted_at = fields.Datetime(string="Fecha del conteo", readonly=True)
    closed_at = fields.Datetime(string="Fecha de cierre", readonly=True)
    opening_cash = fields.Monetary(string="Efectivo inicial", currency_field="currency_id", readonly=True)
    cash_sales = fields.Monetary(string="Ventas en efectivo", currency_field="currency_id", readonly=True)
    cash_moves = fields.Monetary(string="Entradas y salidas de efectivo", currency_field="currency_id", readonly=True)
    expected_cash = fields.Monetary(string="Efectivo esperado", currency_field="currency_id", readonly=True)
    counted_cash = fields.Monetary(string="Efectivo contado", currency_field="currency_id", readonly=True)
    difference = fields.Monetary(
        string="Diferencia (contado - esperado)", currency_field="currency_id", readonly=True)
    difference_at_count = fields.Monetary(
        string="Diferencia medida al contar", currency_field="currency_id", readonly=True,
        help="Contado - esperado en el momento del conteo; no cambia al cerrar.")
    cash_sales_after_count = fields.Monetary(
        string="Ventas en efectivo despues del conteo", currency_field="currency_id", readonly=True,
        help="Ventas en efectivo registradas entre el conteo y el cierre; explican la diferencia "
             "entre 'diferencia al contar' y 'diferencia'.")
    odoo_expected_cash = fields.Monetary(
        string="Esperado segun Odoo (control cruzado)", currency_field="currency_id", readonly=True,
        help="Valor nativo de la sesion, solo para detectar discrepancias de calculo.")
    has_previous = fields.Boolean(string="Hay cierre anterior", readonly=True)
    previous_counted_cash = fields.Monetary(
        string="Efectivo contado en el cierre anterior", currency_field="currency_id", readonly=True)
    opening_discrepancy = fields.Monetary(
        string="Apertura declarada - cierre anterior", currency_field="currency_id", readonly=True,
        help="Distinto de cero: el efectivo inicial declarado no coincide con lo contado al cerrar "
             "la sesion anterior (puede haber retiros autorizados; revisar).")
    calc_after_close = fields.Boolean(
        string="Cifras calculadas tras el cierre", readonly=True,
        help="Cierre hecho sin conteo ciego previo (p. ej. por el gerente): el ajuste de "
             "diferencia nativo puede estar ya incluido; no confiar en la diferencia.")
    odoo_mismatch = fields.Boolean(
        string="Difiere del calculo de Odoo", compute="_compute_odoo_mismatch")

    _sql_constraints = [
        ("session_unique", "unique(session_id)", "Ya existe un cierre ciego para esta sesion."),
    ]

    @api.depends("expected_cash", "odoo_expected_cash", "currency_id")
    def _compute_odoo_mismatch(self):
        for rec in self:
            if not rec.odoo_expected_cash and not rec.expected_cash:
                rec.odoo_mismatch = False
                continue
            rounding = rec.currency_id.rounding or 0.01
            rec.odoo_mismatch = abs(rec.expected_cash - rec.odoo_expected_cash) >= rounding

    # Inmutable: solo codigo con sudo() (env.su) puede escribir o borrar.
    def write(self, vals):
        if not self.env.su:
            raise UserError(_("El registro de cierre es inmutable."))
        return super().write(vals)

    def unlink(self):
        if not self.env.su:
            raise UserError(_("El registro de cierre es inmutable."))
        return super().unlink()

    @api.model
    def _register_opening(self, session):
        """Registra la apertura declarada y la compara con el ultimo cierre
        cerrado de la misma caja. Ejecutar con sudo."""
        session = session.sudo()
        rec = self.sudo().search([("session_id", "=", session.id)], limit=1)
        if rec:
            return rec
        currency = session.currency_id
        declared = currency.round(session.cash_register_balance_start or 0.0)
        previous = self.sudo().search([
            ("config_id", "=", session.config_id.id),
            ("state", "=", "closed"),
            ("session_id", "!=", session.id),
        ], order="closed_at desc, id desc", limit=1)
        return self.sudo().create({
            "session_id": session.id,
            "session_name": session.name,
            "config_id": session.config_id.id,
            "cashier_id": self.env.user.id,
            "currency_id": currency.id,
            "state": "open",
            "opening_cash": declared,
            "has_previous": bool(previous),
            "previous_counted_cash": previous.counted_cash if previous else 0.0,
            "opening_discrepancy": currency.round(declared - previous.counted_cash) if previous else 0.0,
        })

    @api.model
    def _register(self, session, counted_cash=None, final=False):
        """Guarda el conteo (final=False) o marca el cierre (final=True).

        Conteo: calcula esperado y diferencia y guarda difference_at_count.

        Cierre con conteo previo (N2/A1): recalcula SOLO las ventas en efectivo
        (pos.payment) para reflejar ventas hechas entre el conteo y el cierre, y
        con ellas expected_cash y difference. NO se vuelven a leer las
        entradas/salidas de efectivo (statement_line_ids): Odoo registra el
        ajuste nativo de diferencia ahi al cerrar y sumarlo igualaria esperado y
        contado. Se conservan los movimientos del conteo. counted_cash,
        opening_cash y difference_at_count no cambian. TODO-VERIFICAR (Odoo 18):
        confirmar en una prueba real que el ajuste nativo entra en
        statement_line_ids; si no, bastaria releer los movimientos.

        Sin registro de conteo (cierre del gerente sin conteo ciego) se crea con
        las cifras de ese momento y se marca calc_after_close. Ejecutar con sudo.
        """
        session = session.sudo()
        rec = self.sudo().search([("session_id", "=", session.id)], limit=1)
        currency = session.currency_id
        now = fields.Datetime.now()
        if final and rec and rec.state == "counted":
            figures = session._pos_cash_figures()
            expected = currency.round(rec.opening_cash + figures["cash_sales"] + rec.cash_moves)
            rec.write({
                "state": "closed",
                "closed_at": now,
                "cash_sales": figures["cash_sales"],
                "cash_sales_after_count": currency.round(
                    figures["cash_sales"] - rec.cash_sales),
                "expected_cash": expected,
                "difference": currency.round(rec.counted_cash - expected),
            })
            return rec
        if final and rec and rec.state == "closed":
            return rec
        figures = session._pos_cash_figures()
        if counted_cash is None:
            counted_cash = session.cash_register_balance_end_real or 0.0
        counted_cash = currency.round(counted_cash)
        difference = currency.round(counted_cash - figures["expected"])
        vals = {
            "session_id": session.id,
            "session_name": session.name,
            "config_id": session.config_id.id,
            "currency_id": currency.id,
            "opening_cash": figures["opening"],
            "cash_sales": figures["cash_sales"],
            "cash_moves": figures["moves"],
            "cash_sales_after_count": 0.0,
            "expected_cash": figures["expected"],
            "odoo_expected_cash": figures["odoo_expected"],
            "counted_cash": counted_cash,
            "difference": difference,
            "difference_at_count": difference,
            "counted_at": now,
        }
        if final:
            vals.update({"state": "closed", "closed_at": now, "calc_after_close": True})
        else:
            vals["state"] = "counted"
        if rec:
            rec.write(vals)
            return rec
        # sudo() conserva el uid real: quien conto.
        vals["cashier_id"] = self.env.user.id
        return self.sudo().create(vals)
