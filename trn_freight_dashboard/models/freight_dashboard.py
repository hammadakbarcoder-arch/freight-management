# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class FreightDashboard(models.AbstractModel):
    _name = 'freight.dashboard'
    _description = 'Freight Management Dashboard'

    @api.model
    def get_dashboard_data(self):
        Order = self.env['freight.shipping']

        # 1. Orders count per state
        state_counts = {
            'draft': 0,
            'submitted': 0,
            'confirmed': 0,
            'invoiced': 0,
            'done': 0,
            'cancelled': 0,
        }
        for state_val, count in Order._read_group([], ['state'], ['__count']):
            if state_val in state_counts:
                state_counts[state_val] = count

        total_orders = sum(state_counts.values())
        active_orders = total_orders - state_counts['cancelled']

        # 2. Revenue & Expense of active orders (state != 'cancelled')
        totals = Order._read_group(
            [('state', '!=', 'cancelled')],
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

        # 3. Last 6 Months Revenue vs Expense
        today = fields.Date.context_today(self)
        start_month = today.replace(day=1) - relativedelta(months=5)

        months_map = {}
        months_order = []
        for i in range(6):
            m_date = start_month + relativedelta(months=i)
            m_key = m_date.strftime('%Y-%m')
            months_order.append(m_key)
            months_map[m_key] = {
                'month': m_date.strftime('%b %Y'),
                'revenue': 0.0,
                'expense': 0.0,
            }

        monthly_groups = Order._read_group(
            [('state', '!=', 'cancelled'), ('order_date', '>=', start_month)],
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
