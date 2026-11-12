# -*- coding: utf-8 -*-
{
    'name': 'Freight Dashboard (OWL)',
    'version': '19.0.1.0.0',
    'summary': 'Interactive OWL Dashboard for Freight Management',
    'description': """
Freight Management Dashboard
============================
- Live KPI Cards (Orders per state, Total Revenue, Total Expense, Net Margin)
- Last 6 Months Revenue vs Expense Trend Chart
- Status Distribution Donut Chart
- Quick Presets & Custom Date Range Filtering
- Interactive drill-down to filtered Freight Orders
    """,
    'category': 'Operations/Logistics',
    'author': 'Hammad Akbar',
    'maintainer': 'Hammad Akbar',
    'website': 'https://hammad-akbar-odoo-store.netlify.app',
    'support': 'rrajahammadakbar@gmail.com',
    'license': 'OPL-1',
    'price': 34.00,
    'currency': 'USD',
    'images': ['static/description/banner.png'],
    'depends': [
        'trn_freight',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'trn_freight_dashboard/static/src/scss/freight_dashboard.scss',
            'trn_freight_dashboard/static/src/xml/freight_dashboard.xml',
            'trn_freight_dashboard/static/src/js/freight_dashboard.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
