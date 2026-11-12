from odoo import models, fields

class ClientType(models.Model):
    _name = 'company.client.type'
    _description = 'Tipo de Cliente'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class CompanySize(models.Model):
    _name = 'company.size'
    _description = 'Tamaño de Empresa'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class SectorSiren(models.Model):
    _name = 'company.sector.siren'
    _description = 'Sector Siren'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class MacroSector(models.Model):
    _name = 'company.macro.sector'
    _description = 'Macro Sector'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class ConsumptionProfile(models.Model):
    _name = 'company.consumption.profile'
    _description = 'Perfil de Consumo'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
