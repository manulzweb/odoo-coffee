"""Regla para modelos opcionales que no se pueden referenciar desde XML sin
riesgo de romper la instalacion si el nombre cambia entre versiones."""
import logging

_logger = logging.getLogger(__name__)

PRIV_EXPR = (
    "user.has_group('pos_order_integrity.group_pos_store_manager') "
    "or user.has_group('base.group_system') "
    "or not (user.has_group('point_of_sale.group_pos_user') "
    "or user.has_group('pos_order_integrity.group_cashier_restricted'))"
)
OPTIONAL_RULES = (
    # (modelo, nombre de la regla)
    # TODO-VERIFICAR: nombre del modelo del reporte de analisis de ventas del POS.
    ("report.pos.order", "Cierre ciego POS: sin lectura para no gerentes (report.pos.order)"),
)


def post_init_hook(env):
    for model_name, rule_name in OPTIONAL_RULES:
        model = env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
        if not model:
            _logger.warning(
                "pos_blind_cash_closing: el modelo %s no existe; regla omitida. "
                "TODO-VERIFICAR: reporte sin proteger.", model_name)
            continue
        Rule = env["ir.rule"].sudo()
        if Rule.search([("name", "=", rule_name)], limit=1):
            continue
        Rule.create({
            "name": rule_name,
            "model_id": model.id,
            "domain_force": "[(1, '=', 1)] if (%s) else [(0, '=', 1)]" % PRIV_EXPR,
            "perm_read": True,
            "perm_write": False,
            "perm_create": False,
            "perm_unlink": False,
        })


def uninstall_hook(env):
    names = [name for _model, name in OPTIONAL_RULES]
    env["ir.rule"].sudo().search([("name", "in", names)]).unlink()
