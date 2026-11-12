import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from . import blind_common as bc

_logger = logging.getLogger(__name__)

GENERIC_CLOSE_ERROR = "No se pudo cerrar la caja. Avise al gerente."
# Escritura directa (RPC write) permitida a un cajero ciego fuera de la ventana
# interna. Todo lo demas (state, cash_register_*, stop_at, user_id...) exige
# pasar por los metodos propios. TODO-VERIFICAR (Odoo 18): campos que el flujo
# nativo escribe como cajero sin sudo (login_number, sequence_number, ...).
SAFE_DIRECT_WRITE = frozenset({"login_number", "sequence_number"})
# Transiciones de estado que un cajero ciego puede provocar (siempre dentro de
# los metodos propios). El paso a 'closed' ademas exige un conteo previo.
STATE_TRANSITIONS = frozenset({
    ("opening_control", "opened"),
    ("opened", "closing_control"),
    ("closing_control", "opened"),
})
MAX_NOTES = 500


class PosSession(models.Model):
    _inherit = "pos.session"

    # Campo tecnico para las reglas (ver security_rules.xml): verdadero solo
    # mientras corre una ventana interna del servidor. Siempre devuelve falso
    # a cualquier lectura RPC porque el cliente no puede abrir la ventana.
    pos_window = fields.Boolean(
        compute="_compute_pos_window", search="_search_pos_window",
        string="Ventana interna (tecnico)")

    def _compute_pos_window(self):
        active = bc.in_window()
        for rec in self:
            rec.pos_window = active

    def _search_pos_window(self, operator, value):
        if operator not in ("=", "!="):
            raise UserError(_("Operador no soportado."))
        wants_true = bool(value) if operator == "=" else not bool(value)
        match_all = bc.in_window() == wants_true
        return [(1, "=", 1)] if match_all else [(0, "=", 1)]

    def _setup_complete(self):
        super()._setup_complete()
        bc.apply_field_groups(self, bc.SESSION_SENSITIVE)

    # ------------------------------------------------------------------
    # Vectores RPC genericos
    # ------------------------------------------------------------------
    def read(self, fields=None, load="_classic_read"):
        return bc.filtered_read(self, super().read, fields, load)

    def _search(self, domain, *args, **kwargs):
        bc.check_domain(self.env, domain, *args, **kwargs)
        return super()._search(domain, *args, **kwargs)

    def _read_group(self, domain, groupby=(), aggregates=(), *args, **kwargs):
        bc.check_domain(self.env, domain, *args, **kwargs)
        bc.check_group_args(self.env, groupby, aggregates, *args, **kwargs)
        return super()._read_group(domain, groupby, aggregates, *args, **kwargs)

    def export_data(self, *args, **kwargs):
        bc.block_export(self.env)
        return super().export_data(*args, **kwargs)

    # ------------------------------------------------------------------
    # Precarga del POS (loadData)
    # ------------------------------------------------------------------
    @api.model
    def _load_pos_data_fields(self, *args, **kwargs):
        # TODO-VERIFICAR (Odoo 18): metodo de precarga del POS.
        return bc.filter_load_fields(self.env, super()._load_pos_data_fields(*args, **kwargs))

    def load_data(self, *args, **kwargs):
        """Red de seguridad: ademas de recortar los campos, se limpia la
        respuesta completa. TODO-VERIFICAR (Odoo 18): existencia y firma de
        pos.session.load_data."""
        result = super().load_data(*args, **kwargs)
        if bc.is_blind(self.env):
            result = bc.strip_sensitive_payload(result)
        return result

    # ------------------------------------------------------------------
    # Calculo de efectivo esperado (solo servidor)
    # ------------------------------------------------------------------
    def _pos_cash_methods(self):
        """Medios de pago en efectivo de la sesion. TODO-VERIFICAR (Odoo 18):
        se usa type == 'cash' si el campo existe; si no, is_cash_count."""
        methods = self.sudo().payment_method_ids
        if methods and "type" in methods._fields:
            return methods.filtered(lambda m: m.type == "cash")
        return methods.filtered(lambda m: getattr(m, "is_cash_count", False))

    def _pos_cash_figures(self):
        """Efectivo esperado calculado por el servidor. Nunca se envia al
        cajero. TODO-VERIFICAR (Odoo 18): campos is_cash_count,
        pos.payment.session_id, statement_line_ids, cash_register_balance_start
        y cash_register_balance_end."""
        self.ensure_one()
        session = self.sudo()
        currency = session.currency_id
        cash_methods = session._pos_cash_methods()
        payments = self.env["pos.payment"].sudo().search([
            ("session_id", "=", session.id),
            ("payment_method_id", "in", cash_methods.ids),
        ])
        cash_sales = sum(payments.mapped("amount"))
        moves = 0.0
        if "statement_line_ids" in session._fields:
            moves = sum(session.statement_line_ids.mapped("amount"))
        opening = session.cash_register_balance_start or 0.0
        odoo_expected = 0.0
        if "cash_register_balance_end" in session._fields:
            odoo_expected = session.cash_register_balance_end or 0.0
        return {
            "opening": currency.round(opening),
            "cash_sales": currency.round(cash_sales),
            "moves": currency.round(moves),
            "expected": currency.round(opening + cash_sales + moves),
            "odoo_expected": currency.round(odoo_expected),
        }

    def _pos_check_blind_caller(self):
        """El cajero solo puede cerrar su propia sesion abierta."""
        self.ensure_one()
        if bc.is_blind(self.env):
            session = self.sudo()
            if session.user_id.id != self.env.uid:
                raise AccessError(_("Operacion no permitida."))
            config = session.config_id
            # El cierre ciego se apoya en el control de efectivo (apertura y
            # cierre con conteo). TODO-VERIFICAR (Odoo 18): campo cash_control.
            if "cash_control" in config._fields and not config.cash_control:
                raise UserError(_(
                    "Active el control avanzado de efectivo en el punto de venta "
                    "para usar el cierre ciego."))
            # Con limite de diferencia activo, Odoo bloquea el cierre cuando la
            # diferencia lo supera: permite deducir el esperado por tanteo.
            if "set_maximum_difference" in config._fields and config.set_maximum_difference:
                raise UserError(_(
                    "Configuracion no valida para cierre ciego: desactive el "
                    "limite maximo de diferencia en el punto de venta."))

    def _pos_draft_orders_message(self):
        draft = self.env["pos.order"].sudo().search_count(
            [("session_id", "=", self.id), ("state", "=", "draft")])
        if draft:
            return _("Hay ventas sin cobrar. Cobrelas o cancelelas antes de cerrar la caja.")
        return False

    # ------------------------------------------------------------------
    # Cierre ciego: datos que ve el cajero
    # ------------------------------------------------------------------
    def get_closing_control_data(self, *args, **kwargs):
        """Datos del dialogo de cierre. Para el cajero: solo nombres e ids de
        medios de pago con importes en cero. No se llama a super() (ni se
        calcula nada). TODO-VERIFICAR (Odoo 18): claves que espera el dialogo
        estandar de cierre del POS."""
        if not bc.is_blind(self.env):
            return super().get_closing_control_data(*args, **kwargs)
        self.ensure_one()
        self._pos_check_blind_caller()
        session = self.sudo()
        methods = session.payment_method_ids
        cash = session._pos_cash_methods()[:1]
        others = methods - cash
        return {
            "orders_details": {"quantity": 0, "amount": 0},
            # TODO-VERIFICAR (Odoo 18): claves exactas del dialogo de cierre;
            # opening_notes es la nota que escribio el propio cajero.
            "opening_notes": (session.opening_notes or "") if "opening_notes" in session._fields else "",
            "default_cash_details": {
                "name": cash.name, "amount": 0, "opening": 0, "payments": 0,
                "moves": [], "id": cash.id,
            } if cash else None,
            "other_payment_methods": [
                {"name": pm.name, "amount": 0, "number": 0, "id": pm.id,
                 "type": pm.type if "type" in pm._fields else False}
                for pm in others
            ],
            "is_manager": False,
            "amount_authorized_diff": None,
            "pos_blind": True,
        }

    def post_closing_cash_details(self, counted_cash, *args, **kwargs):
        """El cajero informa el efectivo contado; el servidor calcula y guarda
        la diferencia en pos.blind.cash.closing y NO la devuelve."""
        if not bc.is_blind(self.env):
            return super().post_closing_cash_details(counted_cash, *args, **kwargs)
        self.ensure_one()
        self._pos_check_blind_caller()
        counted = bc.clean_counted_cash(counted_cash)
        message = self._pos_draft_orders_message()
        if message:
            return {"successful": False, "message": message, "redirect": False}
        session = self.sudo()
        try:
            with self.env.cr.savepoint(), bc.internal_window():
                # Argumentos extra del cliente NO se reenvian (A8).
                result = super(PosSession, session).post_closing_cash_details(counted)
        except (UserError, AccessError) as exc:
            _logger.warning("Cierre ciego, post_closing_cash_details fallo en %s: %s", self.id, exc)
            return {"successful": False, "message": GENERIC_CLOSE_ERROR, "redirect": False}
        if isinstance(result, dict) and result.get("successful") is False:
            _logger.warning("Cierre ciego, rechazo en %s: %s", self.id, result.get("message"))
            return {"successful": False, "message": GENERIC_CLOSE_ERROR, "redirect": False}
        self.env["pos.blind.cash.closing"]._register(session, counted_cash=counted)
        return {"successful": True}

    def action_pos_session_closing_control(self, *args, **kwargs):
        # Ruta directa por RPC: cierra sin pasar por el conteo ciego.
        if bc.is_blind(self.env) and not bc.in_window():
            raise AccessError(_("Operacion no permitida."))
        return super().action_pos_session_closing_control(*args, **kwargs)

    def action_pos_session_validate(self, *args, **kwargs):
        if bc.is_blind(self.env) and not bc.in_window():
            raise AccessError(_("Operacion no permitida."))
        return super().action_pos_session_validate(*args, **kwargs)

    def close_session_from_ui(self, *args, **kwargs):
        """Cierre final. Para el cajero: exige conteo previo, corre con sudo
        (es la operacion de contabilidad de Odoo) y sustituye cualquier
        mensaje de error por uno generico: los mensajes nativos pueden
        contener importes esperados o diferencias."""
        if not bc.is_blind(self.env):
            result = super().close_session_from_ui(*args, **kwargs)
            self._pos_finalize_if_closed(result)
            return result
        self.ensure_one()
        self._pos_check_blind_caller()
        session = self.sudo()
        closing = self.env["pos.blind.cash.closing"].sudo().search(
            [("session_id", "=", session.id), ("state", "=", "counted")], limit=1)
        if not closing:
            return {"successful": False, "redirect": False,
                    "message": _("Registre primero el efectivo contado.")}
        message = self._pos_draft_orders_message()
        if message:
            return {"successful": False, "message": message, "redirect": False}
        try:
            with self.env.cr.savepoint(), bc.internal_window():
                # Sin argumentos del cliente: bank_payment_method_diff_pairs
                # generaria asientos con importes elegidos por el cajero (A8).
                result = super(PosSession, session).close_session_from_ui()
        except (UserError, AccessError) as exc:
            _logger.warning("Cierre ciego, close_session_from_ui fallo en %s: %s", self.id, exc)
            return {"successful": False, "message": GENERIC_CLOSE_ERROR, "redirect": False}
        if isinstance(result, dict) and result.get("successful") is False:
            _logger.warning("Cierre ciego, cierre rechazado en %s: %s", self.id, result.get("message"))
            return {"successful": False, "message": GENERIC_CLOSE_ERROR, "redirect": False}
        self._pos_finalize_if_closed(result)
        return {"successful": True}

    def _pos_finalize_if_closed(self, result):
        """Marca el registro como cerrado y recalcula el esperado final."""
        if isinstance(result, dict) and result.get("successful") is False:
            return
        session = self.sudo()
        if session.state != "closed":
            return
        try:
            with self.env.cr.savepoint():
                self.env["pos.blind.cash.closing"]._register(session, final=True)
        except Exception:  # noqa: BLE001 - no romper el cierre contable
            _logger.exception("No se pudo registrar el cierre ciego de la sesion %s", self.id)

    # ------------------------------------------------------------------
    # Integridad del flujo ciego (C2): escrituras y metodos publicos
    # ------------------------------------------------------------------
    def onchange(self, *args, **kwargs):
        bc.block_export(self.env)
        return super().onchange(*args, **kwargs)

    @api.model_create_multi
    def create(self, vals_list):
        if bc.is_blind(self.env):
            for vals in vals_list:
                if vals.get("state") not in (None, False, "opening_control"):
                    raise AccessError(_("Operacion no permitida."))
                if vals.get("user_id") not in (None, False, self.env.uid):
                    raise AccessError(_("Operacion no permitida."))
                if set(vals) & {"cash_register_balance_start", "cash_register_balance_end_real"}:
                    raise AccessError(_("Operacion no permitida."))
        return super().create(vals_list)

    def write(self, vals):
        if bc.is_blind(self.env):
            self._pos_check_blind_write(vals)
        return super().write(vals)

    def _pos_check_blind_write(self, vals):
        """Un cajero no puede escribir state, efectivo inicial/final ni otros
        campos de la sesion por RPC; solo lo hacen los metodos propios
        (ventana interna). El paso a 'closed' exige un conteo previo."""
        keys = set(vals)
        if keys - SAFE_DIRECT_WRITE and not bc.in_window():
            raise AccessError(_("Operacion no permitida."))
        if "state" in vals:
            new_state = vals["state"]
            Closing = self.env["pos.blind.cash.closing"].sudo()
            for rec in self.sudo():
                if new_state == rec.state:
                    continue
                if new_state == "closed":
                    counted = Closing.search_count([
                        ("session_id", "=", rec.id), ("state", "=", "counted")])
                    if not counted:
                        raise AccessError(_("Operacion no permitida."))
                elif (rec.state, new_state) not in STATE_TRANSITIONS:
                    raise AccessError(_("Operacion no permitida."))

    def action_pos_session_open(self, *args, **kwargs):
        # TODO-VERIFICAR (Odoo 18): nombre; escribe state/start_at al abrir.
        if not bc.is_blind(self.env):
            return super().action_pos_session_open(*args, **kwargs)
        with bc.internal_window():
            return super().action_pos_session_open(*args, **kwargs)

    def set_opening_control(self, cashbox_value, notes=None, *args, **kwargs):
        """Apertura con efectivo inicial. Se registra el efectivo declarado y
        su diferencia con el ultimo conteo cerrado (M9)."""
        if not bc.is_blind(self.env):
            result = super().set_opening_control(cashbox_value, notes, *args, **kwargs)
            self._pos_register_opening()
            return result
        self.ensure_one()
        self._pos_check_blind_caller()
        # N1: una sola declaracion, y solo mientras la sesion esta en apertura.
        # Re-declarar el efectivo inicial despues de vender falsearia el esperado.
        session = self.sudo()
        if session.state != "opening_control" or self.env["pos.blind.cash.closing"].sudo().search_count(
                [("session_id", "=", session.id)]):
            raise UserError(_("El efectivo inicial ya fue declarado para esta sesion."))
        amount = bc.clean_counted_cash(cashbox_value)
        notes = str(notes)[:MAX_NOTES] if notes else notes
        with bc.internal_window():
            result = super().set_opening_control(amount, notes)
        self._pos_register_opening()
        return result

    def _pos_register_opening(self):
        """Registra la apertura declarada y la compara con el ultimo conteo
        cerrado de la misma caja. Nunca rompe la apertura."""
        try:
            with self.env.cr.savepoint():
                self.env["pos.blind.cash.closing"]._register_opening(self.sudo())
        except Exception:  # noqa: BLE001
            _logger.exception("No se pudo registrar la apertura de la sesion %s", self.id)

    def update_closing_control_state_session(self, notes=None, *args, **kwargs):
        """Paso intermedio del cierre nativo (state -> closing_control). Para el
        cajero solo despues de registrar el conteo ciego."""
        if not bc.is_blind(self.env):
            return super().update_closing_control_state_session(notes, *args, **kwargs)
        self.ensure_one()
        self._pos_check_blind_caller()
        if not self.env["pos.blind.cash.closing"].sudo().search_count([
                ("session_id", "=", self.id), ("state", "=", "counted")]):
            raise UserError(_("Registre primero el efectivo contado."))
        notes = str(notes)[:MAX_NOTES] if notes else notes
        with bc.internal_window():
            return super().update_closing_control_state_session(notes)

    def action_pos_session_close(self, *args, **kwargs):
        """Cierre contable directo (acepta diferencias bancarias y cuentas de
        ajuste elegidas por el llamante): solo gerente/admin. El cajero cierra
        con close_session_from_ui / pos_blind_close.
        TODO-VERIFICAR (Odoo 18): nombre y firma."""
        if bc.is_blind(self.env):
            raise AccessError(_("Operacion no permitida."))
        return super().action_pos_session_close(*args, **kwargs)

    def try_cash_in_out(self, *args, **kwargs):
        """Entradas y salidas de efectivo: pueden tapar un faltante sin dejar
        rastro en el conteo. DECISION: solo gerente/admin las registran; el
        cajero ciego queda bloqueado (pendiente confirmar con Efrain).
        TODO-VERIFICAR (Odoo 18): nombre y firma."""
        if bc.is_blind(self.env):
            raise AccessError(_("Solo el gerente puede registrar entradas o salidas de efectivo."))
        return super().try_cash_in_out(*args, **kwargs)

    def pos_blind_close(self, counted_cash, notes=None):
        """Punto de entrada unico de cierre ciego (para el POS o clientes
        propios): cuenta, guarda notas y cierra en una sola llamada."""
        self.ensure_one()
        result = self.post_closing_cash_details(counted_cash)
        if isinstance(result, dict) and not result.get("successful"):
            return result
        if notes and hasattr(self, "update_closing_control_state_session"):
            # TODO-VERIFICAR (Odoo 18): update_closing_control_state_session(notes).
            self.update_closing_control_state_session(notes)
        return self.close_session_from_ui()
