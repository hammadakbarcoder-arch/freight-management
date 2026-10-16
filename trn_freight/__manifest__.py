# -*- coding: utf-8 -*-
{
    'name': 'Freight Management System',
    'version': '19.0.1.0.0',
    'summary': 'Manage Freight Ports, Containers, Prices, Routes, and Services',
    'category': 'Logistics',
    'author': 'Hammad',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'uom', 'mail', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/freight_port_views.xml',
        'views/freight_container_views.xml',
        'views/freight_price_views.xml',
        'views/freight_service_views.xml',
        'views/freight_routes_views.xml',
        'views/freight_shipping_views.xml',
        'views/freight_menus.xml',
    ],
    'installable': True,
    'application': True,
}
