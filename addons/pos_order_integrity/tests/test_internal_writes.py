"""Caso central del rediseño: el control NO debe bloquear las escrituras internas
legitimas de Odoo (costo tras el pago) y TAMPOCO confiar en datos del cliente."""
import unittest

from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import PosIntegrityCommon


@tagged("post_install", "-at_install", "pos_order_integrity")
class TestInternalWrites(PosIntegrityCommon):

    def test_odoo_cost_write_after_payment_with_cashier_user_is_allowed(self):
        """Odoo escribe total_cost/is_total_cost_computed con el usuario de la
        sesion, sin sudo, justo despues de marcar el pedido como pagado."""
        order = self._create_order(self.cashier, [self._line_vals(self.coffee, 2)])
        self._pay(order)
        order.with_user(self.cashier).write({"state": "paid"})
        order.lines.with_user(self.cashier).write(
            {"total_cost": 3000.0, "is_total_cost_computed": True})
        self.assertTrue(order.lines.is_total_cost_computed)

    def test_native_cost_cannot_be_rewritten_once_computed(self):
        order = self._confirmed_order()
        order.lines.sudo().write({"total_cost": 100.0, "is_total_cost_computed": True})
        with self.assertRaises(AccessError):
            order.lines.with_user(self.cashier).write({"total_cost": 0.0})

    def test_cost_snapshot_does_not_need_cashier_write_rights(self):
        self._set_cost(self.coffee, 1500.0)
        order = self._create_order(self.cashier, [self._line_vals(self.coffee, 1)])
        self._pay(order)
        order.with_user(self.cashier).write({"state": "paid"})
        self.assertEqual(order.lines.pos_unit_cost, 1500.0)

    def test_context_flags_do_not_bypass_guard(self):
        order = self._confirmed_order()
        for key in ("pos_internal", "skip_guard", "install_mode", "tracking_disable",
                    "force_write", "_pos_internal_write", "mail_notrack"):
            with self.subTest(key=key), self.assertRaises(AccessError):
                order.lines.with_user(self.cashier).with_context(**{key: True}).write(
                    {"price_unit": 1.0})

    def test_cashier_cannot_set_client_side_role_or_manager_id(self):
        """Un identificador de empleado/gerente enviado por el cliente no autoriza."""
        order = self._confirmed_order()
        ctx = {"manager_id": self.manager.id, "employee_role": "manager", "uid": self.manager.id}
        with self.assertRaises(AccessError):
            order.lines.with_user(self.cashier).with_context(**ctx).write({"qty": 1.0})

    def test_full_odoo_payment_flow_with_cashier(self):
        """Flujo real: add_payment + action_pos_order_paid + calculo de costo."""
        raise unittest.SkipTest(
            "TODO-VERIFICAR: requiere metodo de pago y sesion abierta reales; "
            "completar en el entorno aislado llamando a order.add_payment(...), "
            "order.action_pos_order_paid() y al calculo de costo nativo con el "
            "usuario cajero, y comprobar que ninguna escritura es rechazada.")
