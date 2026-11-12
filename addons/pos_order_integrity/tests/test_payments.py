from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import PosIntegrityCommon


@tagged("post_install", "-at_install", "pos_order_integrity")
class TestPaymentsAndConfirmation(PosIntegrityCommon):

    def _draft(self, qty=2):
        return self._create_order(self.cashier, [self._line_vals(self.coffee, qty)])

    def test_empty_order_with_negative_total_rejected(self):
        """Orden vacia con total negativo (y pago negativo en efectivo)."""
        with self.assertRaises(AccessError):
            self.env["pos.order"].with_user(self.cashier).create(
                self._order_vals([], amount_total=-5000.0))

    def test_empty_order_cannot_be_confirmed(self):
        order = self.env["pos.order"].with_user(self.cashier).create(self._order_vals([]))
        with self.assertRaises(AccessError):
            order.with_user(self.cashier).write({"state": "paid"})

    def test_negative_payment_on_empty_order_rejected(self):
        order = self.env["pos.order"].with_user(self.cashier).create(self._order_vals([]))
        with self.assertRaises(AccessError):
            self._pay(order, amount=-5000.0)

    def test_paid_without_payments_rejected(self):
        order = self._draft()
        with self.assertRaises(AccessError):
            order.with_user(self.cashier).write({"state": "paid"})
        self.assertEqual(order.state, "draft")

    def test_paid_with_partial_or_excess_payment_rejected(self):
        for amount in (1.0, 5999.0, 6001.0):
            with self.subTest(amount=amount):
                order = self._draft()
                self._pay(order, amount=amount)
                with self.assertRaises(AccessError):
                    order.with_user(self.cashier).write({"state": "paid"})

    def test_paid_with_exact_payment_accepted(self):
        order = self._draft()
        self._pay(order)
        order.with_user(self.cashier).write({"state": "paid"})
        self.assertEqual(order.state, "paid")

    def test_negative_or_zero_payment_rejected(self):
        order = self._draft()
        for amount in (-1.0, 0.0):
            with self.subTest(amount=amount), self.assertRaises(AccessError):
                self._pay(order, amount=amount)

    def test_change_line_must_be_negative_and_cash(self):
        """Solo la linea nativa de cambio puede ser negativa. TODO-VERIFICAR
        campo is_change y metodo de efectivo (is_cash_count) en Odoo 18."""
        order = self._draft()
        with self.assertRaises(AccessError):
            self._pay(order, amount=100.0, is_change=True)
        with self.assertRaises(AccessError):
            self._pay(order, amount=-100.0, is_change=True)  # metodo de prueba no es efectivo

    def test_payment_method_must_belong_to_the_order_config(self):
        order = self._draft()
        with self.assertRaises(AccessError):
            self._pay(order, method=self.foreign_pay_method)

    def test_payments_on_confirmed_order_rejected_for_cashier(self):
        order = self._confirmed_order()
        with self.assertRaises(AccessError):
            self._pay(order, amount=1.0)
        with self.assertRaises(AccessError):
            order.payment_ids.with_user(self.cashier).write({"amount": 1.0})
        with self.assertRaises(AccessError):
            order.payment_ids.with_user(self.cashier).unlink()

    def test_cashier_can_edit_or_remove_payment_of_draft_order(self):
        order = self._draft()
        pay = self._pay(order, amount=1000.0)
        pay.with_user(self.cashier).write({"amount": 6000.0})
        self.assertEqual(pay.amount, 6000.0)
        pay.with_user(self.cashier).unlink()
        self.assertFalse(pay.exists())

    def test_manager_payment_change_on_confirmed_order_is_audited(self):
        order = self._confirmed_order()
        order.payment_ids.with_user(self.manager).write({"amount": 5000.0})
        log = self.env["pos.order.audit.log"].search(
            [("order_id", "=", order.id), ("action", "=", "correction")])
        self.assertEqual(len(log), 1)
        self.assertEqual(log.user_id, self.manager)

    # -- efectivo con cambio y pago mixto (logica de suma neta) -----------
    def test_cash_payment_with_change_accepted(self):
        """Total 6.000; entrega 10.000 en efectivo; cambio -4.000 en efectivo.
        La suma neta de pagos (10.000 - 4.000) iguala el total.
        TODO-VERIFICAR: que el fixture de efectivo sea de tipo cash y que Odoo 18
        cree el cambio como pago negativo con is_change."""
        order = self._draft()
        self._pay(order, amount=10000.0, method=self.cash_method)
        self._pay(order, amount=-4000.0, method=self.cash_method, is_change=True)
        order.with_user(self.cashier).write({"state": "paid"})
        self.assertEqual(order.state, "paid")
        self.assertAlmostEqual(sum(order.payment_ids.mapped("amount")), order.amount_total)

    def test_cash_overpayment_without_change_line_rejected(self):
        order = self._draft()
        self._pay(order, amount=10000.0, method=self.cash_method)
        with self.assertRaises(AccessError):
            order.with_user(self.cashier).write({"state": "paid"})

    def test_change_larger_than_cash_received_rejected(self):
        """Nequi 8.000 + cambio -2.000 en efectivo sin haber recibido efectivo:
        la suma neta cuadra (6.000) pero el cambio no sale de efectivo cobrado."""
        order = self._draft()
        self._pay(order, amount=8000.0, method=self.nequi_method)
        self._pay(order, amount=-2000.0, method=self.cash_method, is_change=True)
        with self.assertRaises(AccessError):
            order.with_user(self.cashier).write({"state": "paid"})

    def test_change_line_in_non_cash_method_rejected(self):
        order = self._draft()
        with self.assertRaises(AccessError):
            self._pay(order, amount=-1000.0, method=self.nequi_method, is_change=True)

    def test_mixed_cash_and_nequi_accepted_when_net_sum_matches(self):
        order = self._draft()
        self._pay(order, amount=2000.0, method=self.cash_method)
        self._pay(order, amount=4000.0, method=self.nequi_method)
        order.with_user(self.cashier).write({"state": "paid"})
        self.assertEqual(order.state, "paid")

    def test_mixed_cash_and_nequi_rejected_when_net_sum_short(self):
        order = self._draft()
        self._pay(order, amount=2000.0, method=self.cash_method)
        self._pay(order, amount=3000.0, method=self.nequi_method)
        with self.assertRaises(AccessError):
            order.with_user(self.cashier).write({"state": "paid"})

    def test_mixed_with_cash_overpayment_and_change(self):
        """Nequi 4.000 + efectivo 5.000 (total 9.000 para 6.000) con cambio -3.000."""
        order = self._draft()
        self._pay(order, amount=4000.0, method=self.nequi_method)
        self._pay(order, amount=5000.0, method=self.cash_method)
        self._pay(order, amount=-3000.0, method=self.cash_method, is_change=True)
        order.with_user(self.cashier).write({"state": "paid"})
        self.assertEqual(order.state, "paid")
