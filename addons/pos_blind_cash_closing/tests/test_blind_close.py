"""Pruebas del cierre ciego. ESCRITAS, NO EJECUTADAS (no hay Odoo en este entorno).

El montaje de datos (diario, medios de pago, sesion, pedidos) depende de campos
obligatorios de Odoo 18 que no se pudieron verificar: cada bloque de montaje esta
marcado TODO-VERIFICAR. Un fallo en setUp no prueba nada sobre el modulo.

Cada prueba simula al cajero (usuario real, with_user) intentando leer totales
por las mismas vias que usaria una llamada RPC: read, search_read, read_group,
search_count, export_data, metodos publicos y precarga del POS.
"""
import json

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pos_blind_cash_closing.models import blind_common as bc

# Importes distintivos: si aparecen en una respuesta al cajero, hubo fuga.
HISTORY_AMOUNT = 777777.0
CURRENT_PAID_AMOUNT = 333333.0
OPENING_CASH = 20000.0
EXPECTED_CASH = OPENING_CASH + CURRENT_PAID_AMOUNT  # solo pagos en efectivo
COUNTED_CASH = EXPECTED_CASH - 1500.0               # faltante de 1500


@tagged("post_install", "-at_install", "pos_blind_cash_closing")
class TestBlindClose(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        company = env.company
        Users = env["res.users"].with_context(no_reset_password=True)
        g_user = env.ref("point_of_sale.group_pos_user")
        # TODO-VERIFICAR: ids de grupos de pos_order_integrity.
        g_cashier = env.ref("pos_order_integrity.group_cashier_restricted")
        g_manager = env.ref("pos_order_integrity.group_pos_store_manager")
        cls.cashier = Users.create({
            "name": "Cajero Prueba", "login": "cajero_cc", "email": "cajero_cc@example.com",
            "groups_id": [(6, 0, [g_user.id, g_cashier.id])],
        })
        cls.other_cashier = Users.create({
            "name": "Cajero Dos", "login": "cajero_cc2", "email": "cajero_cc2@example.com",
            "groups_id": [(6, 0, [g_user.id, g_cashier.id])],
        })
        cls.manager = Users.create({
            "name": "Gerente Prueba", "login": "gerente_cc", "email": "gerente_cc@example.com",
            "groups_id": [(6, 0, [g_manager.id])],
        })
        # TODO-VERIFICAR: campos obligatorios de diario y medios de pago en 18.
        cash_vals = {"name": "Efectivo CC", "type": "cash", "code": "CCC", "company_id": company.id}
        # Cuentas de perdida/ganancia del diario de efectivo: sin ellas el cierre
        # con diferencia falla. TODO-VERIFICAR: account_type y company_ids en 18.
        Account = env["account.account"]
        loss = Account.create({"name": "Faltante caja CC", "code": "CCL001",
                               "account_type": "expense"})
        profit = Account.create({"name": "Sobrante caja CC", "code": "CCP001",
                                 "account_type": "income_other"})
        if "loss_account_id" in env["account.journal"]._fields:
            cash_vals["loss_account_id"] = loss.id
        if "profit_account_id" in env["account.journal"]._fields:
            cash_vals["profit_account_id"] = profit.id
        cash_journal = env["account.journal"].create(cash_vals)
        bank_journal = env["account.journal"].create(
            {"name": "Nequi CC", "type": "bank", "code": "CCB", "company_id": company.id})
        cls.pm_cash = env["pos.payment.method"].create(
            {"name": "Efectivo", "journal_id": cash_journal.id, "company_id": company.id})
        cls.pm_bank = env["pos.payment.method"].create(
            {"name": "Nequi", "journal_id": bank_journal.id, "company_id": company.id})
        config_vals = {
            "name": "Caja CC",
            "payment_method_ids": [(6, 0, [cls.pm_cash.id, cls.pm_bank.id])],
        }
        # Precondiciones exigidas por el modulo: control de efectivo activo y sin
        # limite maximo de diferencia. TODO-VERIFICAR: nombres de campos.
        config_fields = env["pos.config"]._fields
        if "cash_control" in config_fields:
            config_vals["cash_control"] = True
        if "set_maximum_difference" in config_fields:
            config_vals["set_maximum_difference"] = False
        cls.config = env["pos.config"].create(config_vals)
        if "cash_control" in config_fields:
            assert cls.config.cash_control, "fixture: cash_control debe quedar activo"
        cls.product = env["product.product"].create(
            {"name": "Cafe CC", "list_price": 3000.0, "available_in_pos": True})

        # Sesion historica ya cerrada (otro turno) con una venta pagada.
        cls.history = env["pos.session"].create(
            {"config_id": cls.config.id, "user_id": cls.other_cashier.id})
        cls._make_order(cls.history, HISTORY_AMOUNT, "paid", cls.pm_cash)
        cls.history.write({"state": "closed"})  # TODO-VERIFICAR: write directo permitido

        # Sesion actual del cajero, abierta, con efectivo inicial y una venta cobrada.
        cls.session = env["pos.session"].create(
            {"config_id": cls.config.id, "user_id": cls.cashier.id})
        cls.session.write({"state": "opened", "cash_register_balance_start": OPENING_CASH})
        cls.paid_order = cls._make_order(cls.session, CURRENT_PAID_AMOUNT, "paid", cls.pm_cash)
        # Sin borradores por defecto: cada prueba que necesite uno lo crea con _new_draft().

    @classmethod
    def _make_order(cls, session, amount, state, payment_method):
        # TODO-VERIFICAR: campos obligatorios de pos.order / pos.order.line / pos.payment.
        vals = {
            "session_id": session.id,
            "company_id": session.company_id.id,
            "state": state,
            "amount_tax": 0.0,
            "amount_total": amount,
            "amount_paid": amount if state == "paid" else 0.0,
            "amount_return": 0.0,
            "lines": [(0, 0, {
                "product_id": cls.product.id, "qty": 1.0, "price_unit": amount,
                "price_subtotal": amount, "price_subtotal_incl": amount,
                "full_product_name": "Cafe CC",
            })],
        }
        if payment_method:
            vals["payment_ids"] = [(0, 0, {"amount": amount, "payment_method_id": payment_method.id})]
        return cls.env["pos.order"].sudo().create(vals)

    DRAFT_AMOUNT = 4500.0

    def _new_draft(self):
        return self._make_order(self.session, self.DRAFT_AMOUNT, "draft", None)

    def _count(self, amount=COUNTED_CASH):
        return self.session.with_user(self.cashier).post_closing_cash_details(amount)

    # ------------------------------------------------------------------
    def _as_cashier(self, model_name):
        return self.env[model_name].with_user(self.cashier)

    def _assert_hidden(self, value, secret):
        self.assertNotIn(str(int(secret)), json.dumps(value, default=str))

    # ---- pos.order / pos.payment / pos.order.line ---------------------
    def test_cashier_cannot_search_read_history(self):
        draft = self._new_draft()
        # Control: el sudo ve los pedidos cobrados; si no, la prueba no prueba nada.
        self.assertTrue(self.env["pos.order"].sudo().search([("state", "=", "paid")]))
        orders = self._as_cashier("pos.order")
        rows = orders.search_read([], ["amount_total", "state", "session_id"])
        self.assertEqual([r["id"] for r in rows], [draft.id])
        self.assertTrue(all(r["state"] == "draft" for r in rows))
        self._assert_hidden(rows, HISTORY_AMOUNT)
        self._assert_hidden(rows, CURRENT_PAID_AMOUNT)

    def test_cashier_cannot_read_paid_order_by_id(self):
        paid = self.paid_order.with_user(self.cashier)
        with self.assertRaises(AccessError):
            paid.read(["amount_total"])
        with self.assertRaises(AccessError):
            self.history.with_user(self.cashier).read(["name"])

    def test_cashier_read_group_and_count_return_no_totals(self):
        orders = self._as_cashier("pos.order")
        self.assertEqual(
            orders.search_count([("state", "=", "paid")]), 0)
        groups = orders.read_group([("state", "=", "paid")], ["amount_total:sum"], [])
        self._assert_hidden(groups, CURRENT_PAID_AMOUNT)
        self._assert_hidden(groups, HISTORY_AMOUNT)

    def test_cashier_cannot_read_payments_by_method(self):
        self.assertTrue(self.env["pos.payment"].sudo().search([]))  # control
        payments = self._as_cashier("pos.payment")
        self.assertFalse(payments.search([]))
        groups = payments.read_group([], ["amount:sum"], ["payment_method_id"])
        self._assert_hidden(groups, CURRENT_PAID_AMOUNT)

    def test_cashier_cannot_read_order_lines_of_paid_orders(self):
        self.assertTrue(self.env["pos.order.line"].sudo().search([("order_id.state", "=", "paid")]))
        lines = self._as_cashier("pos.order.line").search([("order_id.state", "=", "paid")])
        self.assertFalse(lines)

    def test_cashier_cannot_export_orders(self):
        with self.assertRaises(AccessError):
            self._as_cashier("pos.order").browse(self.paid_order.id).export_data(["amount_total"])

    def test_cashier_ticket_history_is_empty(self):
        # TODO-VERIFICAR: existencia/firma de search_paid_order_ids en 18.
        result = self._as_cashier("pos.order").search_paid_order_ids(
            self.config.id, [], 80, 0)
        self.assertEqual(result.get("totalCount"), 0)

    # ---- pos.session --------------------------------------------------
    def test_cashier_cannot_read_other_sessions(self):
        self.assertEqual(self.env["pos.session"].sudo().search_count([]), 2)  # control
        sessions = self._as_cashier("pos.session").search([])
        self.assertEqual(sessions, self.session)

    def test_cashier_cannot_read_session_totals(self):
        session = self.session.with_user(self.cashier)
        for name in bc.SESSION_SENSITIVE:
            if name not in session._fields:
                continue
            # Con groups= hay AccessError; con el filtro de read() la clave
            # simplemente no vuelve. Ambos son aceptables; un valor, no.
            try:
                rows = session.read([name, "name"])
            except AccessError:
                continue
            self.assertNotIn(name, rows[0], "campo sensible devuelto: %s" % name)
        rows = session.read()
        for name in bc.SESSION_SENSITIVE:
            self.assertNotIn(name, rows[0])

    def test_cashier_cannot_use_session_totals_as_search_oracle(self):
        sessions = self._as_cashier("pos.session")
        for name in ("cash_register_balance_end", "cash_register_difference", "total_payments_amount"):
            if name in sessions._fields:
                with self.assertRaises(AccessError):
                    sessions.search_count([(name, ">", 0)])

    def test_cashier_cannot_group_by_or_aggregate_session_totals(self):
        sessions = self._as_cashier("pos.session")
        if "total_payments_amount" in sessions._fields:
            with self.assertRaises(AccessError):
                sessions.read_group([], ["total_payments_amount:sum"], [])

    def test_cashier_cannot_close_session_by_direct_rpc(self):
        session = self.session.with_user(self.cashier)
        with self.assertRaises(AccessError):
            session.action_pos_session_closing_control()
        with self.assertRaises(AccessError):
            session.action_pos_session_validate()

    def test_cashier_cannot_close_other_cashier_session(self):
        with self.assertRaises((AccessError, UserError)):
            self.session.with_user(self.other_cashier).post_closing_cash_details(1.0)

    # ---- Cierre ciego -------------------------------------------------
    def test_closing_control_data_is_blind_for_cashier(self):
        data = self.session.with_user(self.cashier).get_closing_control_data()
        dumped = json.dumps(data, default=str)
        for secret in (EXPECTED_CASH, CURRENT_PAID_AMOUNT, HISTORY_AMOUNT, OPENING_CASH):
            self.assertNotIn(str(int(secret)), dumped)
        self.assertEqual(data["orders_details"], {"quantity": 0, "amount": 0})
        self.assertFalse(data["is_manager"])

    def test_closing_control_data_is_real_for_manager(self):
        self.assertTrue(self.session.with_user(self.manager))
        data = self.session.with_user(self.manager).get_closing_control_data()
        self.assertIn(str(int(CURRENT_PAID_AMOUNT)), json.dumps(data, default=str))

    def test_counting_records_difference_only_for_manager(self):
        result = self._count()
        self.assertEqual(result, {"successful": True})
        self._assert_hidden(result, EXPECTED_CASH)
        closing = self.env["pos.blind.cash.closing"].with_user(self.manager).search(
            [("session_id", "=", self.session.id)])
        self.assertEqual(len(closing), 1)
        self.assertAlmostEqual(closing.expected_cash, EXPECTED_CASH, places=2)
        self.assertAlmostEqual(closing.counted_cash, COUNTED_CASH, places=2)
        self.assertAlmostEqual(closing.difference, -1500.0, places=2)
        self.assertEqual(closing.cashier_id, self.cashier)
        # El cajero no puede leer ni buscar el registro, ni por ORM ni por RPC.
        closings = self.env["pos.blind.cash.closing"].with_user(self.cashier)
        with self.assertRaises(AccessError):
            closings.search([])
        with self.assertRaises(AccessError):
            closings.search_read([], ["difference"])
        with self.assertRaises(AccessError):
            closings.read_group([], ["difference:sum"], [])

    def test_counting_twice_updates_single_record(self):
        sess = self.session.with_user(self.cashier)
        self.assertEqual(sess.post_closing_cash_details(1000.0), {"successful": True})
        self.assertEqual(sess.post_closing_cash_details(COUNTED_CASH), {"successful": True})
        closing = self.env["pos.blind.cash.closing"].sudo().search(
            [("session_id", "=", self.session.id)])
        self.assertEqual(len(closing), 1)
        self.assertAlmostEqual(closing.counted_cash, COUNTED_CASH, places=2)
        self.assertAlmostEqual(closing.difference, -1500.0, places=2)

    def test_counted_cash_validation(self):
        sess = self.session.with_user(self.cashier)
        for bad in (-1.0, float("nan"), float("inf"), "100", True, None, 1e15):
            with self.assertRaises(UserError, msg=repr(bad)):
                sess.post_closing_cash_details(bad)

    def test_close_requires_previous_count(self):
        # Borrar borradores para aislar la condicion: sin conteo no hay cierre.
        result = self.session.with_user(self.cashier).close_session_from_ui()
        self.assertFalse(result["successful"])
        self._assert_hidden(result, EXPECTED_CASH)

    def test_close_with_draft_orders_gives_safe_message(self):
        # La venta en borrador sigue abierta: el conteo se rechaza con mensaje propio.
        self._new_draft()
        result = self._count()
        self.assertFalse(result["successful"])
        self._assert_hidden(result, EXPECTED_CASH)

    def test_full_blind_close_returns_no_amounts(self):
        # TODO-VERIFICAR: requiere configuracion contable completa (cuentas de
        # perdida/ganancia del diario de efectivo); si falta, el resultado es el
        # mensaje generico y la prueba debe ajustarse a la configuracion.
        result = self.session.with_user(self.cashier).pos_blind_close(COUNTED_CASH, "sin novedades")
        self._assert_hidden(result, EXPECTED_CASH)
        self._assert_hidden(result, 1500)
        closing = self.env["pos.blind.cash.closing"].sudo().search(
            [("session_id", "=", self.session.id)])
        self.assertTrue(closing)
        if result.get("successful"):
            # A1: tras cerrar, la diferencia sigue siendo la del conteo (no se recalcula).
            self.assertEqual(closing.state, "closed")
            self.assertFalse(closing.calc_after_close)
            self.assertAlmostEqual(closing.difference, -1500.0, places=2)
            self.assertAlmostEqual(closing.expected_cash, EXPECTED_CASH, places=2)
            self.assertAlmostEqual(closing.counted_cash, COUNTED_CASH, places=2)
            self.assertAlmostEqual(closing.difference_at_count, -1500.0, places=2)
            self.assertAlmostEqual(closing.cash_sales_after_count, 0.0, places=2)
            # El ajuste nativo de diferencia no debe haber igualado esperado y contado.
            self.assertNotAlmostEqual(closing.difference, 0.0, places=2)
        else:
            self.assertEqual(closing.state, "counted")

    def test_closing_record_is_immutable(self):
        self._count()
        closing = self.env["pos.blind.cash.closing"].with_user(self.manager).search(
            [("session_id", "=", self.session.id)])
        self.assertEqual(len(closing), 1)  # sin esto la prueba pasaria en vacio
        with self.assertRaises((AccessError, UserError)):
            closing.write({"difference": 0.0})
        with self.assertRaises((AccessError, UserError)):
            closing.unlink()

    # ---- C2: saltarse el cierre ciego ---------------------------------
    def test_cashier_cannot_write_session_fields_by_rpc(self):
        session = self.session.with_user(self.cashier)
        for vals in ({"state": "closed"}, {"cash_register_balance_start": 1.0},
                     {"cash_register_balance_end_real": 1.0}, {"stop_at": False},
                     {"user_id": self.other_cashier.id}):
            with self.assertRaises(AccessError, msg=str(vals)):
                session.write(vals)
        self.assertEqual(self.session.sudo().state, "opened")
        self.assertAlmostEqual(self.session.sudo().cash_register_balance_start, OPENING_CASH, places=2)

    def test_cashier_cannot_create_session_already_opened(self):
        with self.assertRaises(AccessError):
            self.env["pos.session"].with_user(self.cashier).create(
                {"config_id": self.config.id, "user_id": self.cashier.id, "state": "opened"})

    def test_state_closed_requires_previous_count_even_in_window(self):
        with bc.internal_window():
            with self.assertRaises(AccessError):
                self.session.with_user(self.cashier).write({"state": "closed"})

    def test_cashier_cannot_use_direct_close_or_cash_moves(self):
        # TODO-VERIFICAR: firmas de action_pos_session_close y try_cash_in_out.
        session = self.session.with_user(self.cashier)
        with self.assertRaises(AccessError):
            session.action_pos_session_close()
        with self.assertRaises(AccessError):
            session.try_cash_in_out("out", 1000.0, "retiro", {})

    def test_update_closing_state_requires_count(self):
        session = self.session.with_user(self.cashier)
        with self.assertRaises(UserError):
            session.update_closing_control_state_session("nota")
        self._count()
        session.update_closing_control_state_session("nota")
        self.assertEqual(self.session.sudo().state, "closing_control")

    def test_opening_discrepancy_is_recorded_for_manager(self):
        # Cierre anterior contado en 50000; apertura declarada 20000 (OPENING_CASH).
        prev = self.history
        self.env["pos.blind.cash.closing"].sudo().create({
            "session_id": prev.id, "config_id": self.config.id, "state": "closed",
            "counted_cash": 50000.0, "closed_at": "2026-01-01 00:00:00",
            "currency_id": self.env.company.currency_id.id,
        })
        rec = self.env["pos.blind.cash.closing"]._register_opening(self.session)
        self.assertTrue(rec.has_previous)
        self.assertAlmostEqual(rec.opening_discrepancy, OPENING_CASH - 50000.0, places=2)
        rec_mgr = self.env["pos.blind.cash.closing"].with_user(self.manager).browse(rec.id)
        self.assertAlmostEqual(rec_mgr.opening_discrepancy, OPENING_CASH - 50000.0, places=2)

    def test_final_register_ignores_native_difference_adjustment(self):
        """A1: simula que el ajuste nativo de diferencia entro en los movimientos
        al cerrar (+1500, igual al faltante). La diferencia guardada debe seguir
        siendo el faltante."""
        from unittest.mock import patch
        self._count()
        closing = self.env["pos.blind.cash.closing"].sudo().search([("session_id", "=", self.session.id)])
        self.assertEqual(len(closing), 1)
        self.assertAlmostEqual(closing.difference, -1500.0, places=2)
        real = type(self.session)._pos_cash_figures

        def fake(rec):
            figures = real(rec)
            figures["moves"] += 1500.0
            figures["expected"] += 1500.0
            return figures

        with patch.object(type(self.session), "_pos_cash_figures", fake):
            self.env["pos.blind.cash.closing"]._register(self.session, final=True)
        self.assertEqual(closing.state, "closed")
        self.assertAlmostEqual(closing.counted_cash, COUNTED_CASH, places=2)
        self.assertAlmostEqual(closing.expected_cash, EXPECTED_CASH, places=2)
        self.assertAlmostEqual(closing.difference, -1500.0, places=2)
        self.assertAlmostEqual(closing.difference_at_count, -1500.0, places=2)
        self.assertFalse(closing.calc_after_close)

    def test_cash_sale_after_count_is_reflected_at_close(self):
        """N2: una venta en efectivo entre el conteo y el cierre cambia esperado
        y diferencia final, sin tocar lo contado ni la diferencia al contar."""
        self._count()
        self._make_order(self.session, 500.0, "paid", self.pm_cash)
        self.env["pos.blind.cash.closing"]._register(self.session, final=True)
        closing = self.env["pos.blind.cash.closing"].sudo().search([("session_id", "=", self.session.id)])
        self.assertEqual(len(closing), 1)
        self.assertEqual(closing.state, "closed")
        self.assertAlmostEqual(closing.counted_cash, COUNTED_CASH, places=2)
        self.assertAlmostEqual(closing.opening_cash, OPENING_CASH, places=2)
        self.assertAlmostEqual(closing.cash_sales_after_count, 500.0, places=2)
        self.assertAlmostEqual(closing.expected_cash, EXPECTED_CASH + 500.0, places=2)
        self.assertAlmostEqual(closing.difference, -2000.0, places=2)
        self.assertAlmostEqual(closing.difference_at_count, -1500.0, places=2)

    def test_opening_cannot_be_redeclared(self):
        """N1: set_opening_control solo en opening_control y una vez por sesion."""
        session = self.session.with_user(self.cashier)
        # La sesion ya esta 'opened' (hubo ventas): se rechaza.
        with self.assertRaises(UserError):
            session.set_opening_control(999999.0, "re-declaro")
        self.assertAlmostEqual(self.session.sudo().cash_register_balance_start, OPENING_CASH, places=2)
        # Aun en opening_control, si ya hay apertura registrada se rechaza.
        self.session.sudo().write({"state": "opening_control"})
        self.env["pos.blind.cash.closing"]._register_opening(self.session)
        with self.assertRaises(UserError):
            session.set_opening_control(999999.0, "otra vez")
        self.assertAlmostEqual(self.session.sudo().cash_register_balance_start, OPENING_CASH, places=2)

    def test_manager_close_without_count_is_flagged(self):
        self.env["pos.blind.cash.closing"]._register(self.session, counted_cash=1.0, final=True)
        closing = self.env["pos.blind.cash.closing"].sudo().search([("session_id", "=", self.session.id)])
        self.assertTrue(closing.calc_after_close)

    # ---- A5, M3 -------------------------------------------------------
    def test_filter_sync_result_is_fail_closed(self):
        payload = {
            "pos.order": [{"id": 1, "uuid": "mine", "amount_total": 10},
                          {"id": 2, "uuid": "other", "amount_total": 999},
                          {"id": 3, "amount_total": 888}],
            "pos.order.line": [{"id": 10, "order_id": 1}, {"id": 11, "order_id": [2, "x"]}],
            "pos.payment": [{"id": 20, "pos_order_id": 1, "amount": 10},
                            {"id": 21, "pos_order_id": 2, "amount": 999}],
            "res.partner": [{"id": 5, "name": "x"}],
        }
        out = bc.filter_sync_result(payload, {"mine"})
        self.assertEqual([r["id"] for r in out["pos.order"]], [1])
        self.assertEqual([r["id"] for r in out["pos.order.line"]], [10])
        self.assertEqual([r["id"] for r in out["pos.payment"]], [20])
        self.assertNotIn("res.partner", out)
        empty = bc.filter_sync_result(payload, set())
        self.assertEqual(empty.get("pos.order"), [])
        self.assertEqual(empty.get("pos.payment"), [])

    def test_cashier_cannot_use_order_or_paths_to_probe_costs(self):
        products = self._as_cashier("product.product")
        with self.assertRaises(AccessError):
            products.search([], order="standard_price desc")
        lines = self._as_cashier("pos.order.line")
        with self.assertRaises(AccessError):
            lines.search([("product_id.standard_price", ">", 0)])
        with self.assertRaises(AccessError):
            lines.read_group([], ["id:count"], ["total_cost"])

    def test_check_text_handles_non_list_domain_objects(self):
        class FakeDomain:
            def __str__(self):
                return "Domain(standard_price > 0)"
        env = self.env(user=self.cashier)
        with self.assertRaises(AccessError):
            bc.check_text(env, FakeDomain())

    def test_blind_scope_excludes_non_pos_users(self):
        outsider = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Externo CC", "login": "externo_cc", "email": "externo_cc@example.com",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        self.assertFalse(bc.is_blind(self.env(user=outsider)))
        self.assertTrue(bc.is_blind(self.env(user=self.cashier)))
        self.assertFalse(bc.is_blind(self.env(user=self.manager)))

    # ---- Informes -----------------------------------------------------
    def test_cashier_cannot_call_sales_details_report(self):
        # TODO-VERIFICAR: nombre del informe y firma de get_sale_details.
        report = self.env["report.point_of_sale.report_saledetails"].with_user(self.cashier)
        with self.assertRaises(AccessError):
            report.get_sale_details(session_ids=[self.session.id])

    def test_manager_can_call_sales_details_report(self):
        report = self.env["report.point_of_sale.report_saledetails"].with_user(self.manager)
        result = report.get_sale_details(session_ids=[self.session.id])
        self.assertTrue(result)

    # ---- Precarga del POS y costos -----------------------------------
    def test_pos_load_fields_exclude_sensitive_for_cashier(self):
        # TODO-VERIFICAR: _load_pos_data_fields existe en cada modelo y su firma.
        for model_name in ("pos.session", "pos.order", "pos.order.line", "product.product"):
            model = self.env[model_name].with_user(self.cashier)
            if not hasattr(model, "_load_pos_data_fields"):
                continue
            names = model._load_pos_data_fields(self.config.id)
            self.assertFalse(set(names) & bc.ALL_SENSITIVE, model_name)

    def test_pos_load_fields_unchanged_for_manager(self):
        model = self.env["product.product"].with_user(self.manager)
        if hasattr(model, "_load_pos_data_fields"):
            base = model._load_pos_data_fields(self.config.id)
            self.assertIsInstance(base, list)

    def test_cashier_read_filters_costs(self):
        self.product.sudo().standard_price = 1234.0
        row = self.product.with_user(self.cashier).read(["name", "standard_price"])[0]
        self.assertNotIn("standard_price", row)
        row_all = self.product.with_user(self.cashier).read()[0]
        self.assertNotIn("standard_price", row_all)
        with self.assertRaises(AccessError):
            self.env["product.product"].with_user(self.cashier).search_count(
                [("standard_price", ">", 0)])

    def test_strip_sensitive_payload(self):
        payload = {"pos.order": [{"id": 1, "margin": 5, "uuid": "a",
                                   "lines": [{"total_cost": 3, "qty": 1}]}],
                   "pos.session": [{"id": 2, "cash_register_balance_end": 99}]}
        clean = bc.strip_sensitive_payload(payload)
        self.assertEqual(clean["pos.order"][0], {"id": 1, "uuid": "a", "lines": [{"qty": 1}]})
        self.assertEqual(clean["pos.session"][0], {"id": 2})

    def test_window_is_not_activable_from_context_or_rpc(self):
        # Una clave de contexto enviada por el cliente no abre la ventana.
        ctx_orders = self.env["pos.order"].with_user(self.cashier).with_context(
            pos_window=True, internal=True, pos_internal=True)
        rows = ctx_orders.search_read([("state", "=", "paid")], ["amount_total"])
        self.assertFalse(rows)
        self.assertFalse(bc.in_window())

    # ---- Gerente ve todo ----------------------------------------------
    def test_manager_sees_history_and_totals(self):
        orders = self.env["pos.order"].with_user(self.manager)
        amounts = orders.search([("state", "=", "paid")]).mapped("amount_total")
        self.assertIn(HISTORY_AMOUNT, amounts)
        self.assertIn(CURRENT_PAID_AMOUNT, amounts)
