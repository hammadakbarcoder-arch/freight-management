# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class GenerateDailyTripsWizard(models.TransientModel):
    _name = 'generate.daily.trips.wizard'
    _description = 'Generate Daily Trips Wizard'

    date = fields.Date(
        string='Date', required=True, default=fields.Date.context_today
    )
    direction = fields.Selection(
        [
            ('pickup', 'Pickup'),
            ('drop_off', 'Drop-off'),
            ('both', 'Both')
        ],
        string='Direction', default='both', required=True
    )
    route_ids = fields.Many2many(
        'logistics.transport.route', string='Routes',
        help='Select specific routes or leave empty to generate for all active routes.'
    )

    def action_generate_trips(self):
        self.ensure_one()
        Trip = self.env['logistics.transport.trip']
        Schedule = self.env['logistics.transport.schedule']
        Route = self.env['logistics.transport.route']

        # 1. Routes filter karein (Archived routes ko skip karein)
        routes = self.route_ids if self.route_ids else Route.search([])
        routes = routes.filtered(lambda r: getattr(r, 'active', True))

        if not routes:
            raise UserError(_("No active routes found to generate trips!"))

        # 2. Schedules dhoondein
        schedule_domain = [('route_id', 'in', routes.ids), ('active', '=', True)]
        if self.direction != 'both':
            schedule_domain.append(('direction', 'in', [self.direction, 'both']))

        schedules = Schedule.search(schedule_domain)
        # Sirf woh schedules jo is date ke weekday par run karte hain
        matching_schedules = schedules.filtered(lambda s: s.is_running_on_date(self.date))

        if not matching_schedules:
            raise UserError(_("No schedules are running on %s for the selected routes.") % self.date)

        created_trips = Trip.browse()

        # 3. Har schedule ke liye trip banayein (Duplicate Check / Idempotent)
        for sched in matching_schedules:
            # Check karein agar is date aur schedule ki trip pehle se bani hui hai
            existing_trip = Trip.search([
                ('date', '=', self.date),
                ('schedule_id', '=', sched.id),
                ('state', '!=', 'cancelled')
            ], limit=1)

            if existing_trip:
                # Agar pehle se bani hai toh duplicate create nahi karni (Skip)
                continue

            # Route ke assigned employees ko passengers banayein
            passenger_lines = []
            for emp in sched.route_id.employee_ids:
                passenger_lines.append((0, 0, {
                    'employee_id': emp.id,
                    'pickup_stop_id': emp.pickup_stop_id.id if emp.pickup_stop_id else False,
                    'drop_off_stop_id': emp.drop_off_stop_id.id if emp.drop_off_stop_id else False,
                    'status': 'expected',
                }))

            trip_vals = {
                'date': self.date,
                'route_id': sched.route_id.id,
                'schedule_id': sched.id,
                'direction': sched.direction or sched.route_id.direction or 'both',
                'vehicle_id': sched.effective_vehicle_id.id or sched.route_id.vehicle_id.id or False,
                'driver_id': sched.effective_driver_id.id or sched.route_id.driver_id.id or False,
                'company_id': sched.company_id.id,
                'state': 'planned',
                'planned_departure_time': sched.float_time_to_utc_datetime(self.date, sched.departure_time),
                'planned_arrival_time': sched.float_time_to_utc_datetime(self.date, sched.arrival_time),
                'passenger_ids': passenger_lines,
            }
            new_trip = Trip.create(trip_vals)
            created_trips |= new_trip

        # 4. Resulting trips open karein
        return {
            'name': _('Daily Trips (%s)') % self.date,
            'type': 'ir.actions.act_window',
            'res_model': 'logistics.transport.trip',
            'view_mode': 'list,form',
            'domain': [('date', '=', self.date)],
            'context': {'search_default_group_route': 1},
        }
