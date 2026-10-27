# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    seat_capacity_override = fields.Integer(
        string='Capacity Override',
        help='Override standard vehicle seating capacity for staff transport.'
    )
    effective_capacity = fields.Integer(
        string='Effective Capacity',
        compute='_compute_effective_capacity',
        store=True,
        help='Effective transport capacity (Override capacity if set, otherwise standard seats).'
    )

    # 🔹 NEW: Gaari ke sath assigned routes aur Trips count
    route_ids = fields.One2many(
        'logistics.transport.route', 'vehicle_id', string='Assigned Routes'
    )
    trip_count = fields.Integer(
        string='Trips Count', compute='_compute_trip_count'
    )

    @api.depends('seats', 'seat_capacity_override')
    def _compute_effective_capacity(self):
        for vehicle in self:
            if vehicle.seat_capacity_override and vehicle.seat_capacity_override > 0:
                vehicle.effective_capacity = vehicle.seat_capacity_override
            else:
                vehicle.effective_capacity = vehicle.seats or 0

    # 🔹 NEW: Compute Trips Count
    @api.depends('route_ids')
    def _compute_trip_count(self):
        for vehicle in self:
            vehicle.trip_count = len(vehicle.route_ids)

    # 🔹 NEW: Smart Button Click Action
    def action_view_transport_routes(self):
        self.ensure_one()
        return {
            'name': 'Transport Routes',
            'type': 'ir.actions.act_window',
            'res_model': 'logistics.transport.route',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }