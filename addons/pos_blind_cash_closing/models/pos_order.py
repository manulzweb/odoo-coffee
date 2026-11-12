from odoo import api, models

from . import blind_common as bc


def _submitted_uuids(orders):
    """uuid de los pedidos que el cliente envio a sincronizar (formatos 17/18)."""
    found = set()
    for order in orders or []:
        if not isinstance(order, dict):
            continue
        data = order.get("data") if isinstance(order.get("data"), dict) else order
        for key in ("uuid", "uid"):
            if data.get(key):
                found.add(data[key])
    return found


class PosOrder(models.Model):
    _inherit = "pos.order"

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

    def onchange(self, *args, **kwargs):
        # onchange devuelve valores calculados (costos, margenes) sin pasar por read().
        bc.block_export(self.env)
        return super().onchange(*args, **kwargs)

    @api.model
    def _load_pos_data_fields(self, *args, **kwargs):
        # TODO-VERIFICAR (Odoo 18): metodo de precarga del POS.
        return bc.filter_load_fields(self.env, super()._load_pos_data_fields(*args, **kwargs))

    @api.model
    def sync_from_ui(self, orders, *args, **kwargs):
        """Venta enviada por el POS del cajero.

        NO se usa sudo(): pos_order_integrity valida precios, descuentos y
        totales con el usuario real y trata env.su como codigo interno de
        confianza; un sudo aqui anularia esos controles. En su lugar se abre la
        ventana interna, que solo permite a las reglas de registro (ir.rule)
        dejar leer los pedidos de la sesion del propio cajero mientras corre
        el codigo de Odoo. La respuesta se filtra antes de salir.
        TODO-VERIFICAR (Odoo 18): nombre y forma de sync_from_ui/create_from_ui.
        """
        if not bc.is_blind(self.env):
            return super().sync_from_ui(orders, *args, **kwargs)
        submitted = _submitted_uuids(orders)
        with bc.internal_window():
            result = super().sync_from_ui(orders, *args, **kwargs)
        result = bc.strip_sensitive_payload(result)
        # Falla cerrado: solo pedidos cuyo uuid envio el cliente, con sus
        # lineas y pagos; ningun importe de pedidos no enviados.
        return bc.filter_sync_result(result, submitted)

    @api.model
    def search_paid_order_ids(self, *args, **kwargs):
        """Historial de la pantalla de tickets: no existe para el cajero.
        TODO-VERIFICAR (Odoo 18): firma y forma de la respuesta de la pantalla
        de tickets del POS (si espera otra clave, la interfaz mostrara error
        o lista vacia; ambos son aceptables)."""
        if bc.is_blind(self.env):
            return {"ordersInfo": [], "totalCount": 0}
        return super().search_paid_order_ids(*args, **kwargs)


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

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

    def onchange(self, *args, **kwargs):
        bc.block_export(self.env)
        return super().onchange(*args, **kwargs)

    @api.model
    def _load_pos_data_fields(self, *args, **kwargs):
        return bc.filter_load_fields(self.env, super()._load_pos_data_fields(*args, **kwargs))
