from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    client_type_id = fields.Many2one(
        'company.client.type',
        string="Tipo de Cliente"
    )

    company_size_id = fields.Many2one(
        'company.size',
        string="Tamaño de la Empresa"
    )

    employee_qty = fields.Integer(
        string="Cantidad de Empleados"
    )

    sector_siren_id = fields.Many2one(
        'company.sector.siren',
        string="Sector Siren"
    )

    ciiu_main = fields.Char(
        string="CIIU Principal"
    )

    macro_sector_id = fields.Many2one(
        'company.macro.sector',
        string="Macro Sector"
    )

    consumption_profile_id = fields.Many2one(
        'company.consumption.profile',
        string="Perfil de Consumo"
    )

    social_profile_ids = fields.One2many(
        "social.profile",
        "partner_id",
        string="Redes Sociales",
    )