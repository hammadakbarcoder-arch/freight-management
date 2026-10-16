from odoo import models, fields


class FreightPort(models.Model):
    _name = 'freight.port'
    _description = 'Freight Port'
    _order = 'name'

    name = fields.Char(string='Name', required=True, index=True)
    code = fields.Char(string='Code', index=True)
    country_id = fields.Many2one('res.country', string='Country')
    state_id = fields.Many2one('res.country.state', string='State', domain="[('country_id', '=', country_id)]")
    active = fields.Boolean(string='Active', default=True)

    # Flags
    is_land = fields.Boolean(string='Land')
    is_air = fields.Boolean(string='Air')
    is_water = fields.Boolean(string='Water')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
