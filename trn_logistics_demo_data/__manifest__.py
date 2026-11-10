# -*- coding: utf-8 -*-
{
    'name': 'Logistics & Staff Transport Demo Data',
    'version': '18.0.1.0.0',
    'category': 'Logistics',
    'summary': 'End-to-End Master & Operational Demo Data for Freight & Staff Transport',
    'author': 'Hammad Akbar',
    'website': 'https://apps.odoo.com/apps/modules/browse?author=Hammad%20Akbar',
    'support': 'rrajahammadakbar@gmail.com',
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
    'depends': [
        'trn_freight',
        'trn_staff_transport',
        'trn_freight_dashboard',
    ],
    'data': [
        'data/01_partners_and_company.xml',
        'data/02_ports_containers_catalog.xml',
        'data/03_freight_orders_demo.xml',
        'data/04_staff_transport_master.xml',
        'data/05_staff_transport_operations.xml',
    ],
    'installable': True,
    'application': False,
}