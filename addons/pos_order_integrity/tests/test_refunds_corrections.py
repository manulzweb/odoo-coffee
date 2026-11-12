import json

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged

from .common import PosIntegrityCommon


@tagged("post_install", "-at_install", "pos_order_integrity")
class TestRefundsAndCorrections(PosIntegrityCommon):

    def _refund_vals(self, original_line, qty=-1.0):
        return self._line_vals(
            self.coffee, qty, refunded_orderline_id=original_line.id)

    def test_cashier_cannot_create_refund(self):
        original = self._confirmed_order().lines
        with self.assertRaises(AccessError):
            self._create_order(self.cashier, [self._refund_vals(original)])

    def test_negative_quantity_without_refund_link_is_invalid_for_everyone(self):
        for user in (self.cashier, self.manager):
            with self.subTest(user=user.login), self.assertRaises(ValidationError):
                self._create_order(user, [self._line_vals(self.coffee, -1.0)])

    def test_manager_refund_is_logged_with_author_and_date_without_reason(self):
        original = self._confirmed_order().lines
        order = self._create_order(self.manager, [self._refund_vals(original)])
        log = self.env["pos.order.audit.log"].search([("order_id", "=", order.id)])
        self.assertEqual(len(log), 1)
        self.assertEqual(log.action, "refund")
        self.assertEqual(log.user_id, self.manager)
        self.assertTrue(log.date)
        self.assertFalse(log.reason)

    def test_manager_refund_with_optional_reason(self):
        original = self._confirmed_order().lines
        order = self.env["pos.order"].with_user(self.manager).with_context(
            pos_audit_reason="Cliente devolvio el cafe").create(
            self._order_vals([self._refund_vals(original)]))
        log = self.env["pos.order.audit.log"].search([("order_id", "=", order.id)])
        self.assertEqual(log.reason, "Cliente devolvio el cafe")

    def test_manager_correction_of_confirmed_line_is_logged(self):
        order = self._confirmed_order([self._line_vals(self.coffee, 2)])
        order.lines.with_user(self.manager).write({"qty": 1.0})
        log = self.env["pos.order.audit.log"].search(
            [("order_id", "=", order.id), ("action", "=", "correction")])
        self.assertEqual(len(log), 1)
        self.assertEqual(log.user_id, self.manager)
        detail = json.loads(log.detail)
        self.assertIn("qty", detail["campos"])
        self.assertEqual(detail["antes"][str(order.lines.id)]["qty"], 2.0)

    def test_manager_correction_of_confirmed_order_field_is_logged(self):
        order = self._confirmed_order()
        order.with_user(self.manager).write({"note": "ajuste"})
        log = self.env["pos.order.audit.log"].search(
            [("order_id", "=", order.id), ("action", "=", "correction")])
        self.assertEqual(len(log), 1)

    def test_manager_edit_of_draft_order_is_not_logged(self):
        order = self._create_order(self.manager, [self._line_vals(self.coffee, 1)])
        order.lines.with_user(self.manager).write({"qty": 2.0})
        self.assertFalse(self.env["pos.order.audit.log"].search([("order_id", "=", order.id)]))

    def test_audit_log_is_immutable_and_hidden_from_cashier(self):
        original = self._confirmed_order().lines
        order = self._create_order(self.manager, [self._refund_vals(original)])
        log = self.env["pos.order.audit.log"].search([("order_id", "=", order.id)])
        with self.assertRaises(AccessError):
            log.with_user(self.manager).write({"reason": "borrado"})
        with self.assertRaises(AccessError):
            log.with_user(self.manager).unlink()
        with self.assertRaises(AccessError):
            log.with_user(self.cashier).read(["detail"])
