"""Base comun de pruebas. ESCRITAS, NO EJECUTADAS (no hay Odoo disponible).

TODO-VERIFICAR en el primer arranque real:
- la base de pruebas necesita plan contable (post_install con l10n_generic_coa);
- creacion de pos.config / pos.session como se hace abajo en Odoo 18;
- campos obligatorios de pos.order y pos.order.line (name, amount_*, subtotales);
- permisos ACL de point_of_sale.group_pos_user para crear/escribir pedidos.
"""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged("post_install", "-at_install", "pos_order_integrity")
class PosIntegrityCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env
        # Usuarios con identidades separadas (no un empleado por PIN).
        cls.cashier = new_test_user(
            env, login="cafe_cajero",
            groups="point_of_sale.group_pos_user,pos_order_integrity.group_cashier_restricted")
        cls.manager = new_test_user(
            env, login="cafe_gerente",
            groups="point_of_sale.group_pos_user,pos_order_integrity.group_pos_store_manager")
        # Usuario POS sin el grupo de cajero: tambien debe quedar restringido.
        cls.plain_pos_user = new_test_user(
            env, login="cafe_pos_sin_grupo", groups="point_of_sale.group_pos_user")

        uom_unit = env.ref("uom.product_uom_unit")
        uom_kg = env.ref("uom.product_uom_kgm")
        Product = env["product.product"]
        cls.coffee = Product.create({
            "name": "Cafe test", "list_price": 3000.0, "uom_id": uom_unit.id,
            "available_in_pos": True, "taxes_id": [(5, 0, 0)],
        })
        cls.bag = Product.create({
            "name": "Pan de bolita bolsa test", "list_price": 8000.0, "uom_id": uom_unit.id,
            "available_in_pos": True, "taxes_id": [(5, 0, 0)],
            "pos_sale_mode": "bag", "pos_units_per_bag": 10,
        })
        cls.by_weight = Product.create({
            "name": "Producto por peso test", "list_price": 20000.0, "uom_id": uom_kg.id,
            "available_in_pos": True, "taxes_id": [(5, 0, 0)],
            "pos_sale_mode": "weight",
        })
        cls.config = env["pos.config"].create({"name": "Cafeteria test"})
        # TODO-VERIFICAR: creacion de pos.payment.method sin diario y alta en la caja.
        cls.pay_method = env["pos.payment.method"].create({"name": "Metodo test"})
        cls.foreign_pay_method = env["pos.payment.method"].create({"name": "Metodo ajeno"})
        # Efectivo real (diario de tipo cash) y Nequi (sin diario de efectivo).
        # TODO-VERIFICAR: campos obligatorios de account.journal y de
        # pos.payment.method al crearlos asi en Odoo 18.
        cash_journal = env["account.journal"].create(
            {"name": "Efectivo test", "type": "cash", "code": "CSHT"})
        cls.cash_method = env["pos.payment.method"].create(
            {"name": "Efectivo test", "journal_id": cash_journal.id})
        cls.nequi_method = env["pos.payment.method"].create({"name": "Nequi test"})
        cls.config.write({"payment_method_ids": [
            (4, cls.pay_method.id), (4, cls.cash_method.id), (4, cls.nequi_method.id)]})
        cls.session = env["pos.session"].create(
            {"config_id": cls.config.id, "user_id": cls.manager.id})

    # -- ayudantes ------------------------------------------------------
    def _line_vals(self, product, qty=1.0, price=None, with_subtotals=True, **extra):
        price = product.lst_price if price is None else price
        vals = {
            "product_id": product.id, "qty": qty, "price_unit": price, "discount": 0.0,
            "name": product.display_name, "tax_ids": [(6, 0, [])],
        }
        if with_subtotals:
            vals.update({"price_subtotal": qty * price, "price_subtotal_incl": qty * price})
        vals.update(extra)
        return vals

    def _order_vals(self, line_vals_list, **extra):
        total = sum(v.get("price_subtotal_incl", v["qty"] * v["price_unit"])
                    for v in line_vals_list)
        vals = {
            "session_id": self.session.id, "company_id": self.env.company.id,
            "amount_tax": 0.0, "amount_total": total, "amount_paid": 0.0,
            "amount_return": 0.0, "lines": [(0, 0, v) for v in line_vals_list],
        }
        vals.update(extra)
        return vals

    def _create_order(self, user, line_vals_list, **extra):
        return self.env["pos.order"].with_user(user).create(
            self._order_vals(line_vals_list, **extra))

    def _pay(self, order, amount=None, method=None, user=None, **extra):
        """Registra un pago como usuario (por defecto el cajero)."""
        vals = {
            "pos_order_id": order.id,
            "amount": order.amount_total if amount is None else amount,
            "payment_method_id": (method or self.pay_method).id,
        }
        vals.update(extra)
        return self.env["pos.payment"].with_user(user or self.cashier).create(vals)

    def _confirmed_order(self, line_vals_list=None):
        """Venta confirmada: fixture armado con sudo (equivale al flujo interno
        de Odoo); no pasa por los controles del cajero."""
        line_vals_list = line_vals_list or [self._line_vals(self.coffee, 2)]
        order = self._create_order(self.cashier, line_vals_list)
        self.env["pos.payment"].sudo().create({
            "pos_order_id": order.id, "amount": order.amount_total,
            "payment_method_id": self.pay_method.id})
        order.sudo().write({"state": "paid"})
        return order

    def _set_cost(self, product, cost):
        product.product_tmpl_id.sudo().write({"pos_manual_cost": cost})
