from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import PosIntegrityCommon


@tagged("post_install", "-at_install", "pos_order_integrity")
class TestQuantitiesAndModes(PosIntegrityCommon):

    def _assert_rejected(self, user, product, qty):
        with self.assertRaises(ValidationError):
            self._create_order(user, [self._line_vals(product, qty)])

    def test_unit_requires_positive_integer(self):
        self._create_order(self.cashier, [self._line_vals(self.coffee, 2)])
        for qty in (0.0, -1.0, 1.5):
            with self.subTest(qty=qty):
                self._assert_rejected(self.cashier, self.coffee, qty)

    def test_bag_requires_positive_integer(self):
        self._create_order(self.cashier, [self._line_vals(self.bag, 3)])
        for qty in (0.0, -2.0, 0.5):
            with self.subTest(qty=qty):
                self._assert_rejected(self.cashier, self.bag, qty)

    def test_weight_requires_positive_value(self):
        self._create_order(self.cashier, [self._line_vals(self.by_weight, 0.250)])
        for qty in (0.0, -0.1):
            with self.subTest(qty=qty):
                self._assert_rejected(self.cashier, self.by_weight, qty)

    def test_weight_more_than_three_decimals_rejected_not_rounded(self):
        self._assert_rejected(self.cashier, self.by_weight, 0.1255)

    def test_raw_weight_checked_before_field_rounding_on_create_and_write(self):
        """El campo qty redondea (2 decimales por defecto) y ocultaria 0,1255;
        la regla valida el valor crudo de vals antes de super()."""
        for qty in (0.1255, 0.0004, 1.0005):
            with self.subTest(op="create", qty=qty), self.assertRaises(ValidationError):
                self.env["pos.order.line"].with_user(self.cashier).create(
                    self._line_vals(self.by_weight, qty, order_id=self._draft().id))
        line = self._draft().lines
        with self.assertRaises(ValidationError):
            line.with_user(self.cashier).write({"qty": 0.1255})

    def test_raw_fractional_unit_checked_before_rounding(self):
        line = self._draft().lines
        with self.assertRaises(ValidationError):
            line.with_user(self.cashier).write({"qty": 1.004})

    def _draft(self):
        return self._create_order(self.cashier, [self._line_vals(self.coffee, 1)])

    def test_quantity_rules_also_apply_to_manager(self):
        self._assert_rejected(self.manager, self.coffee, -1.0)
        self._assert_rejected(self.manager, self.by_weight, 0.0)

    def test_weight_mode_requires_kg_uom(self):
        with self.assertRaises(ValidationError):
            self.coffee.product_tmpl_id.write({"pos_sale_mode": "weight"})

    def test_kg_product_must_be_weight_mode(self):
        with self.assertRaises(ValidationError):
            self.by_weight.product_tmpl_id.write({"pos_sale_mode": "unit"})

    def test_bag_requires_units_per_bag(self):
        with self.assertRaises(ValidationError):
            self.bag.product_tmpl_id.write({"pos_units_per_bag": 0})
