# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class FreightDashboard(models.AbstractModel):
    _name = 'freight.dashboard'
    _description = 'Freight Management Dashboard'

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None, transport=None, status=None):
        Order = self.env['freight.shipping']
        Clearance = self.env['custom.clearance']

        # Clean filter parameters
        date_from = date_from or None
        date_to = date_to or None
        transport = transport if transport and transport != 'all' else None
        status = status if status and status != 'all' else None

        # Multi-Company scoping: Only show data for currently active company/companies
        company_ids = self.env.companies.ids if self.env.companies else [self.env.company.id]
        company_domain = ['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]

        # Base filter domain (multi-company + order_date range + transport mode)
        base_domain = list(company_domain)
        if date_from:
            base_domain.append(('order_date', '>=', date_from))
        if date_to:
            base_domain.append(('order_date', '<=', date_to))
        if transport:
            base_domain.append(('transport', '=', transport))

        # 1. Orders count per state
        state_counts_domain = list(base_domain)
        if status:
            state_counts_domain.append(('state', '=', status))

        state_counts = {
            'draft': 0,
            'submitted': 0,
            'confirmed': 0,
            'invoiced': 0,
            'done': 0,
            'cancelled': 0,
        }
        for state_val, count in Order._read_group(state_counts_domain, ['state'], ['__count']):
            if state_val in state_counts:
                state_counts[state_val] = count

        total_orders = sum(state_counts.values())
        active_orders = total_orders - state_counts['cancelled']

        # KPI derived counters
        in_transit_orders = state_counts['submitted'] + state_counts['confirmed']
        delivered_orders = state_counts['done']
        awaiting_action_orders = state_counts['draft']

        # 2. Revenue & Expense of active orders
        active_domain = list(base_domain)
        if status:
            active_domain.append(('state', '=', status))
        else:
            active_domain.append(('state', '!=', 'cancelled'))

        totals = Order._read_group(
            active_domain,
            [],
            ['cargo_total:sum', 'routes_total:sum', 'service_total_sale:sum']
        )
        cargo_sum, routes_sum, service_sum = totals[0] if totals else (0.0, 0.0, 0.0)
        cargo_sum = cargo_sum or 0.0
        routes_sum = routes_sum or 0.0
        service_sum = service_sum or 0.0

        total_revenue = round(cargo_sum + routes_sum + service_sum, 2)
        total_expense = round(service_sum, 2)
        net_margin = round(total_revenue - total_expense, 2)
        profit_margin_pct = round(((total_revenue - total_expense) / total_revenue) * 100, 1) if total_revenue > 0 else 0.0

        # Delivered rate percentage
        delivered_rate_pct = round((state_counts['done'] / (active_orders or total_orders or 1)) * 100)
        tracked_states_count = sum(1 for v in state_counts.values() if v > 0)

        # 3. Monthly Revenue vs Expense Trend (6 months for test compatibility)
        today = fields.Date.context_today(self)
        if date_from:
            try:
                start_dt = datetime.strptime(str(date_from)[:10], '%Y-%m-%d').date()
            except Exception:
                start_dt = today.replace(day=1) - relativedelta(months=5)
        else:
            start_dt = today.replace(day=1) - relativedelta(months=5)

        if date_to:
            try:
                end_dt = datetime.strptime(str(date_to)[:10], '%Y-%m-%d').date()
            except Exception:
                end_dt = today
        else:
            end_dt = today

        months_map = {}
        months_order = []
        cur_m = start_dt.replace(day=1)
        target_end_m = end_dt.replace(day=1)
        count_m = 0
        while cur_m <= target_end_m and count_m < 12:
            m_key = cur_m.strftime('%Y-%m')
            months_order.append(m_key)
            months_map[m_key] = {
                'month': cur_m.strftime('%b %Y'),
                'revenue': 0.0,
                'expense': 0.0,
            }
            cur_m += relativedelta(months=1)
            count_m += 1

        if not months_order:
            m_key = today.strftime('%Y-%m')
            months_order.append(m_key)
            months_map[m_key] = {
                'month': today.strftime('%b %Y'),
                'revenue': 0.0,
                'expense': 0.0,
            }

        monthly_domain = list(active_domain)
        monthly_domain.append(('order_date', '>=', months_order[0] + '-01'))

        monthly_groups = Order._read_group(
            monthly_domain,
            ['order_date:month'],
            ['cargo_total:sum', 'routes_total:sum', 'service_total_sale:sum']
        )
        for month_dt, m_cargo, m_routes, m_service in monthly_groups:
            if month_dt:
                m_key = month_dt.strftime('%Y-%m')
                if m_key in months_map:
                    m_rev = round((m_cargo or 0.0) + (m_routes or 0.0) + (m_service or 0.0), 2)
                    m_exp = round(m_service or 0.0, 2)
                    months_map[m_key]['revenue'] = m_rev
                    months_map[m_key]['expense'] = m_exp

        # 4. 12-Month Timeline Data for Executive Area Chart (Dec - Nov timeline)
        chart_12m = []
        chart_12m_map = {}
        for i in range(11, -1, -1):
            m_date = today.replace(day=1) - relativedelta(months=i)
            mk = m_date.strftime('%Y-%m')
            item = {
                'key': mk,
                'label': m_date.strftime('%b'),
                'full_label': m_date.strftime('%b %Y'),
                'revenue': 0.0,
                'expense': 0.0,
                'profit': 0.0,
            }
            chart_12m.append(item)
            chart_12m_map[mk] = item

        chart_12m_domain = list(active_domain)
        chart_12m_domain.append(('order_date', '>=', chart_12m[0]['key'] + '-01'))

        chart_12m_groups = Order._read_group(
            chart_12m_domain,
            ['order_date:month'],
            ['cargo_total:sum', 'routes_total:sum', 'service_total_sale:sum']
        )
        for month_dt, c_cargo, c_routes, c_service in chart_12m_groups:
            if month_dt:
                mk = month_dt.strftime('%Y-%m')
                if mk in chart_12m_map:
                    c_rev = round((c_cargo or 0.0) + (c_routes or 0.0) + (c_service or 0.0), 2)
                    c_exp = round(c_service or 0.0, 2)
                    chart_12m_map[mk]['revenue'] = c_rev
                    chart_12m_map[mk]['expense'] = c_exp
                    chart_12m_map[mk]['profit'] = max(0.0, round(c_rev - c_exp, 2))

        # 5. Shipments by Top Routes (Grouped by loading_port -> discharge_port)
        top_routes = []
        route_palette = ['#f97316', '#3b82f6', '#10b981', '#ea580c', '#8b5cf6']
        route_groups = Order._read_group(
            active_domain,
            ['loading_port', 'discharge_port_id'],
            ['__count']
        )
        sorted_routes = sorted(route_groups, key=lambda x: x[2], reverse=True)[:5]
        max_route_count = sorted_routes[0][2] if sorted_routes else 1
        for idx, (l_port, d_port, cnt) in enumerate(sorted_routes):
            lp_name = l_port.name if l_port else 'Origin'
            dp_name = d_port.name if d_port else 'Destination'
            pct = max(10, min(100, round((cnt / max_route_count) * 100)))
            top_routes.append({
                'name': f"{lp_name} → {dp_name}",
                'count': cnt,
                'percentage': pct,
                'color': route_palette[idx % len(route_palette)],
                'loading_port_id': l_port.id if l_port else False,
                'discharge_port_id': d_port.id if d_port else False,
            })

        # 6. Booking Pipeline Counters & Pending Tasks (multi-company scoped)
        pending_invoices_cnt = Order.search_count(company_domain + [
            ('state', '=', 'confirmed'),
            ('invoice_ids', '=', False),
        ])
        pending_clearances_cnt = Clearance.search_count(company_domain + [('state', '=', 'draft')])

        booking_pipeline = {
            'draft': state_counts['draft'],
            'submitted': state_counts['submitted'],
            'confirmed': state_counts['confirmed'],
            'invoiced': state_counts['invoiced'],
            'done': state_counts['done'],
            'pending_invoices': pending_invoices_cnt,
            'pending_clearances': pending_clearances_cnt,
        }

        # 7. Recent Shipments (Scoped to active companies)
        recent_shipments = []
        for o in Order.search(company_domain, order='id desc', limit=6):
            lp_str = o.loading_port.name or ''
            dp_str = o.discharge_port_id.name or ''
            r_str = f"{lp_str} → {dp_str}" if (lp_str or dp_str) else 'Direct'
            recent_shipments.append({
                'id': o.id,
                'name': o.name,
                'shipper': o.shipper_id.name or 'Unknown',
                'route': r_str,
                'state': o.state,
            })

        # 8. Recent Clearances (Scoped to active companies)
        recent_clearances = []
        for c in Clearance.search(company_domain, order='id desc', limit=6):
            recent_clearances.append({
                'id': c.id,
                'name': c.name,
                'shipment': c.freight_id.name if c.freight_id else 'N/A',
                'agent': c.agent_id.name or 'N/A',
                'state': c.state,
            })

        # 9. Alerts & Notifications (Scoped to active companies)
        draft_clearances_alert = Clearance.search_count(company_domain + [('state', '=', 'draft')])
        overdue_orders_alert = Order.search_count(company_domain + [
            ('expected_date', '<', today),
            ('state', 'not in', ['done', 'cancelled'])
        ])

        # 10. Top Shippers (Scoped to active companies)
        top_shippers = []
        shipper_groups = Order._read_group(
            active_domain,
            ['shipper_id'],
            ['__count']
        )
        sorted_shippers = sorted(shipper_groups, key=lambda x: x[1], reverse=True)[:5]
        total_active_shippers_cnt = sum(x[1] for x in sorted_shippers) or 1
        for rank, (partner, cnt) in enumerate(sorted_shippers, start=1):
            pct = round((cnt / total_active_shippers_cnt) * 100)
            top_shippers.append({
                'rank': rank,
                'id': partner.id if partner else False,
                'name': partner.name if partner else 'Unknown',
                'count': cnt,
                'percentage': pct,
            })

        return {
            'orders_by_state': state_counts,
            'total_orders': total_orders,
            'active_orders': active_orders,
            'in_transit_orders': in_transit_orders,
            'delivered_orders': delivered_orders,
            'awaiting_action_orders': awaiting_action_orders,
            'total_revenue': total_revenue,
            'total_expense': total_expense,
            'net_margin': net_margin,
            'profit_margin_pct': profit_margin_pct,
            'delivered_rate_pct': delivered_rate_pct,
            'tracked_states_count': tracked_states_count,
            'currency_symbol': self.env.company.currency_id.symbol or '$',
            'monthly_data': [months_map[k] for k in months_order],
            'chart_12m': chart_12m,
            'top_routes': top_routes,
            'booking_pipeline': booking_pipeline,
            'recent_shipments': recent_shipments,
            'recent_clearances': recent_clearances,
            'alerts': {
                'draft_clearances': draft_clearances_alert,
                'overdue_shipments': overdue_orders_alert,
            },
            'top_shippers': top_shippers,
        }
