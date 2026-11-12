import { patch } from "@web/core/utils/patch";
import { formatCurrency } from "@web/core/currency";
import { SelfOrder } from "@pos_self_order/app/self_order_service";

// Pesos colombianos sin ",00" cuando el valor es entero ($ 35.000 en vez de $ 35.000,00)
patch(SelfOrder.prototype, {
    formatMonetary(price) {
        if (this.currency?.name === "COP" && Math.abs(price % 1) < 0.005) {
            return formatCurrency(price, this.currency.id, { digits: [69, 0] });
        }
        return super.formatMonetary(...arguments);
    },
});
