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
            loading: false,

            // Filter selections
            filter_status: "all",
            filter_transport: "all",
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("freight.dashboard", "get_dashboard_data", []);
            Object.assign(this.state, data);

            // Chart bar scale max value
            let maxVal = 1;
            for (const item of this.state.monthly_data || []) {
                if (item.revenue > maxVal) maxVal = item.revenue;
                if (item.expense > maxVal) maxVal = item.expense;
            }
            this.state.max_chart_value = maxVal;
        } finally {
            this.state.loading = false;
        }
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

    get statusSegments() {
        const counts = this.state.orders_by_state || {};
        const total = this.state.total_orders || 0;
        if (total === 0) return [];

        const colors = {
            draft: "#64748b",     // Slate
            submitted: "#f59e0b", // Amber
            confirmed: "#3b82f6", // Blue
            invoiced: "#8b5cf6",  // Purple
            done: "#10b981",      // Emerald green
            cancelled: "#ef4444", // Red
        };
        const labels = {
            draft: "Draft",
            submitted: "Submitted",
            confirmed: "Confirmed",
            invoiced: "Invoiced",
            done: "Delivered",
            cancelled: "Cancelled",
        };

        const circumference = 251.327; // 2 * PI * r (r=40)
        let accumulated = 0;
        const segments = [];

        for (const [key, count] of Object.entries(counts)) {
            if (count > 0) {
                const fraction = count / total;
                const dashLength = fraction * circumference;
                segments.push({
                    key,
                    label: labels[key] || key,
                    count,
                    color: colors[key] || "#94a3b8",
                    dasharray: `${dashLength} ${circumference}`,
                    dashoffset: -accumulated,
                    percentage: Math.round(fraction * 100),
                });
                accumulated += dashLength;
            }
        }
        return segments;
    }

    openOrders(stateFilter = null, title = "Freight Orders") {
        let domain = [];
        if (stateFilter === "active") {
            domain = [["state", "!=", "cancelled"]];
        } else if (stateFilter) {
            domain = [["state", "=", stateFilter]];
        }

        if (this.state.filter_transport && this.state.filter_transport !== "all") {
            domain.push(["transport", "=", this.state.filter_transport]);
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

    onFilterChange(type, ev) {
        if (type === "status") {
            this.state.filter_status = ev.target.value;
            if (this.state.filter_status !== "all") {
                this.openOrders(this.state.filter_status, `${this.state.filter_status.toUpperCase()} Orders`);
            }
        } else if (type === "transport") {
            this.state.filter_transport = ev.target.value;
            if (this.state.filter_transport !== "all") {
                this.action.doAction({
                    type: "ir.actions.act_window",
                    name: `${this.state.filter_transport.toUpperCase()} Shipments`,
                    res_model: "freight.shipping",
                    views: [[false, "list"], [false, "form"]],
                    domain: [["transport", "=", this.state.filter_transport]],
                    target: "current",
                });
            }
        }
    }

    clearFilters() {
        this.state.filter_status = "all";
        this.state.filter_transport = "all";
        this.loadDashboardData();
    }
}

registry.category("actions").add("trn_freight_dashboard.dashboard", FreightDashboard);
