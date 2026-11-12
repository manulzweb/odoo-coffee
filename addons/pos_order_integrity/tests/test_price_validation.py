from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import PosIntegrityCommon


@tagged("post_install", "-at_install", "pos_order_integrity")
class TestPriceValidation(PosIntegrityCommon):

    def test_cashier_sells_at_list_price(self):
        order = self._create_order(self.cashier, [self._line_vals(self.coffee, 2)])
        self.assertEqual(order.lines.price_unit, 3000.0)

    def test_cashier_cannot_lower_or_raise_price(self):
        for price in (1.0, 2999.0, 3001.0):
            with self.subTest(price=price), self.assertRaises(AccessError):
                self._create_order(self.cashier, [self._line_vals(self.coffee, 1, price=price)])

    def test_cashier_cannot_change_price_of_draft_line_by_write(self):
        order = self._create_order(self.cashier, [self._line_vals(self.coffee, 1)])
        with self.assertRaises(AccessError):
            order.lines.with_user(self.cashier).write({"price_unit": 100.0})

    def test_cashier_cannot_apply_discount(self):
        with self.assertRaises(AccessError):
            self._create_order(self.cashier, [self._line_vals(self.coffee, 1, discount=10.0)])
        order = self._create_order(self.cashier, [self._line_vals(self.coffee, 1)])
        with self.assertRaises(AccessError):
            order.lines.with_user(self.cashier).write({"discount": 5.0})

    def test_user_without_cashier_group_is_also_restricted(self):
        with self.assertRaises(AccessError):
            self._create_order(self.plain_pos_user, [self._line_vals(self.coffee, 1, price=1.0)])

    def test_manager_may_adjust_price_and_discount_before_confirmation(self):
        order = self._create_order(
            self.manager, [self._line_vals(self.coffee, 1, price=2500.0)])
        self.assertEqual(order.lines.price_unit, 2500.0)

    def test_invalid_numbers_rejected(self):
        for field, value in (("qty", float("nan")), ("price_unit", float("inf")),
                             ("discount", "10"), ("qty", True)):
            vals = self._line_vals(self.coffee, 1)
            vals[field] = value  # no pasar qty dos veces como kwarg
            with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                self.env["pos.order.line"].with_user(self.cashier).create(vals)

    def test_forged_line_subtotal_rejected(self):
        vals = self._line_vals(self.coffee, 2)
        vals["price_subtotal"] = vals["price_subtotal_incl"] = 1.0
        with self.assertRaises(AccessError):
            self._create_order(self.cashier, [vals], amount_total=1.0)

    def test_forged_order_total_rejected(self):
        with self.assertRaises(AccessError):
            self._create_order(self.cashier, [self._line_vals(self.coffee, 2)], amount_total=1.0)

    def test_weight_sale_250g_at_20000_per_kg_is_5000(self):
        """Sin subtotales fabricados: el 5.000 lo calcula el servidor, no el test.
        TODO-VERIFICAR: asume que price_subtotal/_incl son campos calculados en
        Odoo 18; si fueran obligatorios y no calculados, este create fallaria y
        el calculo deberia hacerse en el servidor antes de crear."""
        vals = self._line_vals(self.by_weight, 0.250, with_subtotals=False)
        self.assertNotIn("price_subtotal", vals)
        order = self._create_order(self.cashier, [vals], amount_total=5000.0)
        self.assertAlmostEqual(order.lines.price_subtotal, 5000.0, places=2)
        self.assertAlmostEqual(order.lines.price_subtotal_incl, 5000.0, places=2)

    def test_weight_sale_wrong_price_per_kg_rejected(self):
        with self.assertRaises(AccessError):
            self._create_order(
                self.cashier, [self._line_vals(self.by_weight, 0.250, price=10000.0)])

    def test_pricelist_and_fiscal_position_not_chosen_by_cashier(self):
        """TODO-VERIFICAR: tarifa y posicion fiscal ajenas a la caja se rechazan."""
        other_pricelist = self.env["product.pricelist"].create({"name": "Tarifa ajena test"})
        with self.assertRaises(AccessError):
            self._create_order(
                self.cashier, [self._line_vals(self.coffee, 1)], pricelist_id=other_pricelist.id)
        fpos = self.env["account.fiscal.position"].create({"name": "Posicion ajena test"})
        with self.assertRaises(AccessError):
            self._create_order(
                self.cashier, [self._line_vals(self.coffee, 1)], fiscal_position_id=fpos.id)
        order = self._create_order(self.cashier, [self._line_vals(self.coffee, 1)])
        with self.assertRaises(AccessError):
            order.with_user(self.cashier).write({"fiscal_position_id": fpos.id})

    def test_line_taxes_must_match_product_taxes(self):
        tax = self.env["account.tax"].create(
            {"name": "IVA ajeno test", "amount": 0.0, "amount_type": "percent",
             "type_tax_use": "sale"})
        vals = self._line_vals(self.coffee, 1, tax_ids=[(6, 0, [tax.id])])
        with self.assertRaises(AccessError):
            self._create_order(self.cashier, [vals])
