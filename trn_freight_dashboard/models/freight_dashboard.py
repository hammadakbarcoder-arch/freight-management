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

        # Clean filter parameters
        date_from = date_from or None
        date_to = date_to or None
        transport = transport if transport and transport != 'all' else None
        status = status if status and status != 'all' else None

        # Base filter domain (order_date range + transport mode)
        base_domain = []
        if date_from:
            base_domain.append(('order_date', '>=', date_from))
        if date_to:
            base_domain.append(('order_date', '<=', date_to))
        if transport:
            base_domain.append(('transport', '=', transport))

        # 1. Orders count per state (matching date + transport + optional status)
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

        # 2. Revenue & Expense of active orders (state != 'cancelled' or specific active status)
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

        # 3. Monthly Revenue vs Expense Trend
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

        # Generate month sequence (up to 12 months for chart display)
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

        return {
            'orders_by_state': state_counts,
            'total_orders': total_orders,
            'active_orders': active_orders,
            'total_revenue': total_revenue,
            'total_expense': total_expense,
            'net_margin': net_margin,
            'currency_symbol': self.env.company.currency_id.symbol or '$',
            'monthly_data': [months_map[k] for k in months_order],
        }
