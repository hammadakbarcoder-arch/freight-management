from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FreightService(models.Model):
    _name = 'freight.service'
    _description = 'Freight Service'

    name = fields.Char(string='Name', required=True)
    sale_price = fields.Float(string='Sale Price')
    vendor_line_ids = fields.One2many(
        'freight.service.line', 'service_id', string='Vendors')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    @api.constrains('sale_price')
    def _check_sale_price(self):
        for rec in self:
            if rec.sale_price < 0:
                raise ValidationError("Sale price cannot be negative.")


class FreightServiceLine(models.Model):
    _name = 'freight.service.line'
    _description = 'Freight Service Vendor Line'

    service_id = fields.Many2one(
        'freight.service', string='Service', required=True, ondelete='cascade')
    vendor_id = fields.Many2one(
        'res.partner', string='Vendor', required=True)
    sale_price = fields.Float(string='Sale Price')

    @api.constrains('sale_price')
    def _check_sale_price(self):
        for rec in self:
            if rec.sale_price < 0:
                raise ValidationError("Vendor sale price cannot be negative.")