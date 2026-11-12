"""Utilidades compartidas de los controles de servidor (no es un modelo de Odoo).

Criterio central: la decision de restringir depende SOLO de datos del servidor
(usuario autenticado y sus grupos, y env.su que solo puede activar codigo
Python del servidor). Nunca de claves de contexto ni de parametros enviados por
el cliente, porque un cajero puede fabricar cualquier llamada RPC.
"""
import json
from math import isfinite
from numbers import Real

from odoo import _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round

GROUP_CASHIER = "pos_order_integrity.group_cashier_restricted"
GROUP_MANAGER = "pos_order_integrity.group_pos_store_manager"
GROUP_SYSTEM = "base.group_system"

# Decimales maximos aceptados para pesos (balanza de mostrador: gramos).
WEIGHT_DECIMALS = 3


def is_privileged(env):
    """Gerente de la cafeteria o administrador tecnico."""
    user = env.user
    return user.has_group(GROUP_MANAGER) or user.has_group(GROUP_SYSTEM)


def is_restricted(env):
    """Denegar por defecto: restringido es todo usuario que no sea gerente ni
    administrador tecnico, aunque se le olvide asignar el grupo de cajero.

    env.su es verdadero para uid 1 y para cualquier sudo() ejecutado por codigo
    del servidor (incluido el propio Odoo en sus operaciones internas); un
    cliente RPC no puede activarlo.
    """
    if env.su:
        return False
    return not is_privileged(env)


def check_numeric_vals(vals, field_names):
    """Rechaza no numericos, booleanos, NaN e infinitos antes de escribir."""
    for name in field_names:
        if name in vals:
            value = vals[name]
            if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
                raise ValidationError(
                    _("El valor del campo %s debe ser un numero finito.", name))


def exceeds_decimals(value, digits):
    """True si value tiene mas decimales que digits (evita redondeo silencioso)."""
    rounded = float_round(value, precision_digits=digits)
    return float_compare(value, rounded, precision_digits=digits + 3) != 0


def scalar_field_names(model, names):
    return [
        n for n in names
        if n in model._fields
        and model._fields[n].type not in ("one2many", "many2many", "binary")
    ]


def dump_detail(payload):
    return json.dumps(payload, default=str, ensure_ascii=False, sort_keys=True)


def read_before(records, names):
    """Valores actuales (antes de escribir) de los campos escalares de names."""
    scalar = scalar_field_names(records, names)
    if not scalar:
        return {}
    return {str(vals["id"]): vals for vals in records.sudo().read(scalar)}


def is_cash_method(payment_method):
    """True si el metodo de pago (un solo registro) es de efectivo.

    Unico punto de decision del guard. Prefiere `type == 'cash'` si el campo
    existe en el modelo y usa `is_cash_count` si no. Si no existe ninguno falla
    cerrado con un mensaje claro (no se adivina ni se asume efectivo).
    TODO-VERIFICAR (Odoo 18): cual de los dos campos existe en pos.payment.method.
    pos_blind_cash_closing tiene su propio helper equivalente: ese modulo depende
    de este, asi que no puede importarse en sentido contrario; mantener ambas
    reglas alineadas a mano.
    """
    fields_ = payment_method._fields
    if "type" in fields_:
        return payment_method.type == "cash"
    if "is_cash_count" in fields_:
        return bool(payment_method.is_cash_count)
    raise UserError(_(
        "No se puede determinar si el metodo de pago es de efectivo: el modelo no "
        "tiene ni 'type' ni 'is_cash_count'. Se rechaza la operacion por seguridad."))


def cash_methods(payments):
    """Subconjunto de pagos cuyo metodo es de efectivo (usa is_cash_method)."""
    return payments.filtered(lambda p: is_cash_method(p.payment_method_id))
