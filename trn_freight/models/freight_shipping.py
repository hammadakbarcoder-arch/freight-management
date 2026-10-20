import json
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

PORT_FLAG = {'land': 'is_land', 'air': 'is_air', 'water': 'is_water'}
TRANSPORT_LABEL = {'land': 'Land', 'air': 'Air', 'water': 'Water'}


# Main Model: Freight Shipping
class FreightShipping(models.Model):
    _name = 'freight.shipping'
    _description = 'Freight Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Header
    name = fields.Char(string="Name", default="New", readonly=True, copy=False)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    # Left
    shipper_id = fields.Many2one(
        'res.partner', string="Shipper", required=True, tracking=True, copy=False,
        help="The party that sends the goods (Sender/Exporter).")
    consignee_id = fields.Many2one(
        'res.partner', string="Consignee", required=True, tracking=True, copy=False,
        help="The party that receives the goods (Receiver/Importer).")
    order_date = fields.Date(
        string="Date", default=fields.Date.context_today,
        help="Date when the freight order is created.")
    loading_port = fields.Many2one(
        'freight.port', string="Loading Port", required=True,
        help="Port where the cargo is loaded.")
    agent_id = fields.Many2one(
        'res.partner', string="Agent",
        help="Freight forwarding agent handling this shipment.")

    # Right Column Fields
    order_type = fields.Selection(
        [('import', 'Import'), ('export', 'Export')],
        string='Import/Export', required=True, tracking=True,
        help="Specify whether this shipment is an Import or Export order.")

    transport = fields.Selection(
        [('land', 'Land'), ('air', 'Air'), ('water', 'Water')],
        string='Transport', required=True, tracking=True,
        help="Mode of transport used for the shipment.")

    land_type = fields.Selection(
        [('ftl', 'FTL'), ('ltl', 'LTL')], string='Land Shipping',
        help="Full Truck Load (FTL) or Less than Truck Load (LTL).")
    sea_type = fields.Selection(
        [('fcl', 'FCL'), ('lcl', 'LCL')], string='Water Shipping',
        help="Full Container Load (FCL) or Less than Container Load (LCL).")

    discharge_port_id = fields.Many2one(
        'freight.port', string='Discharging Port', required=True,
        help="Destination port where the cargo is discharged.")
    expected_date = fields.Date(
        string='Expected Date',
        help="Expected arrival or completion date of the shipment.")
    port_domain = fields.Char(compute='_compute_port_domain')

    # State Field
    state = fields.Selection(
        [('draft', 'Draft'), ('submitted', 'Submitted'), ('confirmed', 'Confirmed'),
         ('invoiced', 'Invoiced'), ('done', 'Done'), ('cancelled', 'Cancel')],
        default='draft', required=True, tracking=True, copy=False)

    # Smart Button Counters
    clearance_count = fields.Integer(string="Clearance Count", default=0)
    invoice_count = fields.Integer(string="Invoice Count", default=0)

    # Child Lines Relations
    cargo_ids = fields.One2many('freight.order.cargo', 'order_id', string='Cargo')
    route_ids = fields.One2many('freight.order.route', 'order_id', string='Routes')
    service_ids = fields.One2many('freight.order.service', 'order_id', string='Services')
    track_ids = fields.One2many('freight.order.track', 'order_id', string='Tracking')

    # Totals Fields
    cargo_total = fields.Float(
        compute='_compute_totals', store=True, string='Cargo Total',
        help="Total amount for all cargo lines.")
    total_weight = fields.Float(
        compute='_compute_totals', store=True, string='Total Weight',
        help="Total weight of all cargo lines.")
    total_volume = fields.Float(
        compute='_compute_totals', store=True, string='Total Volume',
        help="Total volume of all cargo lines.")
    routes_total = fields.Float(
        compute='_compute_totals', store=True, string='Routes Total',
        help="Total sale amount for all route lines.")
    service_total_sale = fields.Float(
        compute='_compute_totals', store=True, string='Service Total Sale',
        help="Total sale amount for all service lines.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('freight.order') or 'New'
        return super().create(vals_list)

    @api.depends('cargo_ids.total_price', 'cargo_ids.weight', 'cargo_ids.volume',
                 'route_ids.sale', 'service_ids.total_sale')
    def _compute_totals(self):
        for rec in self:
            rec.cargo_total = sum(rec.cargo_ids.mapped('total_price'))
            rec.total_weight = sum(rec.cargo_ids.mapped('weight'))
            rec.total_volume = sum(rec.cargo_ids.mapped('volume'))
            rec.routes_total = sum(rec.route_ids.mapped('sale'))
            rec.service_total_sale = sum(rec.service_ids.mapped('total_sale'))

    @api.depends('transport')
    def _compute_port_domain(self):
        for rec in self:
            if rec.transport:
                flag = PORT_FLAG.get(rec.transport)
                domain = [(flag, '=', True)] if flag else []
            else:
                domain = []
            rec.port_domain = json.dumps(domain)

    @api.onchange('transport')
    def _onchange_transport(self):
        self.land_type = False
        self.sea_type = False
        self.loading_port = False
        self.discharge_port_id = False

    @api.constrains('loading_port', 'discharge_port_id', 'transport')
    def _check_order_ports_transport(self):
        for rec in self:
            flag = PORT_FLAG.get(rec.transport)
            if not flag:
                continue
            for port in (rec.loading_port | rec.discharge_port_id):
                if port and not port[flag]:
                    raise ValidationError(
                        f"Port '{port.name}' does not handle {TRANSPORT_LABEL[rec.transport]} transport.")

    def _ensure_state(self, allowed, action):
        labels = dict(self._fields['state'].selection)
        for rec in self:
            if rec.state not in allowed:
                allowed_text = ' or '.join(labels[s] for s in allowed)
                raise UserError(
                    f"Order {rec.name} cannot be {action} because it is {labels[rec.state]}. "
                    f"Only {allowed_text} orders can be {action}.")

    def action_submit(self):
        self._ensure_state(['draft'], 'submitted')
        self.write({'state': 'submitted'})

    def action_confirm(self):
        self._ensure_state(['submitted'], 'confirmed')
        self.write({'state': 'confirmed'})
        self.cargo_ids.mapped('container_id').write({'state': 'reserved'})

    def action_invoice(self):
        self._ensure_state(['confirmed'], 'invoiced')
        self.write({'state': 'invoiced'})

    def action_done(self):
        self._ensure_state(['confirmed', 'invoiced'], 'marked as done')
        self.write({'state': 'done'})
        self.cargo_ids.mapped('container_id').write({'state': 'available'})

    def action_cancel(self):
        self._ensure_state(['draft', 'submitted', 'confirmed'], 'cancelled')
        self.write({'state': 'cancelled'})

    @api.ondelete(at_uninstall=False)
    def _unlink_except_confirmed(self):
        for rec in self:
            if rec.state not in ('draft', 'cancelled'):
                raise UserError("You cannot delete a submitted or confirmed order.")

    def action_view_clearance(self):
        return True

    def action_view_invoices(self):
        return True

    def action_tracking(self):
        self.ensure_one()
        return {
            'name': 'Track Order',
            'type': 'ir.actions.act_window',
            'res_model': 'freight.order.track.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_source_location_id': self.loading_port.id,
                'default_destination_location_id': self.discharge_port_id.id,
                'default_transport': self.transport,
            }
        }


