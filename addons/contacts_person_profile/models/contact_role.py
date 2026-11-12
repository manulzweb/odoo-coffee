from odoo import models, fields

class ContactRole(models.Model):
    _name = "contact.role"
    _description = "Contact Role"
    _rec_name = "name"

    name = fields.Char(string="Rol", required=True)
    active = fields.Boolean(default=True)
