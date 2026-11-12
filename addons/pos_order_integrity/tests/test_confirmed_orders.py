from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import PosIntegrityCommon


@tagged("post_install", "-at_install", "pos_order_integrity")
class TestConfirmedOrders(PosIntegrityCommon):

    def test_cashier_cannot_create_order_in_non_draft_state(self):
        for state in ("paid", "done", "cancel", "invoiced"):
            with self.subTest(state=state), self.assertRaises(AccessError):
                self._create_order(self.cashier, [self._line_vals(self.coffee, 1)], state=state)

    def test_cashier_cannot_modify_confirmed_order_line(self):
        order = self._confirmed_order()
        for vals in ({"price_unit": 1.0}, {"qty": 1.0}, {"discount": 50.0},
                     {"product_id": self.bag.id}):
            with self.subTest(vals=vals), self.assertRaises(AccessError):
                order.lines.with_user(self.cashier).write(vals)

    def test_cashier_cannot_modify_confirmed_order_fields(self):
        order = self._confirmed_order()
        with self.assertRaises(AccessError):
            order.with_user(self.cashier).write({"amount_total": 1.0})
        with self.assertRaises(AccessError):
            order.with_user(self.cashier).write({"note": "corregido"})

    def test_cashier_cannot_add_or_delete_lines_of_confirmed_order(self):
        order = self._confirmed_order()
        with self.assertRaises(AccessError):
            self.env["pos.order.line"].with_user(self.cashier).create(
                self._line_vals(self.coffee, 1, order_id=order.id))
        with self.assertRaises(AccessError):
            order.lines.with_user(self.cashier).unlink()

    def test_cashier_cannot_delete_or_cancel_confirmed_order(self):
        order = self._confirmed_order()
        with self.assertRaises(AccessError):
            order.with_user(self.cashier).unlink()
        with self.assertRaises(AccessError):
            order.with_user(self.cashier).write({"state": "cancel"})

    def test_cashier_can_cancel_draft_order_without_payments(self):
        """remove_from_ui puede escribir 'cancel' antes de eliminar el carrito.
        TODO-VERIFICAR la secuencia real de remove_from_ui en Odoo 18."""
        order = self._create_order(self.cashier, [self._line_vals(self.coffee, 1)])
        order.with_user(self.cashier).write({"state": "cancel"})
        self.assertEqual(order.state, "cancel")

    def test_cashier_cannot_cancel_draft_order_with_payments(self):
        order = self._create_order(self.cashier, [self._line_vals(self.coffee, 1)])
        self._pay(order)
        with self.assertRaises(AccessError):
            order.with_user(self.cashier).write({"state": "cancel"})

    def test_cashier_cannot_cancel_confirmed_order_via_cancel_state(self):
        order = self._confirmed_order()
        with self.assertRaises(AccessError):
            order.with_user(self.cashier).write({"state": "cancel"})

    def test_cashier_cannot_reopen_confirmed_order(self):
        order = self._confirmed_order()
        with self.assertRaises(AccessError):
            order.with_user(self.cashier).write({"state": "draft"})

    def test_cashier_can_follow_normal_state_flow(self):
        """paid -> done lo provoca el cierre de sesion de Odoo con el usuario del cajero."""
        order = self._create_order(self.cashier, [self._line_vals(self.coffee, 1)])
        self._pay(order)
        order.with_user(self.cashier).write({"state": "paid"})
        order.with_user(self.cashier).write({"state": "done"})
        self.assertEqual(order.state, "done")

    def test_cashier_can_discard_draft_cart(self):
        # TODO-VERIFICAR: requiere perm_unlink de pos.order para group_pos_user (ACL nativa).
        order = self._create_order(self.cashier, [self._line_vals(self.coffee, 1)])
        order.with_user(self.cashier).unlink()
        self.assertFalse(order.exists())
