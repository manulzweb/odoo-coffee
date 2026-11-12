from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero

from .guard import GROUP_MANAGER, GROUP_SYSTEM

COST_GROUPS = "%s,%s" % (GROUP_MANAGER, GROUP_SYSTEM)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    pos_sale_mode = fields.Selection(
        [("unit", "Unidad"), ("bag", "Bolsa"), ("weight", "Peso (kg)")],
        string="Venta por",
        default="unit",
        required=True,
        help="Unidad y bolsa: cantidad entera. Peso: cantidad en kg, positiva, "
             "hasta 3 decimales; el precio de lista es COP por kg.",
    )
    pos_units_per_bag = fields.Integer(
        string="Unidades por bolsa",
        help="Informativo (p. ej. 10 para el pan de bolita). La relacion con "
             "existencias esta pendiente de confirmar y no afecta ventas.",
    )
    # Un costo desconocido NO es cero: el ORM devuelve 0.0 para un Float vacio,
    # asi que 'sin costo' se representa con un indicador explicito.
    pos_cost_known = fields.Boolean(
        string="Costo conocido", default=False, groups=COST_GROUPS,
        help="Desmarcado = sin costo registrado (el margen es desconocido, no 100 %).",
    )
    pos_manual_cost = fields.Float(
        string="Costo manual", digits="Product Price", groups=COST_GROUPS,
        help="Solo tiene significado si 'Costo conocido' esta marcado; 0 con el "
             "indicador marcado significa costo cero real.",
    )

    @api.model
    def _pos_normalize_cost_vals(self, vals):
        """Coherencia entre indicador y valor.

        - Desmarcar el indicador (o vaciar el costo con None/False) => desconocido, costo 0.
        - Escribir un numero sin indicar nada => se entiende que el costo es conocido.
        """
        if "pos_manual_cost" in vals and (
                vals["pos_manual_cost"] is None or vals["pos_manual_cost"] is False):
            vals["pos_cost_known"] = False
        if "pos_cost_known" in vals and not vals["pos_cost_known"]:
            vals["pos_manual_cost"] = 0.0
            vals["pos_cost_known"] = False
        elif "pos_manual_cost" in vals and "pos_cost_known" not in vals:
            vals["pos_cost_known"] = True
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._pos_normalize_cost_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._pos_normalize_cost_vals(vals)
        return super().write(vals)

    @api.constrains("pos_manual_cost", "pos_cost_known")
    def _check_pos_cost(self):
        # sudo: la validacion no debe depender de que quien escribe lea el campo.
        for tmpl in self.sudo():
            if tmpl.pos_manual_cost < 0:
                raise ValidationError(_("El costo manual no puede ser negativo."))
            if not tmpl.pos_cost_known and not float_is_zero(
                    tmpl.pos_manual_cost, precision_digits=6):
                raise ValidationError(
                    _("Hay un costo escrito pero 'Costo conocido' esta desmarcado."))

    @api.constrains("pos_sale_mode", "pos_units_per_bag", "uom_id")
    def _check_pos_sale_mode(self):
        kg_categ = self.env.ref("uom.product_uom_categ_kgm")    # TODO-VERIFICAR xmlid
        unit_categ = self.env.ref("uom.product_uom_categ_unit")  # TODO-VERIFICAR xmlid
        for tmpl in self:
            categ = tmpl.uom_id.category_id
            if tmpl.pos_sale_mode == "weight" and categ != kg_categ:
                raise ValidationError(
                    _("'%s': venta por peso exige unidad de medida en kg.", tmpl.display_name))
            if tmpl.pos_sale_mode != "weight" and categ == kg_categ:
                raise ValidationError(
                    _("'%s': un producto medido en kg debe venderse por peso.", tmpl.display_name))
            if tmpl.pos_sale_mode == "bag":
                if categ != unit_categ:
                    raise ValidationError(
                        _("'%s': la bolsa se cuenta en unidades enteras.", tmpl.display_name))
                if tmpl.pos_units_per_bag < 1:
                    raise ValidationError(
                        _("'%s': indique cuantas unidades trae la bolsa.", tmpl.display_name))