# =====================================================================
# Child Model 1: Cargo Lines (TAB 1: Order)
# =====================================================================
class FreightOrderCargo(models.Model):
    _name = 'freight.order.cargo'
    _description = 'Freight Order Cargo Line'

    order_id = fields.Many2one('freight.shipping', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='order_id.company_id', store=True, readonly=True)
    container_id = fields.Many2one('freight.container', string='Container', required=True)
    product_id = fields.Many2one('product.product', string='Goods', required=True)
    billing_on = fields.Selection(
        [('weight', 'Weight'), ('volume', 'Volume')], string='Billing On',
        default='weight', required=True)
    pricing_id = fields.Many2one('freight.price', string='Pricing', required=True)
    weight = fields.Float(string='Weight')
    volume = fields.Float(string='Volume')
    unit_price = fields.Float(compute='_compute_prices', store=True, string='Unit Price')
    total_price = fields.Float(compute='_compute_prices', store=True, string='Total Price')

    @api.depends('billing_on', 'pricing_id.weight_price', 'pricing_id.volume_price',
                 'weight', 'volume')
    def _compute_prices(self):
        for line in self:
            if line.billing_on == 'weight':
                line.unit_price = line.pricing_id.weight_price if line.pricing_id else 0.0
                line.total_price = line.unit_price * line.weight
            else:
                line.unit_price = line.pricing_id.volume_price if line.pricing_id else 0.0
                line.total_price = line.unit_price * line.volume

    @api.constrains('weight', 'volume')
    def _check_not_negative(self):
        for line in self:
            if line.weight < 0:
                raise ValidationError("Weight cannot be negative.")
            if line.volume < 0:
                raise ValidationError("Volume cannot be negative.")


