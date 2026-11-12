from odoo import models

from . import blind_common as bc


class PosPayment(models.Model):
    _inherit = "pos.payment"

    def read(self, fields=None, load="_classic_read"):
        return bc.filtered_read(self, super().read, fields, load)

    def _search(self, domain, *args, **kwargs):
        bc.check_domain(self.env, domain, *args, **kwargs)
        return super()._search(domain, *args, **kwargs)

    def export_data(self, *args, **kwargs):
        bc.block_export(self.env)
        return super().export_data(*args, **kwargs)
