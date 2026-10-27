# -*- coding: utf-8 -*-
import urllib.parse
from odoo import models, fields, api


class LogisticsTransportRoute(models.Model):
    _name = 'logistics.transport.route'
    _description = 'Logistics Transport Route'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Route Name', required=True, tracking=True)
    code = fields.Char(string='Route Code', tracking=True, copy=False)
    direction = fields.Selection(
        [
            ('pickup', 'Pickup'),
            ('drop_off', 'Drop-off'),
            ('both', 'Both')
        ],
        string='Direction', default='both', required=True, tracking=True
    )
    vehicle_id = fields.Many2one(
        'fleet.vehicle', string='Vehicle', tracking=True
    )
    driver_id = fields.Many2one(
        'res.partner', string='Driver',
        related='vehicle_id.driver_id', store=True, readonly=False, tracking=True
    )
    start_address_id = fields.Many2one(
        'res.partner', string='Start Address', tracking=True
    )
    end_address_id = fields.Many2one(
        'res.partner', string='End Address', tracking=True
    )
    stop_ids = fields.One2many(
        'logistics.transport.stop', 'route_id', string='Stops'
    )
    planned_distance = fields.Float(
        string='Planned Distance (KM)', tracking=True
    )
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True
    )

    stop_count = fields.Integer(
        string='Stop Count',
        compute='_compute_stop_count',
        store=True
    )
    employee_ids = fields.One2many(
        'hr.employee', 'transport_route_id', string='Assigned Employees'
    )
    employee_count = fields.Integer(
        string='Employee Count',
        compute='_compute_capacity_and_occupancy',
        store=True
    )
    capacity = fields.Integer(
        string='Capacity',
        compute='_compute_capacity_and_occupancy',
        store=True
    )
    occupancy_percent = fields.Float(
        string='Occupancy %',
        compute='_compute_capacity_and_occupancy',
        store=True
    )

    @api.depends('employee_ids', 'vehicle_id', 'vehicle_id.effective_capacity')
    def _compute_capacity_and_occupancy(self):
        for route in self:
            route.employee_count = len(route.employee_ids)
            route.capacity = route.vehicle_id.effective_capacity if route.vehicle_id else 0
            if route.capacity > 0:
                route.occupancy_percent = route.employee_count / route.capacity
            else:
                route.occupancy_percent = 0.0

    @api.depends('stop_ids')
    def _compute_stop_count(self):
        for route in self:
            route.stop_count = len(route.stop_ids)

    def action_view_stops(self):
        self.ensure_one()
        return {
            'name': f'Stops - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'logistics.transport.stop',
            'view_mode': 'list,form',
            'domain': [('route_id', '=', self.id)],
            'context': {'default_route_id': self.id},
        }

    def action_view_stops_on_map(self):
        self.ensure_one()
        return {
            'name': f'Stops on Map - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'logistics.transport.stop',
            'view_mode': 'map,list,form',
            'domain': [('route_id', '=', self.id)],
            'context': {'default_route_id': self.id},
        }

    def action_open_google_maps(self):
        self.ensure_one()

        def format_addr(partner):
            if not partner:
                return ""
            addr = ", ".join(filter(None, [
                partner.street, partner.street2, partner.city,
                partner.state_id.name, partner.country_id.name
            ]))
            return addr or partner.name or ""

        origin = format_addr(self.start_address_id) or (format_addr(self.stop_ids[0].address_id) if self.stop_ids else "")
        dest = format_addr(self.end_address_id) or (format_addr(self.stop_ids[-1].address_id) if self.stop_ids else "")

        intermediate_stops = self.stop_ids
        if self.start_address_id and self.stop_ids and self.stop_ids[0].address_id == self.start_address_id:
            intermediate_stops = intermediate_stops[1:]
        if self.end_address_id and intermediate_stops and intermediate_stops[-1].address_id == self.end_address_id:
            intermediate_stops = intermediate_stops[:-1]

        waypoints = [format_addr(stop.address_id) for stop in intermediate_stops if format_addr(stop.address_id)]

        params = {'api': '1'}
        if origin:
            params['origin'] = origin
        if dest:
            params['destination'] = dest
        if waypoints:
            params['waypoints'] = '|'.join(waypoints)

        url = f"https://www.google.com/maps/dir/?{urllib.parse.urlencode(params)}"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
