from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    job_title = fields.Char(string="Cargo")

    birthday = fields.Date(
        string="Cumpleaños",
        help="Solo se considera mes y día; el año se ignora"
    )

    role_id = fields.Many2one(
        "contact.role",
        string="Rol"
    )
