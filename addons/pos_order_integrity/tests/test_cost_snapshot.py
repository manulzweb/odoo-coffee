from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import PosIntegrityCommon


@tagged("post_install", "-at_install", "pos_order_integrity")
class TestCostSnapshot(PosIntegrityCommon):

    def test_new_product_cost_is_unknown_not_zero(self):
        tmpl = self.coffee.product_tmpl_id.sudo()
        self.assertFalse(tmpl.pos_cost_known)

    def test_zero_cost_is_known_and_differs_from_unknown(self):
        tmpl = self.coffee.product_tmpl_id.sudo()
        tmpl.write({"pos_manual_cost": 0.0})
        self.assertTrue(tmpl.pos_cost_known)
        self.assertEqual(tmpl.pos_manual_cost, 0.0)

    def test_entering_a_cost_marks_it_known_and_clearing_resets_it(self):
        tmpl = self.coffee.product_tmpl_id.sudo()
        tmpl.write({"pos_manual_cost": 1500.0})
        self.assertTrue(tmpl.pos_cost_known)
        tmpl.write({"pos_cost_known": False})
        self.assertFalse(tmpl.pos_cost_known)
        self.assertEqual(tmpl.pos_manual_cost, 0.0)

    def test_negative_cost_rejected(self):
        with self.assertRaises(ValidationError):
            self.coffee.product_tmpl_id.sudo().write({"pos_manual_cost": -1.0})

    def test_cost_fields_hidden_from_cashier(self):
        """Robusto a ambos comportamientos: AccessError al leer el campo, o bien
        (con otro modulo de privacidad instalado, p. ej. cierre ciego) lectura
        sin error pero sin exponer el valor real."""
        self._set_cost(self.coffee, 1500.0)
        tmpl = self.coffee.product_tmpl_id.with_user(self.cashier)
        try:
            rows = tmpl.read(["pos_manual_cost", "pos_cost_known"])
        except AccessError:
            pass
        else:
            row = rows[0] if rows else {}
            self.assertNotEqual(row.get("pos_manual_cost"), 1500.0)
            self.assertFalse(row.get("pos_cost_known"))
        with self.assertRaises(AccessError):
            tmpl.write({"pos_manual_cost": 1.0})

    def test_manager_can_read_and_write_cost(self):
        tmpl = self.coffee.product_tmpl_id.with_user(self.manager)
        tmpl.write({"pos_manual_cost": 1200.0})
        self.assertEqual(tmpl.read(["pos_manual_cost"])[0]["pos_manual_cost"], 1200.0)

    def test_snapshot_taken_on_confirmation_and_survives_cost_change(self):
        self._set_cost(self.coffee, 1500.0)
        order = self._create_order(self.cashier, [self._line_vals(self.coffee, 2)])
        self.assertFalse(order.lines.pos_cost_date)  # aun en borrador
        self._pay(order)
        order.with_user(self.cashier).write({"state": "paid"})
        line = order.lines
        self.assertTrue(line.pos_cost_known)
        self.assertEqual(line.pos_unit_cost, 1500.0)
        self._set_cost(self.coffee, 2500.0)
        self.assertEqual(line.pos_unit_cost, 1500.0)
        self.assertAlmostEqual(line._pos_line_margin(), 6000.0 - 3000.0)

    def test_unknown_cost_line_has_no_margin(self):
        order = self._confirmed_order([self._line_vals(self.coffee, 1)])
        self.assertFalse(order.lines.pos_cost_known)
        self.assertIsNone(order.lines._pos_line_margin())

    def test_zero_cost_line_has_margin_equal_to_subtotal(self):
        self._set_cost(self.coffee, 0.0)
        order = self._confirmed_order([self._line_vals(self.coffee, 1)])
        self.assertTrue(order.lines.pos_cost_known)
        self.assertAlmostEqual(order.lines._pos_line_margin(), 3000.0)

    def test_snapshot_cannot_be_overwritten_by_anyone_but_server_code(self):
        self._set_cost(self.coffee, 1500.0)
        line = self._confirmed_order().lines
        for user in (self.cashier, self.manager):
            with self.subTest(user=user.login), self.assertRaises(AccessError):
                line.with_user(user).write({"pos_unit_cost": 1.0})

    def test_snapshot_is_not_retaken_once_set(self):
        self._set_cost(self.coffee, 1500.0)
        order = self._confirmed_order()
        self._set_cost(self.coffee, 9999.0)
        order.sudo().write({"state": "done"})
        self.assertEqual(order.lines.pos_unit_cost, 1500.0)

    def test_refund_line_inherits_original_historic_cost(self):
        self._set_cost(self.coffee, 1500.0)
        original = self._confirmed_order([self._line_vals(self.coffee, 2)]).lines
        self._set_cost(self.coffee, 2500.0)
        refund = self._create_order(self.manager, [self._line_vals(
            self.coffee, -1.0, refunded_orderline_id=original.id)])
        refund.sudo().write({"state": "paid"})
        self.assertEqual(refund.lines.pos_unit_cost, 1500.0)
