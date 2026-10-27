# -*- coding: utf-8 -*-
from odoo import models, fields
import urllib.parse


class LogisticsTransportStop(models.Model):
    _name = 'logistics.transport.stop'
    _description = 'Logistics Transport Stop'
    _order = 'sequence, id'

    name = fields.Char(string='Stop Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    route_id = fields.Many2one(
        'logistics.transport.route', string='Route',
        required=True, ondelete='cascade'
    )
    address_id = fields.Many2one(
        'res.partner', string='Stop Address',
        required=True,
        help='Partner record representing the physical address/location of the stop.'
    )
    planned_time = fields.Float(
        string='Planned Time',
        help='Planned arrival time in hours (e.g. 8.5 for 08:30 AM).'
    )
    stop_type = fields.Selection(
        [
            ('pickup', 'Pickup'),
            ('drop_off', 'Drop-off'),
            ('both', 'Both')
        ],
        string='Stop Type', default='both', required=True
    )
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company', string='Company',
        related='route_id.company_id', store=True, readonly=True
    )

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

        origin = format_addr(self.start_address_id) or (
            format_addr(self.stop_ids[0].address_id) if self.stop_ids else "")
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
