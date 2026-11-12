from types import SimpleNamespace

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..models.guard import cash_methods, is_cash_method


def _fake_method(fields_present, **attrs):
    """Metodo simulado: solo expone _fields y los atributos indicados."""
    return SimpleNamespace(_fields={name: object() for name in fields_present}, **attrs)


@tagged("post_install", "-at_install", "pos_order_integrity")
class TestCashMethodHelper(TransactionCase):
    """Cubre los dos caminos de is_cash_method con un metodo simulado y la
    ausencia de ambos campos (falla cerrado con UserError)."""

    def test_type_path_is_preferred_when_field_exists(self):
        self.assertTrue(is_cash_method(_fake_method(["type"], type="cash")))
        self.assertFalse(is_cash_method(_fake_method(["type"], type="bank")))
        # Si existen ambos, manda type aunque is_cash_count diga otra cosa.
        both = _fake_method(["type", "is_cash_count"], type="bank", is_cash_count=True)
        self.assertFalse(is_cash_method(both))

    def test_is_cash_count_fallback_when_type_missing(self):
        self.assertTrue(is_cash_method(_fake_method(["is_cash_count"], is_cash_count=True)))
        self.assertFalse(is_cash_method(_fake_method(["is_cash_count"], is_cash_count=False)))

    def test_fails_closed_when_neither_field_exists(self):
        with self.assertRaises(UserError):
            is_cash_method(_fake_method([]))

    def test_cash_methods_filters_payments(self):
        class Payments(list):
            def filtered(self, func):
                return Payments(p for p in self if func(p))
        cash = SimpleNamespace(payment_method_id=_fake_method(["type"], type="cash"))
        bank = SimpleNamespace(payment_method_id=_fake_method(["type"], type="bank"))
        self.assertEqual(list(cash_methods(Payments([cash, bank]))), [cash])

    def test_real_methods_resolve_as_expected(self):
        """TODO-VERIFICAR: fixtures reales de efectivo y no efectivo."""
        env = self.env
        journal = env["account.journal"].create(
            {"name": "Efectivo helper test", "type": "cash", "code": "CSHH"})
        cash = env["pos.payment.method"].create({"name": "Efectivo helper", "journal_id": journal.id})
        other = env["pos.payment.method"].create({"name": "Otro helper"})
        self.assertTrue(is_cash_method(cash))
        self.assertFalse(is_cash_method(other))
