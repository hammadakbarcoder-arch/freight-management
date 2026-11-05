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
            filter_date_preset: "all",
            filter_date_from: "",
            filter_date_to: "",
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    formatDateISO(d) {
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            const kwargs = {
                date_from: this.state.filter_date_from || false,
                date_to: this.state.filter_date_to || false,
                transport: this.state.filter_transport !== "all" ? this.state.filter_transport : false,
                status: this.state.filter_status !== "all" ? this.state.filter_status : false,
            };
            const data = await this.orm.call("freight.dashboard", "get_dashboard_data", [], kwargs);
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
        const finalState = stateFilter || (this.state.filter_status !== "all" ? this.state.filter_status : null);
        if (finalState === "active") {
            domain.push(["state", "!=", "cancelled"]);
        } else if (finalState) {
            domain.push(["state", "=", finalState]);
        }

        if (this.state.filter_transport && this.state.filter_transport !== "all") {
            domain.push(["transport", "=", this.state.filter_transport]);
        }
        if (this.state.filter_date_from) {
            domain.push(["order_date", ">=", this.state.filter_date_from]);
        }
        if (this.state.filter_date_to) {
            domain.push(["order_date", "<=", this.state.filter_date_to]);
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
        } else if (type === "transport") {
            this.state.filter_transport = ev.target.value;
        }
        this.loadDashboardData();
    }

    onDatePresetChange(ev) {
        const preset = ev.target.value;
        this.state.filter_date_preset = preset;
        const now = new Date();

        if (preset === "all") {
            this.state.filter_date_from = "";
            this.state.filter_date_to = "";
        } else if (preset === "today") {
            const todayStr = this.formatDateISO(now);
            this.state.filter_date_from = todayStr;
            this.state.filter_date_to = todayStr;
        } else if (preset === "this_week") {
            const d = new Date(now);
            const day = d.getDay();
            const diff = d.getDate() - day + (day === 0 ? -6 : 1);
            const monday = new Date(d.setDate(diff));
            this.state.filter_date_from = this.formatDateISO(monday);
            this.state.filter_date_to = this.formatDateISO(new Date());
        } else if (preset === "this_month") {
            const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
            this.state.filter_date_from = this.formatDateISO(firstDay);
            this.state.filter_date_to = this.formatDateISO(now);
        } else if (preset === "last_month") {
            const firstDay = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            const lastDay = new Date(now.getFullYear(), now.getMonth(), 0);
            this.state.filter_date_from = this.formatDateISO(firstDay);
            this.state.filter_date_to = this.formatDateISO(lastDay);
        } else if (preset === "this_quarter") {
            const qMonth = Math.floor(now.getMonth() / 3) * 3;
            const firstDay = new Date(now.getFullYear(), qMonth, 1);
            this.state.filter_date_from = this.formatDateISO(firstDay);
            this.state.filter_date_to = this.formatDateISO(now);
        } else if (preset === "this_year") {
            const firstDay = new Date(now.getFullYear(), 0, 1);
            this.state.filter_date_from = this.formatDateISO(firstDay);
            this.state.filter_date_to = this.formatDateISO(now);
        } else if (preset === "custom") {
            return;
        }
        this.loadDashboardData();
    }

    onCustomDateChange(type, ev) {
        if (type === "from") {
            this.state.filter_date_from = ev.target.value;
        } else if (type === "to") {
            this.state.filter_date_to = ev.target.value;
        }
        this.state.filter_date_preset = "custom";
        this.loadDashboardData();
    }

    clearFilters() {
        this.state.filter_status = "all";
        this.state.filter_transport = "all";
        this.state.filter_date_preset = "all";
        this.state.filter_date_from = "";
        this.state.filter_date_to = "";
        this.loadDashboardData();
    }
}

registry.category("actions").add("trn_freight_dashboard.dashboard", FreightDashboard);
