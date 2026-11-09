# -*- coding: utf-8 -*-
{
    'name': 'Freight Management System',
    'version': '19.0.1.0.0',
    'summary': 'Manage Freight Ports, Containers, Prices, Routes, Services, and Customs Clearance',
    'description': """
Freight Management System for Odoo 19
=====================================
A complete end-to-end multimodal logistics and shipping management suite.
- Multimodal freight (Ocean, Air, Land)
- Port & Container Management
- Automated Freight Pricing & Quotations
- Route Management with stops
- Customs Clearance Tracking
- Direct Invoicing & Accounting Integration
- Interactive OWL Executive Dashboard
    """,
    'category': 'Operations/Logistics',
    'author': 'Hammad Akbar',
    'website': 'https://github.com/hammadakbarcoder-arch',
    'support': 'rrajahammadakbar@gmail.com',
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
    'depends': ['base', 'web', 'uom', 'mail', 'product', 'account'],
    'data': [
        'security/freight_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/freight_port_views.xml',
        'views/freight_container_views.xml',
        'views/freight_price_views.xml',
        'views/freight_service_views.xml',
        'views/freight_routes_views.xml',
        'views/freight_shipping_views.xml',
        'views/custom_clearance_views.xml',
        'views/freight_menus.xml',
        'report/freight_shipping_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
