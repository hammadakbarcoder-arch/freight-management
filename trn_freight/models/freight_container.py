from odoo import models, fields


class FreightContainer(models.Model):
    _name = 'freight.container'
    _description = 'Freight Container'

    name = fields.Char(string='Name', required=True, help='Name of the container')
    code = fields.Char(string='Code', required=True, help='Unique container code')

    size = fields.Float(string='Size', help='Container size')
    size_uom_id = fields.Many2one('uom.uom', string='Size UOM', help='Unit of measure for container size')

    weight = fields.Float(string='Weight', help='Maximum weight capacity')
    weight_uom_id = fields.Many2one('uom.uom', string='Weight UOM', help='Unit of measure for container weight')

    volume = fields.Float(string='Volume', help='Maximum volume capacity')
    volume_uom_id = fields.Many2one('uom.uom', string='Volume UOM', help='Unit of measure for container volume')

    state = fields.Selection([
        ('available', 'Available'),
        ('reserved', 'Reserve')
    ], string='Status', default='available', required=True)

    active = fields.Boolean(string='Active', default=True, help='If unchecked, it will allow you to hide the container without removing it.')
   # company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
