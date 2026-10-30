# -*- coding: utf-8 -*-
from datetime import date, datetime
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install')
class TestTransportOperations(TransactionCase):

    def setUp(self):
        super().setUp()

        # 1. Vehicle Setup
        self.brand = self.env['fleet.vehicle.model.brand'].create({'name': 'Toyota'})
        self.model = self.env['fleet.vehicle.model'].create({
            'name': 'Coaster',
            'brand_id': self.brand.id,
            'seats': 20,
        })
        self.vehicle = self.env['fleet.vehicle'].create({
            'model_id': self.model.id,
            'license_plate': 'LHR-9001',
            'seats': 20,
        })

        # 2. Route & Stops Setup
        self.partner_a = self.env['res.partner'].create({'name': 'DHA Phase 6', 'city': 'Lahore'})
        self.partner_b = self.env['res.partner'].create({'name': 'Head Office Gulberg', 'city': 'Lahore'})

        self.route = self.env['logistics.transport.route'].create({
            'name': 'DHA -> Head Office',
            'code': 'RT-DHA-HO',
            'direction': 'pickup',
            'vehicle_id': self.vehicle.id,
            'start_address_id': self.partner_a.id,
            'end_address_id': self.partner_b.id,
        })

        self.stop_pickup = self.env['logistics.transport.stop'].create({
            'name': 'DHA Main Blvd Stop',
            'route_id': self.route.id,
            'address_id': self.partner_a.id,
            'sequence': 10,
            'planned_time': 7.5,
        })
        self.stop_drop = self.env['logistics.transport.stop'].create({
            'name': 'HO Gate Stop',
            'route_id': self.route.id,
            'address_id': self.partner_b.id,
            'sequence': 20,
            'planned_time': 8.5,
        })

        # 3. Users & Employees Setup
        self.group_user = self.env.ref('trn_staff_transport.group_staff_transport_user')
        self.group_manager = self.env.ref('trn_staff_transport.group_staff_transport_manager')
        self.group_base = self.env.ref('base.group_user')

        self.normal_user = self.env['res.users'].create({
            'name': 'Normal Staff User',
            'login': 'staff_user_test10',
            'group_ids': [(6, 0, [self.group_base.id, self.group_user.id])],
        })
        self.manager_user = self.env['res.users'].create({
            'name': 'Transport Manager User',
            'login': 'transport_mgr_test10',
            'group_ids': [(6, 0, [self.group_base.id, self.group_user.id, self.group_manager.id])],
        })

        self.employee_staff = self.env['hr.employee'].create({
            'name': 'Bilal Ahmed',
            'user_id': self.normal_user.id,
            'is_transport_enabled': True,
            'transport_route_id': self.route.id,
            'pickup_stop_id': self.stop_pickup.id,
            'drop_off_stop_id': self.stop_drop.id,
        })
        self.employee_manager = self.env['hr.employee'].create({
            'name': 'Manager Kamran',
            'user_id': self.manager_user.id,
        })

    def test_01_schedule_constraints_and_weekdays(self):
        """Test schedule arrival > departure, weekday selection, and date matching."""
        # Arrival <= Departure should raise ValidationError
        with self.assertRaises(ValidationError):
            self.env['logistics.transport.schedule'].create({
                'name': 'Invalid Time Schedule',
                'route_id': self.route.id,
                'departure_time': 9.0,
                'arrival_time': 8.0,
            })

        # No weekday selected should raise ValidationError
        with self.assertRaises(ValidationError):
            self.env['logistics.transport.schedule'].create({
                'name': 'No Days Schedule',
                'route_id': self.route.id,
                'departure_time': 7.5,
                'arrival_time': 8.5,
                'mon': False, 'tue': False, 'wed': False,
                'thu': False, 'fri': False, 'sat': False, 'sun': False,
            })

        # Valid Mon-Fri schedule
        schedule = self.env['logistics.transport.schedule'].create({
            'name': 'Morning Pickup Schedule',
            'route_id': self.route.id,
            'departure_time': 7.5,
            'arrival_time': 8.5,
            'mon': True, 'tue': True, 'wed': True, 'thu': True, 'fri': True,
            'sat': False, 'sun': False,
        })
        # 2026-10-26 is Monday, 2026-11-01 is Sunday
        self.assertTrue(schedule.is_running_on_date(date(2026, 10, 26)))
        self.assertFalse(schedule.is_running_on_date(date(2026, 11, 1)))

        dt_utc = schedule.float_time_to_utc_datetime(date(2026, 10, 26), 7.5)
        self.assertIsInstance(dt_utc, datetime)

    def test_02_trip_lifecycle_and_passenger_attendance(self):
        """Test trip sequence, capacity, timestamps, and passenger board/drop/no-show."""
        trip = self.env['logistics.transport.trip'].create({
            'date': date(2026, 10, 26),
            'route_id': self.route.id,
            'direction': 'pickup',
            'vehicle_id': self.vehicle.id,
            'passenger_ids': [(0, 0, {
                'employee_id': self.employee_staff.id,
                'pickup_stop_id': self.stop_pickup.id,
                'drop_off_stop_id': self.stop_drop.id,
            })],
        })
        self.assertTrue(trip.name.startswith('TRIP/'))
        self.assertEqual(trip.passenger_count, 1)
        self.assertEqual(trip.capacity, 20)
        self.assertEqual(trip.free_seats, 19)
        self.assertFalse(trip.over_capacity)

        # Lifecycle transitions
        trip.action_confirm()
        self.assertEqual(trip.state, 'planned')

        trip.action_start()
        self.assertEqual(trip.state, 'in_progress')
        self.assertTrue(trip.actual_departure_time)

        # Passenger Board & Drop
        passenger = trip.passenger_ids[0]
        self.assertEqual(passenger.status, 'expected')

        passenger.action_board()
        self.assertEqual(passenger.status, 'boarded')
        self.assertTrue(passenger.boarding_time)

        passenger.action_drop()
        self.assertEqual(passenger.status, 'dropped')
        self.assertTrue(passenger.drop_time)

        # Complete trip
        trip.action_complete()
        self.assertEqual(trip.state, 'completed')
        self.assertTrue(trip.actual_arrival_time)

        # Completed trip cannot be cancelled
        with self.assertRaises(UserError):
            trip.action_cancel()

    def test_03_generate_daily_trips_wizard_idempotency(self):
        """Test wizard generates trips for active weekday schedules without duplicates."""
        schedule = self.env['logistics.transport.schedule'].create({
            'name': 'Morning Pickup',
            'route_id': self.route.id,
            'departure_time': 7.5,
            'arrival_time': 8.5,
            'mon': True, 'tue': True, 'wed': True, 'thu': True, 'fri': True,
            'sat': False, 'sun': False,
        })

        monday_date = date(2026, 10, 26)  # Monday
        wizard_1 = self.env['generate.daily.trips.wizard'].create({
            'date': monday_date,
            'route_ids': [(6, 0, [self.route.id])],
            'direction': 'both',
        })
        action = wizard_1.action_generate_trips()
        self.assertEqual(action['res_model'], 'logistics.transport.trip')

        trips = self.env['logistics.transport.trip'].search([
            ('date', '=', monday_date),
            ('schedule_id', '=', schedule.id),
        ])
        self.assertEqual(len(trips), 1)
        self.assertEqual(trips.state, 'planned')
        self.assertEqual(len(trips.passenger_ids), 1)
        self.assertEqual(trips.passenger_ids[0].employee_id, self.employee_staff)

        # Running wizard a second time for same date should not create duplicates (idempotent)
        wizard_2 = self.env['generate.daily.trips.wizard'].create({
            'date': monday_date,
            'route_ids': [(6, 0, [self.route.id])],
            'direction': 'both',
        })
        wizard_2.action_generate_trips()

        trips_after = self.env['logistics.transport.trip'].search([
            ('date', '=', monday_date),
            ('schedule_id', '=', schedule.id),
        ])
        self.assertEqual(len(trips_after), 1)

        # Running wizard on Sunday (where sun=False) raises UserError
        sunday_date = date(2026, 11, 1)
        wizard_sun = self.env['generate.daily.trips.wizard'].create({
            'date': sunday_date,
            'route_ids': [(6, 0, [self.route.id])],
            'direction': 'both',
        })
        with self.assertRaises(UserError):
            wizard_sun.action_generate_trips()

    def test_04_vehicle_request_workflow_overlap_and_security(self):
        """Test vehicle request dates, manager approval, self-approval block, overlap, and unlink."""
        # 1. Invalid dates (to <= from) raises ValidationError
        with self.assertRaises(ValidationError):
            self.env['logistics.transport.vehicle.request'].create({
                'employee_id': self.employee_staff.id,
                'from_datetime': datetime(2026, 10, 28, 12, 0, 0),
                'to_datetime': datetime(2026, 10, 28, 10, 0, 0),
                'purpose': 'Invalid time test',
            })

        # 2. Valid request creation
        req1 = self.env['logistics.transport.vehicle.request'].create({
            'employee_id': self.employee_staff.id,
            'from_datetime': datetime(2026, 10, 28, 9, 0, 0),
            'to_datetime': datetime(2026, 10, 28, 12, 0, 0),
            'purpose': 'Client visit at Gulberg',
            'vehicle_id': self.vehicle.id,
        })
        self.assertTrue(req1.name.startswith('VR/'))
        self.assertEqual(req1.state, 'draft')

        req1.action_submit()
        self.assertEqual(req1.state, 'submitted')

        # 3. Non-manager cannot approve
        with self.assertRaises(UserError):
            req1.with_user(self.normal_user).action_approve()

        # 4. Self-approval blocked (Manager requesting for themselves)
        req_self = self.env['logistics.transport.vehicle.request'].create({
            'employee_id': self.employee_manager.id,
            'from_datetime': datetime(2026, 10, 29, 9, 0, 0),
            'to_datetime': datetime(2026, 10, 29, 11, 0, 0),
            'purpose': 'Manager personal visit',
        })
        req_self.action_submit()
        with self.assertRaises(UserError):
            req_self.with_user(self.manager_user).action_approve()

        # 5. Manager approves staff request
        req1.with_user(self.manager_user).action_approve()
        self.assertEqual(req1.state, 'approved')
        self.assertEqual(req1.approver_id, self.manager_user)

        # 6. Assign vehicle
        req1.action_assign()
        self.assertEqual(req1.state, 'assigned')

        # 7. Overlapping request for same vehicle fails when approved
        req_overlap = self.env['logistics.transport.vehicle.request'].create({
            'employee_id': self.employee_staff.id,
            'from_datetime': datetime(2026, 10, 28, 10, 30, 0),
            'to_datetime': datetime(2026, 10, 28, 13, 0, 0),
            'purpose': 'Overlapping airport pickup',
            'vehicle_id': self.vehicle.id,
        })
        req_overlap.action_submit()
        with self.assertRaises(ValidationError):
            req_overlap.with_user(self.manager_user).action_approve()

        # 8. Unlink restriction on assigned/approved/done
        with self.assertRaises(UserError):
            req1.unlink()

        # Complete request
        req1.action_done()
        self.assertEqual(req1.state, 'done')
