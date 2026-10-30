# -*- coding: utf-8 -*-
from datetime import datetime, time
import pytz
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LogisticsTransportSchedule(models.Model):
    _name = 'logistics.transport.schedule'
    _description = 'Logistics Transport Schedule'
    _order = 'route_id, departure_time'

    name = fields.Char(string='Schedule Name', required=True)
    route_id = fields.Many2one(
        'logistics.transport.route', string='Route', required=True, ondelete='cascade'
    )
    direction = fields.Selection(
        related='route_id.direction', string='Direction', readonly=True, store=True
    )
    active = fields.Boolean(string='Active', default=True)

    mon = fields.Boolean(string='Monday', default=True)
    tue = fields.Boolean(string='Tuesday', default=True)
    wed = fields.Boolean(string='Wednesday', default=True)
    thu = fields.Boolean(string='Thursday', default=True)
    fri = fields.Boolean(string='Friday', default=True)
    sat = fields.Boolean(string='Saturday', default=False)
    sun = fields.Boolean(string='Sunday', default=False)

    departure_time = fields.Float(
        string='Departure Time', required=True,
        help='Departure Time in hours (e.g. 7.5 for 07:30)'
    )
    arrival_time = fields.Float(
        string='Arrival Time', required=True,
        help='Arrival time in hours (e.g. 8.5 for 08:30)'
    )
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle Override')
    driver_id = fields.Many2one('res.partner', string='Driver Override')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('company_id'):
                if vals.get('route_id'):
                    route = self.env['logistics.transport.route'].browse(vals['route_id'])
                    vals['company_id'] = route.company_id.id or self.env.company.id
                else:
                    vals['company_id'] = self.env.company.id
        return super().create(vals_list)

    effective_vehicle_id = fields.Many2one(
        'fleet.vehicle', string='Effective Vehicle',
        compute='_compute_effective_resources', store=True
    )
    effective_driver_id = fields.Many2one(
        'res.partner', string='Effective Driver',
        compute='_compute_effective_resources', store=True
    )

    @api.depends('vehicle_id', 'driver_id', 'route_id.vehicle_id', 'route_id.driver_id')
    def _compute_effective_resources(self):
        for rec in self:
            rec.effective_vehicle_id = rec.vehicle_id or rec.route_id.vehicle_id
            rec.effective_driver_id = (
                rec.driver_id or
                (rec.vehicle_id.driver_id if rec.vehicle_id else False) or
                rec.route_id.driver_id
            )

    @api.depends('name', 'departure_time', 'arrival_time')
    def _compute_display_name(self):
        for rec in self:
            def fmt_time(t):
                h = int(t or 0)
                m = int(round(((t or 0) - h) * 60))
                return f"{h:02d}:{m:02d}"
            time_str = f"{fmt_time(rec.departure_time)} - {fmt_time(rec.arrival_time)}"
            rec.display_name = f"{rec.name} ({time_str})" if rec.name else time_str

    @api.onchange('route_id')
    def _onchange_route_id(self):
        if self.route_id and not self.name:
            dir_label = dict(self.route_id._fields['direction'].selection).get(self.route_id.direction, '')
            self.name = f"{self.route_id.name} - {dir_label}".strip(' -')

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id and not self.driver_id and self.vehicle_id.driver_id:
            self.driver_id = self.vehicle_id.driver_id

    @api.constrains('departure_time', 'arrival_time')
    def _check_schedule_times(self):
        for rec in self:
            if rec.departure_time < 0 or rec.departure_time >= 24:
                raise ValidationError("Departure Time must be between 00:00 and 23:59!")
            if rec.arrival_time <= 0 or rec.arrival_time > 24:
                raise ValidationError("Arrival Time must be between 00:01 and 24:00!")
            if rec.arrival_time <= rec.departure_time:
                raise ValidationError("Arrival Time must be after Departure Time!")

    @api.constrains('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
    def _check_at_least_one_day(self):
        for rec in self:
            if not (rec.mon or rec.tue or rec.wed or rec.thu or rec.fri or rec.sat or rec.sun):
                raise ValidationError("At least one weekday must be selected for the schedule!")

    def is_running_on_date(self, target_date):
        """Check if this schedule is active on the weekday of target_date."""
        self.ensure_one()
        weekday_map = {
            0: self.mon,
            1: self.tue,
            2: self.wed,
            3: self.thu,
            4: self.fri,
            5: self.sat,
            6: self.sun,
        }
        return weekday_map.get(target_date.weekday(), False)

    def float_time_to_utc_datetime(self, target_date, float_time_val):
        """
        Combine target_date and float_time_val in user's timezone,
        then convert to UTC datetime (naive) for Odoo fields.Datetime.
        """
        self.ensure_one()
        hours = int(float_time_val or 0)
        minutes = int(round(((float_time_val or 0) - hours) * 60))
        # Clamp minutes to 59 in case of rounding 60
        if minutes >= 60:
            hours += 1
            minutes = 0
        local_time = time(hour=min(hours, 23), minute=minutes)
        naive_dt = datetime.combine(target_date, local_time)

        # Get user's timezone or fallback to UTC
        user_tz_name = self.env.user.tz or 'UTC'
        try:
            user_tz = pytz.timezone(user_tz_name)
            local_dt = user_tz.localize(naive_dt, is_dst=None)
            utc_dt = local_dt.astimezone(pytz.utc)
            return utc_dt.replace(tzinfo=None)
        except Exception:
            return naive_dt
