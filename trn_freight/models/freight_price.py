from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FreightPrice(models.Model):
    _name = 'freight.price'
    _description = 'Freight Price'

    name = fields.Char(string='Name', required=True)
    weight_price = fields.Float(string='Weight Price', required=True)
    volume_price = fields.Float(string='Volume Price', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    @api.constrains('weight_price', 'volume_price')
    def _check_prices(self):
        for rec in self:
            if rec.weight_price < 0 or rec.volume_price < 0:
                raise ValidationError("Weight price and volume price cannot be negative.")