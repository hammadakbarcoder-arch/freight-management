from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FreightRoutes(models.Model):
    _name = 'freight.routes'
    _description = 'Freight Route'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(default=True)
    land_price = fields.Float(string='Land Sale Price')
    air_price = fields.Float(string='Air Sale Price')
    water_price = fields.Float(string='Water Sale Price')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    @api.constrains('land_price', 'air_price', 'water_price')
    def _check_prices(self):
        for rec in self:
            if rec.land_price < 0 or rec.air_price < 0 or rec.water_price < 0:
                raise ValidationError("Route sale prices cannot be negative.")

    def get_price(self, transport):
        """Return this route's sale price for a transport type ('land', 'air' or 'water')."""
        self.ensure_one()
        return {
            'land': self.land_price,
            'air': self.air_price,
            'water': self.water_price,
        }.get(transport, 0.0)