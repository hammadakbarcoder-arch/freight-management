# -*- coding: utf-8 -*-
{
    'name': 'Staff Transport Management',
    'version': '19.0.1.0.0',
    'summary': 'Manage staff transport routes, stops, vehicle capacity and maps',
    'description': """
Staff Transport Management System
==================================
Extends Fleet and HR modules to manage:
- Logistics Transport Routes & Stops
- Route Stops Drag-and-Drop Sequence
- Vehicle Capacity & Route Occupancy %
- Employee Route & Stop Assignments
- Interactive Map Views & Google Maps Integration
    """,
    'category': 'Human Resources/Fleet',
    'author': 'Hammad Akbar',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'fleet',
        'contacts',
        'mail',
        'web_map',
    ],
    'data': [
        'security/transport_security.xml',
        'security/ir.model.access.csv',
        'views/transport_route_views.xml',
        'views/transport_stop_views.xml',
        'views/transport_menus.xml',
        'views/fleet_vehicle_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
