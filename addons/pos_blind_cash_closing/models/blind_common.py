"""Utilidades compartidas del cierre ciego (no es un modelo de Odoo).

Criterio central, igual que en pos_order_integrity: la decision de ocultar datos
depende SOLO de datos del servidor (usuario autenticado, sus grupos, env.su y
una bandera local al hilo que solo el codigo de este modulo puede activar).
Nunca de claves de contexto ni de parametros que envie el cliente.
"""
import contextlib
import math
import threading

from odoo import _
from odoo.exceptions import AccessError, UserError

GROUP_MANAGER = "pos_order_integrity.group_pos_store_manager"
GROUP_SYSTEM = "base.group_system"
GROUP_POS_USER = "point_of_sale.group_pos_user"
GROUP_CASHIER = "pos_order_integrity.group_cashier_restricted"
# groups= sobre campos de sesion: DESACTIVADO por defecto (ver README, M7):
# asignar Field.groups tras el setup puede no surtir efecto y puede romper la
# validacion de vistas nativas al actualizar point_of_sale.
USE_FIELD_GROUPS = False
# Grupos con permiso de ver totales, diferencias y costos (coincide con
# COST_GROUPS de pos_order_integrity.models.product_template).
PRIV_GROUPS_CSV = "%s,%s" % (GROUP_MANAGER, GROUP_SYSTEM)

# Campos de pos.session que revelan totales esperados. Se protegen con
# groups= (ver _setup_complete en pos_session.py) y se filtran en read().
# TODO-VERIFICAR (Odoo 18): existencia y nombre de cada campo; los que no
# existan se ignoran sin error.
SESSION_SENSITIVE = (
    "cash_register_balance_end",
    "cash_register_difference",
    "cash_register_total_entry_encoding",
    "total_payments_amount",
    "order_count",
    "cash_real_expected",
    "cash_real_transaction",
    "cash_real_difference",
)
# Costos y margenes. No se protegen con groups= porque Odoo los calcula y
# escribe con el usuario de la sesion (ver README, decision 4); se filtran en
# read/_read_group/domain/export y en la precarga del POS.
COST_SENSITIVE = (
    "total_cost",
    "is_total_cost_computed",
    "margin",
    "margin_percent",
    "standard_price",
    # Instantanea de costo y costo manual definidos por pos_order_integrity.
    "pos_unit_cost",
    "pos_cost_known",
    "pos_cost_date",
    "pos_manual_cost",
)
ALL_SENSITIVE = frozenset(SESSION_SENSITIVE) | frozenset(COST_SENSITIVE)

MAX_COUNTED_CASH = 1e12

_state = threading.local()


# ----------------------------------------------------------------------
# Identidad
# ----------------------------------------------------------------------
def is_privileged(env):
    user = env.user
    return user.has_group(GROUP_MANAGER) or user.has_group(GROUP_SYSTEM)


def is_blind(env):
    """Usuario a quien se le ocultan totales: usuario POS (group_pos_user, que
    el grupo de cajero del guard implica) que no sea gerente de la cafeteria ni
    administrador tecnico. Un POS manager nativo SIN el grupo de gerente de la
    cafeteria tambien queda ciego (decision deliberada). Usuarios sin ningun
    grupo POS (p. ej. contabilidad) no se ven afectados (ver README, alcance).
    env.su lo activa solo codigo Python del servidor, nunca un cliente RPC.
    """
    if env.su:
        return False
    user = env.user
    if is_privileged(env):
        return False
    return user.has_group(GROUP_POS_USER) or user.has_group(GROUP_CASHIER)


# ----------------------------------------------------------------------
# Ventana interna (solo codigo de este modulo)
# ----------------------------------------------------------------------
def in_window():
    return getattr(_state, "depth", 0) > 0


@contextlib.contextmanager
def internal_window():
    """Mientras dura el bloque, el codigo propio de Odoo (sincronizar una venta,
    cerrar la sesion) puede leer los pedidos de la sesion del cajero. Una
    llamada RPC es una sola peticion en un solo hilo y no puede activar esto.
    """
    _state.depth = getattr(_state, "depth", 0) + 1
    try:
        yield
    finally:
        _state.depth -= 1


# ----------------------------------------------------------------------
# Filtros de datos
# ----------------------------------------------------------------------
def _base_name(name):
    return str(name).split(":")[0]


def strip_sensitive_payload(data):
    """Quita recursivamente las claves sensibles de dicts/listas (respuestas
    de sync_from_ui, load_data, etc.)."""
    if isinstance(data, dict):
        return {k: strip_sensitive_payload(v) for k, v in data.items()
                if k not in ALL_SENSITIVE}
    if isinstance(data, list):
        return [strip_sensitive_payload(v) for v in data]
    if isinstance(data, tuple):
        return tuple(strip_sensitive_payload(v) for v in data)
    return data


def filter_load_fields(env, fields_list):
    """Quita campos sensibles de la lista de campos que el POS precarga."""
    if not is_blind(env) or not isinstance(fields_list, (list, tuple, set, frozenset)):
        return fields_list
    kept = [f for f in fields_list if f not in ALL_SENSITIVE]
    return kept if isinstance(fields_list, list) else type(fields_list)(kept)


