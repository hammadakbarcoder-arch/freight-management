# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, AccessError


@tagged('post_install', '-at_install')
class TestStaffTransport(TransactionCase):

    def setUp(self):
        super().setUp()

        # 1. Test Partners (Addresses)
        self.partner_start = self.env['res.partner'].create({
            'name': 'Start Hub Gulberg',
            'street': 'Main Boulevard Gulberg',
            'city': 'Lahore',
        })
        self.partner_stop1 = self.env['res.partner'].create({
            'name': 'Stop 1 Kalma Chowk',
            'street': 'Ferozepur Road',
            'city': 'Lahore',
        })
        self.partner_end = self.env['res.partner'].create({
            'name': 'Head Office DHA Phase 5',
            'street': 'DHA Phase 5',
            'city': 'Lahore',
        })

        # 2. Test Fleet Vehicle
        self.brand = self.env['fleet.vehicle.model.brand'].create({'name': 'Toyota'})
        self.model = self.env['fleet.vehicle.model'].create({
            'name': 'Hiace Grand Cabin',
            'brand_id': self.brand.id,
            'seats': 14,
        })
        self.vehicle = self.env['fleet.vehicle'].create({
            'model_id': self.model.id,
            'license_plate': 'LEA-1234',
            'seats': 14,
        })

        # 3. Test Route
        self.route = self.env['logistics.transport.route'].create({
            'name': 'Morning Route A - Gulberg to DHA',
            'code': 'M-GUL-DHA',
            'direction': 'pickup',
            'vehicle_id': self.vehicle.id,
            'start_address_id': self.partner_start.id,
            'end_address_id': self.partner_end.id,
            'company_id': self.env.company.id,
        })

        # 4. Test Stops
        self.stop_1 = self.env['logistics.transport.stop'].create({
            'name': 'Kalma Chowk Stop',
            'route_id': self.route.id,
            'address_id': self.partner_stop1.id,
            'sequence': 10,
            'planned_time': 7.5,
        })
        self.stop_2 = self.env['logistics.transport.stop'].create({
            'name': 'DHA Gate Stop',
            'route_id': self.route.id,
            'address_id': self.partner_end.id,
            'sequence': 20,
            'planned_time': 8.0,
        })

        # 5. Test Employee
        self.employee_1 = self.env['hr.employee'].create({
            'name': 'Ali Khan',
            'is_transport_enabled': True,
            'transport_route_id': self.route.id,
            'pickup_stop_id': self.stop_1.id,
            'drop_off_stop_id': self.stop_2.id,
        })

    def test_01_fleet_vehicle_capacity_and_trips(self):
        """1. Test vehicle default capacity vs override aur Trips smart button."""
        # Standard capacity = 14
        self.assertEqual(self.vehicle.effective_capacity, 14)

        # Override capacity = 20
        self.vehicle.seat_capacity_override = 20
        self.assertEqual(self.vehicle.effective_capacity, 20)

        # Vehicle ke trips count = 1
        self.assertEqual(self.vehicle.trip_count, 1)

        # Smart button action check
        action = self.vehicle.action_view_transport_routes()
        self.assertEqual(action['res_model'], 'logistics.transport.route')

    def test_02_route_capacity_and_occupancy(self):
        """2. Test stops count, employee count, capacity aur occupancy %."""
        self.assertEqual(self.route.stop_count, 2)
        self.assertEqual(self.route.employee_count, 1)
        self.assertEqual(self.route.capacity, 14)
        self.assertAlmostEqual(self.route.occupancy_percent, 1.0 / 14.0, places=4)

        # Doosra employee add karo
        self.env['hr.employee'].create({
            'name': 'Usman Tariq',
            'is_transport_enabled': True,
            'transport_route_id': self.route.id,
        })
        self.assertEqual(self.route.employee_count, 2)
        self.assertAlmostEqual(self.route.occupancy_percent, 2.0 / 14.0, places=4)

        # Vehicle remove karo toh capacity 0 aur occupancy 0.0 honi chahiye
        self.route.vehicle_id = False
        self.assertEqual(self.route.capacity, 0)
        self.assertEqual(self.route.occupancy_percent, 0.0)

    def test_03_employee_stop_constraints_and_onchange(self):
        """3. Test employee stop validation (cross-route stop error) aur onchange reset."""
        # Route B banao
        route_b = self.env['logistics.transport.route'].create({
            'name': 'Evening Route B',
            'code': 'E-DHA-GUL',
            'direction': 'drop_off',
        })
        stop_b = self.env['logistics.transport.stop'].create({
            'name': 'Route B Unique Stop',
            'route_id': route_b.id,
            'address_id': self.partner_stop1.id,
        })

        # Error check: Route A ke employee ko Route B ka stop dene par ValidationError aana chahiye
        with self.assertRaises(ValidationError):
            self.employee_1.pickup_stop_id = stop_b.id

        # Onchange check: Route change karne par purane stops reset (False) ho jane chahiye
        emp_temp = self.env['hr.employee'].new({
            'name': 'Temp Employee',
            'transport_route_id': self.route.id,
            'pickup_stop_id': self.stop_1.id,
            'drop_off_stop_id': self.stop_2.id,
        })
        emp_temp.transport_route_id = route_b
        emp_temp._onchange_transport_route_id()
        self.assertFalse(emp_temp.pickup_stop_id)
        self.assertFalse(emp_temp.drop_off_stop_id)

    def test_04_route_actions_and_google_maps(self):
        """4. Test Google Maps URL generation aur View Stops Map action."""
        # Stops action
        act_stops = self.route.action_view_stops()
        self.assertEqual(act_stops['res_model'], 'logistics.transport.stop')

        # Map action
        act_map = self.route.action_view_stops_on_map()
        self.assertIn('map', act_map['view_mode'])

        # Google Maps URL action
        act_url = self.route.action_open_google_maps()
        self.assertEqual(act_url['type'], 'ir.actions.act_url')
        self.assertTrue(act_url['url'].startswith('https://www.google.com/maps/dir/?'))
        self.assertIn('api=1', act_url['url'])

    def test_05_multi_company_security_isolation(self):
        """5. Test multi-company isolation: Company B ka user Company A ka route nahi parh sakta."""
        company_b = self.env['res.company'].create({'name': 'Transport Company B'})
        user_b = self.env['res.users'].create({
            'name': 'User B',
            'login': 'user_b_transport_test',
            'company_id': company_b.id,
            'company_ids': [(6, 0, [company_b.id])],
            'group_ids': [(6, 0, [
                self.env.ref('base.group_user').id,
                self.env.ref('trn_staff_transport.group_staff_transport_user').id,
            ])],
        })

        # Company B ka user Company A ke route ko read karega toh AccessError aana chahiye
        with self.assertRaises(AccessError):
            self.route.with_user(user_b).read(['name'])