import { patch } from "@web/core/utils/patch";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";

patch(ProductCard.prototype, {
    /** Descripcion corta (texto plano) para mostrar en la tarjeta. */
    get lgShortDescription() {
        const html = this.props.product.public_description;
        if (!html) {
            return "";
        }
        const div = document.createElement("div");
        div.innerHTML = html;
        return (div.textContent || "").trim();
    },
});
