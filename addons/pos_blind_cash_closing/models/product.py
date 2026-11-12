from odoo import api, models

from . import blind_common as bc


class ProductProduct(models.Model):
    _inherit = "product.product"

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

    @api.model
    def _load_pos_data_fields(self, *args, **kwargs):
        # Odoo 18 precarga standard_price del producto en el navegador del POS.
        # TODO-VERIFICAR: nombre y firma del metodo; modelo product.product vs
        # product.template en la precarga de esta version.
        return bc.filter_load_fields(self.env, super()._load_pos_data_fields(*args, **kwargs))


class ProductTemplate(models.Model):
    _inherit = "product.template"

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

    @api.model
    def _load_pos_data_fields(self, *args, **kwargs):
        return bc.filter_load_fields(self.env, super()._load_pos_data_fields(*args, **kwargs))
