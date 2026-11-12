/** Permisos por rol en el POS: mesero / cajero / gerente. */
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

// true = permitido. Lo que no aparece en un rol queda permitido.
const RULES = {
    mesero: { pay: false, discount: false, price: false, refund: false, close: false, deleteOrder: false },
    cajero: { pay: true, discount: false, price: false, refund: false, close: true, deleteOrder: false },
    gerente: {},
};

const MESSAGES = {
    pay: _t("Tu rol no permite cobrar. Pide a caja que cobre la cuenta."),
    discount: _t("Solo un gerente puede aplicar descuentos."),
    price: _t("Solo un gerente puede cambiar precios."),
    refund: _t("Solo un gerente puede hacer reembolsos."),
    close: _t("Tu rol no permite cerrar la caja."),
    deleteOrder: _t("Solo un gerente puede anular pedidos."),
};

patch(PosStore.prototype, {
    get posRole() {
        const cashier = this.get_cashier();
        if (cashier?.pos_role) {
            return cashier.pos_role;
        }
        return cashier?._role === "manager" ? "gerente" : "cajero";
    },
    posCan(action) {
        const rules = RULES[this.posRole] || RULES.cajero;
        return rules[action] !== false;
    },
    posDeny(action) {
        this.notification.add(MESSAGES[action], { type: "warning" });
    },
    async pay() {
        if (!this.posCan("pay")) {
            return this.posDeny("pay");
        }
        return super.pay(...arguments);
    },
    async closeSession() {
        if (!this.posCan("close")) {
            return this.posDeny("close");
        }
        return super.closeSession(...arguments);
    },
    async onDeleteOrder(order) {
        if (!this.posCan("deleteOrder")) {
            this.posDeny("deleteOrder");
            return false;
        }
        return super.onDeleteOrder(...arguments);
    },
    cashierHasPriceControlRights() {
        return this.posCan("price") && super.cashierHasPriceControlRights(...arguments);
    },
});

patch(ProductScreen.prototype, {
    getNumpadButtons() {
        const buttons = super.getNumpadButtons(...arguments);
        if (this.pos.posCan("discount")) {
            return buttons;
        }
        return buttons.map((b) => (b.value === "discount" ? { ...b, disabled: true } : b));
    },
    onNumpadClick(buttonValue) {
        if (buttonValue === "discount" && !this.pos.posCan("discount")) {
            return this.pos.posDeny("discount");
        }
        return super.onNumpadClick(...arguments);
    },
});

patch(TicketScreen.prototype, {
    async onDoRefund() {
        if (!this.pos.posCan("refund")) {
            return this.pos.posDeny("refund");
        }
        return super.onDoRefund(...arguments);
    },
});
