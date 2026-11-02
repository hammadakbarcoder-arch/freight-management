/** @odoo-module **/


import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class FreightDashboard extends Component {
    static template = "trn_freight_dashboard.FreightDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            orders_by_state: {
                draft: 0,
                submitted: 0,
                confirmed: 0,
                invoiced: 0,
                done: 0,
                cancelled: 0,
            },
            total_orders: 0,
            active_orders: 0,
            total_revenue: 0,
            total_expense: 0,
            net_margin: 0,
            currency_symbol: "$",
            monthly_data: [],
            max_chart_value: 1,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        const data = await this.orm.call("freight.dashboard", "get_dashboard_data", []);
        Object.assign(this.state, data);

        // Chart ke bars ki % height nikalne ke liye maximum value dhoondein
        let maxVal = 1;
        for (const item of this.state.monthly_data || []) {
            if (item.revenue > maxVal) maxVal = item.revenue;
            if (item.expense > maxVal) maxVal = item.expense;
        }
        this.state.max_chart_value = maxVal;
    }

    getBarHeight(value) {
        if (!value || value <= 0) return 4;
        return Math.max(6, Math.round((value / this.state.max_chart_value) * 100));
    }

    formatCurrency(value) {
        const num = Number(value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        return `${this.state.currency_symbol} ${num}`;
    }

    openOrders(stateFilter = null, title = "Freight Orders") {
        let domain = [];
        if (stateFilter === "active") {
            domain = [["state", "!=", "cancelled"]];
        } else if (stateFilter) {
            domain = [["state", "=", stateFilter]];
        }

        this.action.doAction({
            type: "ir.actions.act_window",
            name: title,
            res_model: "freight.shipping",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: domain,
            target: "current",
        });
    }
}

registry.category("actions").add("trn_freight_dashboard.dashboard", FreightDashboard);