def filtered_read(model, reader, fields, load):
    """read() para usuarios ciegos sin los campos sensibles.

    reader es super().read ya enlazado. Dentro de la ventana interna no se
    filtra (el codigo de Odoo lo necesita); la respuesta al cliente se limpia
    aparte con strip_sensitive_payload.
    """
    if not is_blind(model.env) or in_window():
        return reader(fields, load=load)
    if fields:
        kept = [f for f in fields if _base_name(f) not in ALL_SENSITIVE]
        # Una lista vacia leeria TODOS los campos; pedir al menos id.
        return reader(kept or ["id"], load=load)
    rows = reader(fields, load=load)
    for row in rows:
        for name in ALL_SENSITIVE:
            row.pop(name, None)
    return rows


def check_text(env, *objects):
    """Rechaza si cualquier argumento (order=, groupby, aggregates, having,
    dominios de cualquier tipo, incluido un objeto Domain) menciona un campo
    sensible. Escaneo de texto deliberadamente conservador: falla cerrado.
    Cubre rutas (product_id.standard_price) y order='standard_price desc'."""
    if not is_blind(env) or in_window():
        return
    text = " ".join(str(o) for o in objects)
    for name in ALL_SENSITIVE:
        if name in text:
            raise AccessError(_("Operacion no permitida."))


def check_domain(env, domain, *args, **kwargs):
    """Dominio y order= de _search. No sustituye a las reglas; defensa en
    profundidad contra oraculos por busqueda. TODO-VERIFICAR: firma de _search
    en la version exacta (order puede llegar posicional o por nombre)."""
    check_text(env, domain, args, kwargs)


def check_group_args(env, groupby, aggregates, *args, **kwargs):
    check_text(env, groupby, aggregates, args, kwargs)


def block_export(env):
    """export_data es un metodo RPC publico que lee valores por atributo."""
    if is_blind(env) and not in_window():
        raise AccessError(_("Operacion no permitida."))


def apply_field_groups(model, names):
    """Pone groups= (solo gerente y administrador) a campos ya existentes.

    Se hace en _setup_complete y solo si el campo existe, para no crear campos
    nuevos por error si el nombre no es el de Odoo 18.
    TODO-VERIFICAR (Odoo 18): que asignar Field.groups tras el setup tenga
    efecto en check_field_access_rights (ver README).
    """
    if not USE_FIELD_GROUPS:
        return
    for name in names:
        field = model._fields.get(name)
        if field is not None:
            field.groups = PRIV_GROUPS_CSV


# ----------------------------------------------------------------------
# Validacion de montos
# ----------------------------------------------------------------------
def clean_counted_cash(value):
    """Efectivo contado enviado por el cliente: numero finito, no negativo, acotado.
    Los mensajes no incluyen valores esperados."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise UserError(_("El efectivo contado debe ser un numero."))
    value = float(value)
    if not math.isfinite(value) or value < 0 or value > MAX_COUNTED_CASH:
        raise UserError(_("El efectivo contado no es valido."))
    return value


_SYNC_ALLOWED_MODELS = (
    "pos.order", "pos.order.line", "pos.payment",
    "pos.pack.operation.lot", "product.attribute.custom.value",
)


def _rid(value):
    """id de un many2one serializado como int, [id, nombre] o (id, nombre)."""
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def filter_sync_result(result, submitted_uuids):
    """Respuesta de sync_from_ui para el cajero: SOLO pedidos cuyo uuid envio el
    propio cliente, mas sus lineas y pagos. Falla cerrado: sin uuid enviado, o
    fila de pedido sin uuid, no se devuelve nada. Modelos desconocidos se
    descartan. TODO-VERIFICAR: que las filas de pos.order de 18 traigan 'uuid',
    que pos.order.line traiga 'order_id' y pos.payment 'pos_order_id'; si no,
    la venta legitima volveria vacia (falla seguro, no filtra)."""
    submitted = set(submitted_uuids or ())
    if isinstance(result, list):
        return [r for r in result
                if isinstance(r, dict) and r.get("uuid") in submitted and submitted]
    if not isinstance(result, dict):
        return {}
    out = {}
    orders = [r for r in result.get("pos.order", []) or []
              if isinstance(r, dict) and r.get("uuid") in submitted] if submitted else []
    order_ids = {r.get("id") for r in orders}
    if "pos.order" in result:
        out["pos.order"] = orders
    lines = [r for r in result.get("pos.order.line", []) or []
             if isinstance(r, dict) and _rid(r.get("order_id")) in order_ids]
    line_ids = {r.get("id") for r in lines}
    if "pos.order.line" in result:
        out["pos.order.line"] = lines
    if "pos.payment" in result:
        out["pos.payment"] = [r for r in result["pos.payment"] or []
                              if isinstance(r, dict) and _rid(r.get("pos_order_id")) in order_ids]
    if "pos.pack.operation.lot" in result:
        out["pos.pack.operation.lot"] = [
            r for r in result["pos.pack.operation.lot"] or []
            if isinstance(r, dict) and _rid(r.get("pos_order_line_id")) in line_ids]
    if "product.attribute.custom.value" in result:
        out["product.attribute.custom.value"] = [
            r for r in result["product.attribute.custom.value"] or []
            if isinstance(r, dict) and _rid(r.get("pos_order_line_id")) in line_ids]
    return out
