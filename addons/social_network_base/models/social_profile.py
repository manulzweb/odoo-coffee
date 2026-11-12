from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class SocialProfile(models.Model):
    _name = "social.profile"
    _description = "Social Profile"
    _rec_name = "url"

    partner_id = fields.Many2one(
        "res.partner",
        string="Contacto",
        required=True,
        ondelete="cascade"
    )

    network = fields.Selection([
        ("linkedin", "LinkedIn"),
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("x", "X (Twitter)"),
        ("tiktok", "TikTok"),
    ], required=True)

    url = fields.Char(required=True)

    active = fields.Boolean(default=True)

    @api.model
    def _reference_models(self):
        return [
            ('res.partner', 'Contacto'),
        ]

    # 🔒 Validación básica de URL
    @api.constrains("url")
    def _check_url(self):
        pattern = re.compile(
            r'^(https?:\/\/)?([\w\-]+\.)+[\w\-]+(\/[\w\-._~:/?#[\]@!$&\'()*+,;=]*)?$'
        )
        for record in self:
            if record.url and not pattern.match(record.url):
                raise ValidationError("La URL no es válida.")
