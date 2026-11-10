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
            in_transit_orders: 0,
            delivered_orders: 0,
            awaiting_action_orders: 0,
            total_revenue: 0,
            total_expense: 0,
            net_margin: 0,
            profit_margin_pct: 0,
            delivered_rate_pct: 0,
            tracked_states_count: 0,
            currency_symbol: "$",
            monthly_data: [],
            chart_12m: [],
            top_routes: [],
            booking_pipeline: {
                draft: 0,
                submitted: 0,
                confirmed: 0,
                invoiced: 0,
                done: 0,
                pending_invoices: 0,
                pending_clearances: 0,
            },
            recent_shipments: [],
            recent_clearances: [],
            alerts: {
                draft_clearances: 0,
                overdue_shipments: 0,
            },
            top_shippers: [],
            loading: false,

            // Filter presets: 'today', 'weekly', '12m', 'all'
            active_filter_preset: "all",
            filter_date_from: false,
            filter_date_to: false,
            filter_transport: "all",
            filter_status: "all",

            // Dark Mode toggle
            is_dark_mode: false,
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
        } finally {
            this.state.loading = false;
        }
    }

    toggleDarkMode() {
        this.state.is_dark_mode = !this.state.is_dark_mode;
    }

    selectPreset(preset) {
        this.state.active_filter_preset = preset;
        const now = new Date();

        if (preset === "today") {
            const todayStr = this.formatDateISO(now);
            this.state.filter_date_from = todayStr;
            this.state.filter_date_to = todayStr;
        } else if (preset === "weekly") {
            const d = new Date(now);
            const day = d.getDay();
            const diff = d.getDate() - day + (day === 0 ? -6 : 1);
            const monday = new Date(d.setDate(diff));
            this.state.filter_date_from = this.formatDateISO(monday);
            this.state.filter_date_to = this.formatDateISO(now);
        } else if (preset === "12m") {
            const past12 = new Date(now.getFullYear(), now.getMonth() - 11, 1);
            this.state.filter_date_from = this.formatDateISO(past12);
            this.state.filter_date_to = this.formatDateISO(now);
        } else {
            // "all"
            this.state.filter_date_from = false;
            this.state.filter_date_to = false;
        }
        this.loadDashboardData();
    }

    formatCompact(val) {
        const num = Number(val || 0);
        if (num >= 1000000) {
            return `${this.state.currency_symbol}${(num / 1000000).toFixed(2)}M`;
        }
        if (num >= 1000) {
            return `${this.state.currency_symbol}${(num / 1000).toFixed(1)}K`;
        }
        return `${this.state.currency_symbol}${Math.round(num).toLocaleString()}`;
    }

    formatCurrency(val) {
        const num = Number(val || 0).toLocaleString(undefined, {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });
        return `${this.state.currency_symbol}${num}`;
    }

    // Donut chart segments calculation
    get statusSegments() {
        const counts = this.state.orders_by_state || {};
        const total = this.state.total_orders || 0;
        if (total === 0) return [];

        const colors = {
            invoiced: "#8b5cf6",  // Purple
            done: "#10b981",      // Emerald green
            cancelled: "#f87171", // Coral red
            confirmed: "#3b82f6", // Blue
            submitted: "#f59e0b", // Amber
            draft: "#94a3b8",     // Slate
        };
        const labels = {
            invoiced: "Invoiced",
            done: "Done",
            cancelled: "Cancelled",
            confirmed: "Confirmed",
            submitted: "Submitted",
            draft: "Draft",
        };

        const radius = 38;
        const circumference = 2 * Math.PI * radius; // ~238.76
        let accumulated = 0;
        const segments = [];

        // Order preference: invoiced, done, cancelled, confirmed, submitted, draft
        const orderedKeys = ["invoiced", "done", "cancelled", "confirmed", "submitted", "draft"];
        for (const key of orderedKeys) {
            const count = counts[key] || 0;
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

    // 12-Month Area / Line Chart Computations
    get chartConfig() {
        const data = this.state.chart_12m || [];
        const svgW = 580;
        const svgH = 210;
        const padL = 65;
        const padR = 20;
        const padT = 20;
        const padB = 30;

        const plotW = svgW - padL - padR;
        const plotH = svgH - padT - padB;

        let maxVal = 1000;
        for (const item of data) {
            if (item.revenue > maxVal) maxVal = item.revenue;
            if (item.expense > maxVal) maxVal = item.expense;
            if (item.profit > maxVal) maxVal = item.profit;
        }

        // Round up maxVal to clean ceiling
        let step = 500000;
        if (maxVal < 100000) step = 20000;
        else if (maxVal < 500000) step = 100000;
        else if (maxVal < 2000000) step = 250000;
        else if (maxVal < 5000000) step = 500000;
        else step = 1000000;

        const ceiling = Math.ceil(maxVal / step) * step || step * 5;
        const tickSteps = 5;
        const yTicks = [];
        for (let i = 0; i <= tickSteps; i++) {
            const val = (ceiling / tickSteps) * i;
            const y = padT + plotH - (plotH * (val / ceiling));
            let label = "$0";
            if (val >= 1000000) label = `$${(val / 1000000).toFixed(1)}M`;
            else if (val >= 1000) label = `$${Math.round(val / 1000)}k`;
            yTicks.push({ val, y, label });
        }

        const count = data.length || 1;
        const stepX = plotW / (count - 1 || 1);

        const revPoints = [];
        const expPoints = [];
        const prfPoints = [];
        const xLabels = [];

        data.forEach((item, idx) => {
            const x = padL + (idx * stepX);
            const yRev = padT + plotH - (plotH * (item.revenue / ceiling));
            const yExp = padT + plotH - (plotH * (item.expense / ceiling));
            const yPrf = padT + plotH - (plotH * (item.profit / ceiling));

            revPoints.push({ x, y: yRev, val: item.revenue, month: item.full_label });
            expPoints.push({ x, y: yExp, val: item.expense, month: item.full_label });
            prfPoints.push({ x, y: yPrf, val: item.profit, month: item.full_label });
            xLabels.push({ x, label: item.label });
        });

        const revLinePath = this.buildCurvedPath(revPoints);
        const revAreaPath = this.buildAreaPath(revPoints, padT + plotH);
        const expLinePath = this.buildCurvedPath(expPoints);
        const prfLinePath = this.buildCurvedPath(prfPoints);

        return {
            svgW,
            svgH,
            padL,
            padT,
            plotH,
            yTicks,
            xLabels,
            revPoints,
            expPoints,
            prfPoints,
            revLinePath,
            revAreaPath,
            expLinePath,
            prfLinePath,
        };
    }

    buildCurvedPath(points) {
        if (!points || points.length === 0) return "";
        if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;

        let d = `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
        for (let i = 0; i < points.length - 1; i++) {
            const p0 = points[i === 0 ? 0 : i - 1];
            const p1 = points[i];
            const p2 = points[i + 1];
            const p3 = points[i + 2 < points.length ? i + 2 : i + 1];

            const cp1x = p1.x + (p2.x - p0.x) / 6;
            const cp1y = p1.y + (p2.y - p0.y) / 6;
            const cp2x = p2.x - (p3.x - p1.x) / 6;
            const cp2y = p2.y - (p3.y - p1.y) / 6;

            d += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
        }
        return d;
    }

    buildAreaPath(points, bottomY) {
        if (!points || points.length === 0) return "";
        const curved = this.buildCurvedPath(points);
        const last = points[points.length - 1];
        const first = points[0];
        return `${curved} L ${last.x.toFixed(1)} ${bottomY.toFixed(1)} L ${first.x.toFixed(1)} ${bottomY.toFixed(1)} Z`;
    }

    // Navigation and Drill-down methods
    openAllShipments(domain = [], title = "All Shipments") {
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

    openShipment(orderId) {
        if (!orderId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "freight.shipping",
            res_id: orderId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAllClearances(domain = [], title = "Custom Clearances") {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: title,
            res_model: "custom.clearance",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: domain,
            target: "current",
        });
    }

    openClearance(clearanceId) {
        if (!clearanceId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "custom.clearance",
            res_id: clearanceId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openPartner(partnerId) {
        if (!partnerId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openOrdersByState(stateVal, title) {
        this.openAllShipments([["state", "=", stateVal]], title || `${stateVal} Orders`);
    }

    openRouteShipments(route) {
        const domain = [["state", "!=", "cancelled"]];
        if (route.loading_port_id) {
            domain.push(["loading_port", "=", route.loading_port_id]);
        }
        if (route.discharge_port_id) {
            domain.push(["discharge_port_id", "=", route.discharge_port_id]);
        }
        this.openAllShipments(domain, `Shipments for ${route.name}`);
    }

    openDraftClearances() {
        this.openAllClearances([["state", "=", "draft"]], "Draft Custom Clearances");
    }

    openOverdueShipments() {
        const nowStr = this.formatDateISO(new Date());
        this.openAllShipments([
            ["expected_date", "<", nowStr],
            ["state", "not in", ["done", "cancelled"]],
        ], "Overdue Shipments");
    }

    openPendingInvoices() {
        this.openAllShipments([
            ["state", "=", "confirmed"],
            ["invoice_ids", "=", false],
        ], "Pending Invoices");
    }

    openOrders(stateFilter = null, title = "Freight Orders") {
        let domain = [];
        if (stateFilter === "active") {
            domain.push(["state", "!=", "cancelled"]);
        } else if (stateFilter) {
            domain.push(["state", "=", stateFilter]);
        }
        this.openAllShipments(domain, title);
    }
}

registry.category("actions").add("trn_freight_dashboard.dashboard", FreightDashboard);