# =====================================================================
# Child Model 2: Route Lines (TAB 2: Routes)
# =====================================================================
class FreightOrderRoute(models.Model):
    _name = 'freight.order.route'
    _description = 'Freight Order Route Line'

    order_id = fields.Many2one('freight.shipping', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='order_id.company_id', store=True, readonly=True)
    route_id = fields.Many2one('freight.routes', string='Route', required=True)
    source_port_id = fields.Many2one('freight.port', string='Source Location', required=True)
    destination_port_id = fields.Many2one('freight.port', string='Destination Location', required=True)
    transport = fields.Selection(related='order_id.transport', store=True, string='Transport')
    sale = fields.Float(compute='_compute_sale', store=True, string='Sale')

    @api.depends('route_id', 'transport',
                 'route_id.land_price', 'route_id.air_price', 'route_id.water_price')
    def _compute_sale(self):
        for line in self:
            line.sale = line.route_id.get_price(line.transport) if line.route_id else 0.0

    @api.constrains('source_port_id', 'destination_port_id', 'transport')
    def _check_ports_transport(self):
        for line in self:
            flag = PORT_FLAG.get(line.transport)
            if not flag:
                continue
            for port in (line.source_port_id | line.destination_port_id):
                if not port[flag]:
                    raise ValidationError(
                        f"Port '{port.name}' does not handle {TRANSPORT_LABEL[line.transport]} "
                        "transport. Please choose another port.")


# =====================================================================
# Child Model 3: Service Lines (TAB 3: Services)
# =====================================================================
class FreightOrderService(models.Model):
    _name = 'freight.order.service'
    _description = 'Freight Order Service Line'

    order_id = fields.Many2one('freight.shipping', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='order_id.company_id', store=True, readonly=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True)
    service_id = fields.Many2one('freight.service', string='Service', required=True)
    qty = fields.Float(string='Quantity', default=1.0)
    sale = fields.Float(string='Sale')
    total_sale = fields.Float(compute='_compute_total_sale', store=True, string='Total Sale')

    @api.onchange('service_id', 'vendor_id')
    def _onchange_service_id(self):
        if self.service_id:
            vendor_line = self.service_id.vendor_line_ids.filtered(
                lambda l: l.vendor_id == self.vendor_id
            )[:1]
            self.sale = vendor_line.sale_price if vendor_line else self.service_id.sale_price

    @api.depends('qty', 'sale')
    def _compute_total_sale(self):
        for line in self:
            line.total_sale = line.qty * line.sale


# =====================================================================
# Child Model 4: Track Lines (TAB 4: Track)
# =====================================================================
class FreightOrderTrack(models.Model):
    _name = 'freight.order.track'
    _description = 'Freight Order Track Line'

    order_id = fields.Many2one('freight.shipping', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='order_id.company_id', store=True, readonly=True)
    source_location_id = fields.Many2one('freight.port', string='Source Location', required=True)
    destination_location_id = fields.Many2one('freight.port', string='Destination Location', required=True)
    transport = fields.Selection(
        [('land', 'Land'), ('air', 'Air'), ('water', 'Water')],
        string='Transport', required=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    status = fields.Selection(
        [('received', 'Received'), ('delivered', 'Delivered')],
        string='Received/Delivered', required=True)