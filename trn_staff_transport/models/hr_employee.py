from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_transport_enabled = fields.Boolean(string='Is Transport Enabled', default=False, tracking=True,
                                          help='Check if the company uses company staff transports')
    transport_route_id = fields.Many2one('logistics.transport.route', tracking=True, string='Transport Route')
    pickup_stop_id = fields.Many2one('logistics.transport.stop', tracking=True, string='Pickup Stop')
    drop_off_stop_id = fields.Many2one('logistics.transport.stop', tracking=True, string='Drop Off')
    transport_direction = fields.Selection(selection=[(
        'pickup', 'Pickup'),
        ('drop_off', 'Drop-off'),
        ('both', 'Both'),
    ],
        string='Direction', default='both', tracking=True)
    transport_vehicle_id = fields.Many2one(
        'fleet.vehicle', related='transport_route_id.vehicle_id', string='Vehicle', store=True, readonly=True
    )
    transport_driver_id = fields.Many2one(
        'res.partner', string='Driver', related='transport_route_id.driver_id', store=True, readonly=True
    )

    @api.onchange('transport_route_id')
    def _onchange_transport_route_id(self):
        if self.transport_route_id:
            if self.pickup_stop_id and self.pickup_stop_id.route_id != self.transport_route_id:
                self.pickup_stop_id = False
            if self.drop_off_stop_id and self.drop_off_stop_id.route_id != self.transport_route_id:
                self.drop_off_stop_id = False
        else:
            self.pickup_stop_id = False
            self.drop_off_stop_id = False

    @api.constrains('transport_route_id', 'pickup_stop_id', 'drop_off_stop_id')
    def _check_transport_stops_belong_to_route(self):
        for employee in self:
            if employee.transport_route_id:
                if employee.pickup_stop_id and employee.pickup_stop_id.route_id != employee.transport_route_id:
                    raise ValidationError("Pickup Stop must belong to the selected Transport Route!")
                if employee.drop_off_stop_id and employee.drop_off_stop_id.route_id != employee.transport_route_id:
                    raise ValidationError("Drop-off Stop must belong to the selected Transport Route!")
