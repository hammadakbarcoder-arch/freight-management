# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LogisticsTransportTrip(models.Model):
    _name = 'logistics.transport.trip'
    _description = 'Logistics Transport Trip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Trip Number', required=True, copy=False, readonly=True,
        default='New', tracking=True
    )
    date = fields.Date(
        string='Date', required=True, default=fields.Date.context_today,
        tracking=True
    )
    route_id = fields.Many2one(
        'logistics.transport.route', string='Route', tracking=True
    )
    schedule_id = fields.Many2one(
        'logistics.transport.schedule', string='Schedule',
        domain="[('route_id', '=', route_id)]" if 'route_id' else [], tracking=True
    )
    direction = fields.Selection(
        [
            ('pickup', 'Pickup'),
            ('drop_off', 'Drop-off'),
            ('both', 'Both')
        ],
        string='Direction', required=True, default='both', tracking=True
    )
    vehicle_id = fields.Many2one(
        'fleet.vehicle', string='Vehicle', tracking=True
    )
    driver_id = fields.Many2one(
        'res.partner', string='Driver', tracking=True
    )
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company, store=True
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('planned', 'Planned'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled')
        ],
        string='Status', default='draft', required=True, tracking=True
    )
    planned_departure_time = fields.Datetime(
        string='Planned Departure', tracking=True
    )
    planned_arrival_time = fields.Datetime(
        string='Planned Arrival', tracking=True
    )
    actual_departure_time = fields.Datetime(
        string='Actual Departure', readonly=True, tracking=True
    )
    actual_arrival_time = fields.Datetime(
        string='Actual Arrival', readonly=True, tracking=True
    )

    passenger_ids = fields.One2many(
        'logistics.transport.trip.passenger', 'trip_id', string='Passengers'
    )
    passenger_count = fields.Integer(
        string='Passenger Count', compute='_compute_passenger_metrics', store=True, tracking=True
    )
    capacity = fields.Integer(
        string='Capacity', compute='_compute_passenger_metrics', store=True
    )
    free_seats = fields.Integer(
        string='Available Seats', compute='_compute_passenger_metrics', store=True
    )
    occupancy_percent = fields.Float(
        string='Occupancy %', compute='_compute_passenger_metrics', store=True
    )
    over_capacity = fields.Boolean(
        string='Over Capacity', compute='_compute_passenger_metrics', store=True
    )
    notes = fields.Text(string='Notes')

    @api.depends('passenger_ids', 'passenger_ids.status', 'vehicle_id', 'vehicle_id.effective_capacity')
    def _compute_passenger_metrics(self):
        for trip in self:
            active_passengers = trip.passenger_ids.filtered(lambda p: p.status != 'cancelled')
            trip.passenger_count = len(active_passengers)
            trip.capacity = trip.vehicle_id.effective_capacity if trip.vehicle_id else 0
            trip.free_seats = max(0, trip.capacity - trip.passenger_count)
            if trip.capacity > 0:
                trip.occupancy_percent = trip.passenger_count / trip.capacity
            else:
                trip.occupancy_percent = 0.0
            trip.over_capacity = trip.passenger_count > trip.capacity if trip.capacity > 0 else (
                trip.passenger_count > 0
            )

    @api.onchange('schedule_id')
    def _onchange_schedule_id(self):
        if self.schedule_id:
            self.route_id = self.schedule_id.route_id
            self.direction = self.schedule_id.direction or self.schedule_id.route_id.direction or 'both'
            self.vehicle_id = (
                self.schedule_id.vehicle_id or
                self.schedule_id.route_id.vehicle_id
            )
            self.driver_id = (
                self.schedule_id.driver_id or
                (self.schedule_id.vehicle_id.driver_id if self.schedule_id.vehicle_id else False) or
                self.schedule_id.route_id.driver_id
            )
            target_date = self.date or fields.Date.context_today(self)
            if self.schedule_id.departure_time:
                self.planned_departure_time = self.schedule_id.float_time_to_utc_datetime(
                    target_date, self.schedule_id.departure_time
                )
            if self.schedule_id.arrival_time:
                self.planned_arrival_time = self.schedule_id.float_time_to_utc_datetime(
                    target_date, self.schedule_id.arrival_time
                )

            # Auto-populate route employees as expected passengers
            if self.schedule_id.route_id and not self.passenger_ids:
                lines = []
                for emp in self.schedule_id.route_id.employee_ids:
                    lines.append((0, 0, {
                        'employee_id': emp.id,
                        'pickup_stop_id': emp.pickup_stop_id.id if emp.pickup_stop_id else False,
                        'drop_off_stop_id': emp.drop_off_stop_id.id if emp.drop_off_stop_id else False,
                        'status': 'expected',
                    }))
                self.passenger_ids = lines

    @api.onchange('route_id')
    def _onchange_route_id(self):
        if self.route_id:
            if not self.direction or self.direction == 'both':
                self.direction = self.route_id.direction
            if not self.vehicle_id and self.route_id.vehicle_id:
                self.vehicle_id = self.route_id.vehicle_id
            if not self.driver_id and self.route_id.driver_id:
                self.driver_id = self.route_id.driver_id
            if self.schedule_id and self.schedule_id.route_id != self.route_id:
                self.schedule_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('logistics.transport.trip') or 'New'
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)

    def action_confirm(self):
        for trip in self:
            if trip.state != 'draft':
                raise UserError(_("Only draft trips can be planned."))
            trip.state = 'planned'

    def action_start(self):
        for trip in self:
            if trip.state not in ('draft', 'planned'):
                raise UserError(_("Only draft or planned trips can be started."))
            trip.write({
                'state': 'in_progress',
                'actual_departure_time': fields.Datetime.now()
            })

    def action_complete(self):
        for trip in self:
            if trip.state != 'in_progress':
                raise UserError(_("Only in-progress trips can be completed."))
            trip.write({
                'state': 'completed',
                'actual_arrival_time': fields.Datetime.now()
            })

    def action_cancel(self):
        for trip in self:
            if trip.state == 'completed':
                raise UserError(_("Completed trips cannot be cancelled."))
            trip.state = 'cancelled'

    def action_reset_draft(self):
        for trip in self:
            trip.write({
                'state': 'draft',
                'actual_departure_time': False,
                'actual_arrival_time': False
            })

    def action_open_google_maps(self):
        self.ensure_one()
        if self.route_id:
            return self.route_id.action_open_google_maps()
        raise UserError(_("Please assign a Route first to open Google Maps."))


class LogisticsTransportTripPassenger(models.Model):
    _name = 'logistics.transport.trip.passenger'
    _description = 'Transport Trip Passenger'
    _order = 'trip_id, id'

    trip_id = fields.Many2one(
        'logistics.transport.trip', string='Trip', required=True, ondelete='cascade'
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True
    )
    pickup_stop_id = fields.Many2one(
        'logistics.transport.stop', string='Pickup Stop',
        domain="[('route_id', '=', parent.route_id)]"
    )
    drop_off_stop_id = fields.Many2one(
        'logistics.transport.stop', string='Drop-off Stop',
        domain="[('route_id', '=', parent.route_id)]"
    )
    status = fields.Selection(
        [
            ('expected', 'Expected'),
            ('boarded', 'Boarded'),
            ('no_show', 'No Show'),
            ('dropped', 'Dropped'),
            ('cancelled', 'Cancelled')
        ],
        string='Status', default='expected', required=True
    )
    boarding_time = fields.Datetime(string='Boarding Time', readonly=True)
    drop_time = fields.Datetime(string='Drop Time', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        related='trip_id.company_id', store=True, readonly=True
    )

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            if self.employee_id.pickup_stop_id:
                self.pickup_stop_id = self.employee_id.pickup_stop_id
            if self.employee_id.drop_off_stop_id:
                self.drop_off_stop_id = self.employee_id.drop_off_stop_id

    def action_board(self):
        for rec in self:
            rec.write({
                'status': 'boarded',
                'boarding_time': fields.Datetime.now()
            })

    def action_no_show(self):
        for rec in self:
            rec.write({
                'status': 'no_show'
            })

    def action_drop(self):
        for rec in self:
            rec.write({
                'status': 'dropped',
                'drop_time': fields.Datetime.now()
            })

    def action_cancel(self):
        for rec in self:
            rec.write({
                'status': 'cancelled'
            })
